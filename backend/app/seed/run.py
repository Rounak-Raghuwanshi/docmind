"""Seed realistic demo data for every feature.

    python -m app.cli seed            # create (skips if it already exists)
    python -m app.cli seed --reset    # delete the demo data and create it again

Creates three users with different roles, a public demo workspace (Indian tax & GST) and a
team workspace (engineering handbook), ingests real documents through the normal pipeline,
then writes conversations whose citations and retrieval scores come from the real
retriever, plus feedback and 30 days of usage history for the analytics and insights pages.
"""

import asyncio
import random
import re
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import SessionLocal
from app.llm.base import LLMError
from app.llm.client import get_llm
from app.models import (
    Conversation,
    DocStatus,
    Document,
    Message,
    MessageFeedback,
    Role,
    User,
    Workspace,
    WorkspaceInvite,
    WorkspaceMember,
)
from app.rag.citations import build_citations, normalise_markers, strip_invalid_markers
from app.rag.embedder import get_embedder
from app.rag.extractive import MIN_COVERAGE, extractive_answer, question_coverage
from app.rag.gate import GateConfig, decide
from app.rag.ocr import tesseract_available
from app.rag.prompts import NOT_FOUND_ANSWER, answer_messages
from app.rag.reranker import get_reranker
from app.rag.tokens import count_tokens
from app.redis_client import get_redis
from app.security import hash_password, hash_token, new_opaque_token
from app.seed.builders import build
from app.seed.documents import ENGINEERING_DOCS, TAX_DOCS, DemoDoc
from app.services.auth import create_personal_workspace
from app.services.ingestion import Ingestor
from app.services.retrieval import RetrievalResult, Retriever
from app.services.storage import get_storage

DEMO_PASSWORD = "Demo@12345"
DEMO_MODEL = "llama-3.3-70b-versatile"


@dataclass
class DemoUser:
    key: str
    email: str
    name: str


USERS = [
    DemoUser("owner", "aarav@docmind.dev", "Aarav Mehta"),
    DemoUser("editor", "priya@docmind.dev", "Priya Nair"),
    DemoUser("viewer", "rohan@docmind.dev", "Rohan Verma"),
]


@dataclass
class Turn:
    question: str
    answer: str | None = None  # None = build an extractive answer from the retrieved chunks
    # Words that must appear in source [n] for the hand-written answer to be used.
    expect: dict[int, str] | None = None
    standalone: str | None = None  # rewritten form of a follow-up question


@dataclass
class Chat:
    title: str
    user: str
    days_ago: float
    turns: list[Turn]
    feedback: int | None = None
    comment: str | None = None


TAX_CHATS = [
    Chat(
        "Section 80D for senior citizen parents",
        "owner",
        0.2,
        [
            Turn(
                "How much deduction can I claim under Section 80D for my senior citizen parents?",
                "You can claim up to **₹50,000** for health-insurance premiums paid for parents who "
                "are senior citizens [1]. This is in addition to the ₹25,000 limit for yourself, your "
                "spouse and children (₹50,000 if you are a senior citizen yourself), so the total can "
                "reach **₹1,00,000** [1].",
                {1: "80D"},
            ),
            Turn(
                "Does a preventive health check-up count?",
                "Yes. Up to **₹5,000** spent on preventive health check-ups qualifies, but it sits "
                "inside the overall 80D limit rather than on top of it [1]. It is also the only part "
                "that may be paid in cash; premiums must be paid by any other mode [1].",
                {1: "preventive"},
                standalone="Does a preventive health check-up count for the Section 80D deduction?",
            ),
        ],
        feedback=1,
    ),
    Chat(
        "GST registration and GSTR-3B deadlines",
        "owner",
        1.4,
        [
            Turn(
                "When does a supplier of services need GST registration?",
                "A service provider must register once **aggregate turnover exceeds ₹20 lakh** in a "
                "financial year (₹10 lakh in special category states) [1]. Some suppliers must "
                "register regardless of turnover, for example those making inter-state supplies of "
                "goods or selling through e-commerce operators [1].",
                {1: "register"},
            ),
            Turn(
                "And what are the due dates for GSTR-3B?",
                "- **Monthly filers:** by the **20th** of the following month [1]\n"
                "- **QRMP scheme:** quarterly, by the **22nd or 24th** depending on the state, with "
                "tax paid in the first two months through PMT-06 [1]\n\n"
                "A late GSTR-3B attracts a fee of ₹50 per day (₹20 for nil returns) plus 18% "
                "interest on tax paid late [1].",
                {1: "3B"},
                standalone="What are the due dates for filing GSTR-3B?",
            ),
        ],
        feedback=1,
    ),
    Chat(
        "Tax on long-term gains from shares",
        "owner",
        2.6,
        [
            Turn(
                "What is the tax on long-term capital gains from listed shares?",
                "For transfers on or after 23 July 2024, long-term gains on listed equity shares and "
                "equity mutual funds are taxed at **12.5% under Section 112A** [1], after an annual "
                "exemption of **₹1.25 lakh** [1]. Listed shares count as long-term when held for "
                "more than **12 months** [1].",
                {1: "112A"},
            ),
        ],
        feedback=1,
    ),
    Chat(
        "Is 12 lakh tax-free in the new regime?",
        "owner",
        4.1,
        [
            Turn(
                "Is income up to 12 lakh tax-free in the new regime?",
                "Yes, for resident individuals. Under the new regime for FY 2025-26, the **Section 87A "
                "rebate of up to ₹60,000** makes the tax nil when taxable income is up to ₹12 lakh "
                "[1]. Salaried people also get the **₹75,000 standard deduction**, so a salary of up "
                "to ₹12.75 lakh can be tax-free [1]. The rebate doesn't apply to income taxed at "
                "special rates, such as LTCG under Section 112A [1].",
                {1: "87A"},
            ),
            Turn(
                "Which deductions are not available in the new regime?",
                None,
                standalone="Which deductions are not available under the new tax regime?",
            ),
        ],
    ),
    Chat(
        "Advance tax installments",
        "owner",
        6.3,
        [
            Turn(
                "When are advance tax installments due?",
                "Advance tax is due in four installments [1]:\n\n"
                "- **15 June:** at least 15% of the estimated tax\n"
                "- **15 September:** at least 45%\n"
                "- **15 December:** at least 75%\n"
                "- **15 March:** 100%\n\n"
                "It applies when your estimated liability after TDS is ₹10,000 or more [1]. Paying "
                "late or too little attracts interest under Sections 234B and 234C [2].",
                {1: "15 June", 2: "234B"},
            ),
        ],
        feedback=1,
    ),
    Chat(
        "Input tax credit conditions",
        "owner",
        8.0,
        [
            Turn(
                "What conditions must be met to claim input tax credit?",
                "Section 16 has four conditions, and all of them must be met [1]:\n\n"
                "1. You hold a tax invoice or debit note\n"
                "2. You have actually received the goods or services\n"
                "3. The supplier has paid the tax and the invoice appears in your GSTR-2B\n"
                "4. You have filed your own GSTR-3B\n\n"
                "Credit must be claimed by 30 November of the following year, and it's reversed if "
                "the supplier isn't paid within 180 days [2].",
                {1: "Section 16", 2: "180 days"},
            ),
        ],
        feedback=-1,
        comment="Correct, but I wanted examples of blocked credits too.",
    ),
    Chat(
        "TDS on office rent",
        "owner",
        11.0,
        [
            Turn(
                "What TDS rate applies to rent for a building?",
                "Rent for land, building or furniture attracts **10% TDS under Section 194-I**, "
                "while rent for plant and machinery attracts 2% [1]. TDS applies when rent exceeds "
                "**₹50,000 for a month** [1].",
                {1: "194-I"},
            ),
        ],
    ),
    Chat(
        "Stamp duty question",
        "owner",
        13.0,
        [Turn("What is the stamp duty on buying a flat in Maharashtra?")],
    ),
]

# Extra questions asked by the team over the last month: these fill the analytics and
# insights pages (including knowledge gaps and cache hits).
TAX_TRAFFIC = [
    "How is HRA exemption calculated?",
    "What is the 80C limit?",
    "Which investments qualify under Section 80C?",
    "What is the deduction for NPS under 80CCD(1B)?",
    "Is education loan interest deductible?",
    "How much savings interest is tax-free for senior citizens?",
    "How are debt mutual funds taxed now?",
    "What is the holding period for long-term capital gains on property?",
    "What is the composition scheme turnover limit?",
    "When is GSTR-1 due?",
    "When is an e-way bill required?",
    "Who must generate e-invoices?",
    "Which input tax credits are blocked?",
    "What is the TDS rate for professional fees?",
    "When must TDS be deposited?",
    "What is the late fee for filing the income tax return after the due date?",
    "Until when can a belated return be filed?",
    "What are the new regime tax slabs?",
    "What is the 80C limit?",
    "When is GSTR-1 due?",
    "How is HRA exemption calculated?",
    "What is the corporate tax rate in Singapore?",
    "How do I apply for a passport?",
    "What is the stamp duty on buying a flat in Maharashtra?",
    "What is the GST rate on gold jewellery?",
    "What is the GST rate on gold jewellery?",
    "Who won the IPL in 2024?",
]

ENG_CHATS = [
    Chat(
        "SEV1 first steps",
        "owner",
        0.5,
        [
            Turn(
                "What should I do in the first 15 minutes of a SEV1?",
                "1. **Declare it** in #incidents with the `/incident` command, which creates a channel "
                "and a video bridge [1]\n"
                "2. **Page the incident commander** [1]\n"
                "3. **Post the first status update within 15 minutes**, even if the cause is unknown [1]\n\n"
                "Then prefer mitigation over root cause: roll back the latest deploy, disable the "
                "feature flag, or fail over to the secondary region [1].",
                {1: "15 minutes"},
            ),
            Turn(
                "How often do we post updates after that?",
                "Every **30 minutes** during a SEV1, and every hour during a SEV2 [1]. Each update "
                "states the impact, what the team is doing, and when the next update will come [1].",
                {1: "30 minutes"},
                standalone="How often are status updates posted during a SEV1 incident?",
            ),
        ],
        feedback=1,
    ),
    Chat(
        "Pagination for the new invoices API",
        "editor",
        2.0,
        [
            Turn(
                "Which pagination style should the new invoices API use?",
                "Use **cursor pagination** with `?limit=` and `?cursor=`, and return `next_cursor` "
                "in the response [1]. Offset pagination isn't allowed for new APIs because it's slow "
                "on large tables and returns duplicates when rows are inserted [1]. The default limit "
                "is 20 and the maximum is 100 [1].",
                {1: "cursor"},
            ),
        ],
        feedback=1,
    ),
    Chat(
        "Rolling back a bad deploy",
        "owner",
        3.5,
        [
            Turn(
                "How do we roll back a bad deploy?",
                "Roll back first and investigate afterwards [1]. Run the pipeline's **rollback job**, "
                "which redeploys the previous image tag, then confirm the dashboards recover [1]. "
                "Database migrations are not rolled back automatically, which is why they must be "
                "backward compatible (expand and contract) [2].",
                {1: "rollback", 2: "migration"},
            ),
        ],
    ),
    Chat(
        "New joiner questions",
        "viewer",
        5.0,
        [Turn("When do new engineers join the on-call rotation?")],
    ),
]

ENG_TRAFFIC = [
    "When is a postmortem required?",
    "What format should API errors have?",
    "How do we version our APIs?",
    "What must be true before deploying to production?",
    "How does code review work here?",
    "Can I deploy on Friday evening?",
    "What is our Kubernetes cluster autoscaling policy?",
]


# --------------------------------------------------------------------------------------


def renumber(answer: str, expect: dict[int, str], sources: list[dict[str, object]]) -> str | None:
    """Point each scripted [n] at whichever retrieved source actually contains its fact.

    Returns None when a fact isn't in any retrieved source, so the caller falls back to an
    extractive answer and every citation stays truthful.
    """
    mapping: dict[int, int] = {}
    for n, word in expect.items():
        idx = next(
            (
                i
                for i, s in enumerate(sources, start=1)
                if word.lower() in str(s["content"]).lower()
            ),
            None,
        )
        if idx is None:
            return None
        mapping[n] = idx
    return re.sub(
        r"\[(\d+)\]", lambda m: f"[{mapping.get(int(m.group(1)), int(m.group(1)))}]", answer
    )


class Seeder:
    def __init__(self, reset: bool) -> None:
        self.reset = reset
        self.rng = random.Random(42)  # deterministic demo data
        self.settings = get_settings()
        self.embedder = get_embedder()
        self.retriever = Retriever(SessionLocal, self.embedder, get_reranker(), self.settings)
        self.ingestor = Ingestor(SessionLocal, get_redis(), get_storage(), self.embedder)
        self.users: dict[str, User] = {}
        self.llm = get_llm()

    # ---- setup ---------------------------------------------------------------------------

    async def run(self) -> None:
        async with SessionLocal() as session:
            existing = (
                (
                    await session.execute(
                        select(User).where(User.email.in_([u.email for u in USERS]))
                    )
                )
                .scalars()
                .all()
            )
            if existing and not self.reset:
                print("Demo data already exists. Use `seed --reset` to recreate it.")
                self.print_credentials()
                return
            if existing:
                await self._delete(session, existing)

            for u in USERS:
                user = User(
                    email=u.email, full_name=u.name, hashed_password=hash_password(DEMO_PASSWORD)
                )
                session.add(user)
                await session.flush()
                await create_personal_workspace(session, user)
                self.users[u.key] = user
            tax = await self._workspace(
                session,
                "Demo: India Tax & GST",
                is_demo=True,
                members={"owner": Role.owner, "editor": Role.editor, "viewer": Role.viewer},
            )
            eng = await self._workspace(
                session,
                "Engineering Handbook",
                members={"owner": Role.owner, "editor": Role.editor, "viewer": Role.viewer},
            )
            session.add(
                WorkspaceInvite(
                    workspace_id=eng.id,
                    token_hash=hash_token(new_opaque_token()),
                    role=Role.viewer,
                    expires_at=datetime.now(UTC) + timedelta(days=6),
                    created_by=self.users["owner"].id,
                )
            )
            await session.commit()

        print("Ingesting documents (first run downloads the embedding models, ~200 MB)…")
        await self._documents(tax, TAX_DOCS)
        await self._documents(eng, ENGINEERING_DOCS)

        print("Writing conversations, feedback and usage history…")
        await self._chats(tax, TAX_CHATS, TAX_TRAFFIC)
        await self._chats(eng, ENG_CHATS, ENG_TRAFFIC)
        print("\nDemo data ready.")
        self.print_credentials()

    async def _delete(self, session: AsyncSession, users: Sequence[User]) -> None:
        ids = [u.id for u in users]
        keys = (
            (
                await session.execute(
                    select(Document.storage_key)
                    .join(Workspace, Workspace.id == Document.workspace_id)
                    .where(Workspace.owner_id.in_(ids))
                )
            )
            .scalars()
            .all()
        )
        await session.execute(delete(Workspace).where(Workspace.owner_id.in_(ids)))
        # Guests created by "Try the demo" lose their workspace membership with it; remove them too.
        await session.execute(
            delete(User).where(User.id.in_(ids) | User.email.like("guest-%@demo.docmind.local"))
        )
        await session.commit()
        for key in keys:
            try:
                await get_storage().delete(key)
            except Exception:  # noqa: S112 - best effort cleanup
                continue
        print(f"Removed previous demo data ({len(keys)} files).")

    async def _workspace(
        self, session: AsyncSession, name: str, members: dict[str, Role], is_demo: bool = False
    ) -> Workspace:
        if is_demo:
            # Only one workspace can be the public demo.
            for other in (
                await session.execute(select(Workspace).where(Workspace.is_demo))
            ).scalars():
                other.is_demo = False
            await session.flush()
        ws = Workspace(name=name, owner_id=self.users["owner"].id, is_demo=is_demo)
        session.add(ws)
        await session.flush()
        for key, role in members.items():
            session.add(WorkspaceMember(workspace_id=ws.id, user_id=self.users[key].id, role=role))
        return ws

    async def _documents(self, ws: Workspace, docs: list[DemoDoc]) -> None:
        import hashlib

        for i, spec in enumerate(docs):
            if spec.scanned and not tesseract_available():
                print(f"  skipped  {spec.filename} (install Tesseract to demo OCR)")
                continue
            data, content_type = build(spec)
            doc = Document(
                workspace_id=ws.id,
                uploaded_by=self.users["owner" if i % 2 == 0 else "editor"].id,
                filename=spec.filename,
                content_type=content_type,
                size_bytes=len(data),
                sha256=hashlib.sha256(data).hexdigest(),
                storage_key=f"{ws.id}/{uuid.uuid4().hex}",
                status=DocStatus.queued,
                created_at=datetime.now(UTC) - timedelta(days=30 - i),
            )
            await get_storage().put(doc.storage_key, data, content_type)
            async with SessionLocal() as session:
                session.add(doc)
                await session.commit()
            await self.ingestor.run(doc.id)  # the real pipeline, inline (no worker needed)
            async with SessionLocal() as session:
                fresh = await session.get(Document, doc.id)
                assert fresh is not None
                fresh.summary = spec.summary
                fresh.suggested_questions = spec.questions
                await session.commit()
                print(
                    f"  ready    {spec.filename}  ({fresh.pages_total} pages, {fresh.chunk_count} chunks)"
                )

    # ---- conversations -------------------------------------------------------------------

    async def _answer(
        self, ws: Workspace, question: str, turn: Turn | None
    ) -> tuple[str, list[dict[str, object]], bool, RetrievalResult]:
        query = turn.standalone if turn and turn.standalone else question
        result = await self.retriever.search(ws.id, query)
        top = result.top_rerank_score
        s = self.settings
        gate = GateConfig(s.relevance_threshold, s.relevance_floor, s.relevance_agree_rank)
        if decide(result.chunks, result.reranked, gate) == "refuse":  # live app's rule
            return NOT_FOUND_ANSWER, [], True, result
        sources = [c.as_source() for c in result.chunks]
        answer = turn.answer if turn else None
        if answer and turn and turn.expect:
            answer = renumber(answer, turn.expect, sources)
        if not answer and s.llm_provider == "openai":
            # Same as the live app: the LLM answers from the sources; no citation = not found.
            llm_answer = await self._llm_answer(query, sources)
            if llm_answer is not None:
                citations = build_citations(llm_answer, sources)
                if not citations:
                    return NOT_FOUND_ANSWER, [], True, result
                return llm_answer, citations, False, result
        if not answer:
            # No LLM available: quote sentences, refusing when they barely cover the question.
            if not result.reranked and question_coverage(query, sources) < MIN_COVERAGE:
                return NOT_FOUND_ANSWER, [], True, result
            answer = extractive_answer(query, sources, top)
        return answer, build_citations(answer, sources), False, result

    async def _llm_answer(self, query: str, sources: list[dict[str, object]]) -> str | None:
        await asyncio.sleep(2.5)  # stay inside free-tier rate limits (~30 requests/min)
        try:
            raw = await self.llm.complete(answer_messages(query, sources), max_tokens=500)
        except LLMError:
            return None
        text = normalise_markers(raw).strip()
        return strip_invalid_markers(text, set(range(1, len(sources) + 1)))

    async def _chats(self, ws: Workspace, chats: list[Chat], traffic: list[str]) -> None:
        now = datetime.now(UTC)
        seen: set[str] = set()
        async with SessionLocal() as session:
            for chat in chats:
                start = now - timedelta(days=chat.days_ago)
                await self._conversation(
                    session,
                    ws,
                    chat.user,
                    chat.title,
                    start,
                    chat.turns,
                    chat.feedback,
                    chat.comment,
                    seen,
                )
            # Background traffic spread across the last 30 days, from different team members.
            for i, q in enumerate(traffic):
                when = now - timedelta(days=self.rng.uniform(1, 29), hours=self.rng.uniform(0, 8))
                who = ["editor", "owner", "viewer"][i % 3]
                fb = self.rng.choice([1, 1, 1, None, None, -1]) if i % 2 == 0 else None
                await self._conversation(session, ws, who, q[:60], when, [Turn(q)], fb, None, seen)
            await session.commit()

    async def _conversation(
        self,
        session: AsyncSession,
        ws: Workspace,
        user_key: str,
        title: str,
        start: datetime,
        turns: list[Turn],
        feedback: int | None,
        comment: str | None,
        seen: set[str],
    ) -> None:
        user = self.users[user_key]
        conv = Conversation(
            workspace_id=ws.id, user_id=user.id, title=title, created_at=start, updated_at=start
        )
        session.add(conv)
        await session.flush()
        t = start
        last_answer: Message | None = None
        for turn in turns:
            answer, citations, not_found, result = await self._answer(ws, turn.question, turn)
            key = (turn.standalone or turn.question).lower().strip(" ?")
            cached = key in seen and not not_found
            seen.add(key)
            session.add(
                Message(conversation_id=conv.id, role="user", content=turn.question, created_at=t)
            )
            first = self.rng.randint(380, 1300) + result.retrieval_ms + result.rerank_ms
            total = first + self.rng.randint(700, 2600)
            if cached:
                first, total = self.rng.randint(15, 60), self.rng.randint(60, 140)
            elif not_found:
                total = first = result.retrieval_ms + result.rerank_ms + self.rng.randint(5, 30)
            last_answer = Message(
                conversation_id=conv.id,
                role="assistant",
                content=answer,
                citations=citations,
                status="complete",
                model=None if not_found else DEMO_MODEL,
                rewritten_question=turn.standalone or turn.question,
                not_found=not_found,
                cached=cached,
                prompt_tokens=None if not_found or cached else 900 + count_tokens(answer) * 3,
                completion_tokens=None if not_found or cached else count_tokens(answer),
                retrieval_ms=None if cached else result.retrieval_ms,
                rerank_ms=None if cached else result.rerank_ms,
                first_token_ms=first,
                total_ms=total,
                retrieval_debug=None if cached else [c.debug() for c in result.chunks],
                created_at=t + timedelta(seconds=2),
            )
            session.add(last_answer)
            t += timedelta(minutes=self.rng.randint(1, 6))
        conv.updated_at = t
        await session.flush()
        if feedback and last_answer and not last_answer.not_found:
            session.add(
                MessageFeedback(
                    message_id=last_answer.id,
                    user_id=user.id,
                    rating=feedback,
                    comment=comment,
                    created_at=t,
                )
            )

    def print_credentials(self) -> None:
        print("\n  Sign in with any of these (password for all: Demo@12345)")
        print("  ─────────────────────────────────────────────────────────────")
        for u, role in zip(
            USERS, ["owner of both team workspaces", "editor", "viewer"], strict=True
        ):
            print(f"  {u.email:22s} {u.name:13s} {role}")
        print("  …or click “Try the demo” on the landing page for a guest account.\n")
