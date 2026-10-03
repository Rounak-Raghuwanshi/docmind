"""Operational commands.

python -m app.cli seed                              # full demo data for every feature
python -m app.cli seed --reset                      # wipe and recreate the demo data
python -m app.cli seed-demo --docs ./demo-docs      # demo workspace from your own files
python -m app.cli reindex                           # re-embed docs from another model
python -m app.cli reindex --all                     # re-embed everything (e.g. new chunking)
"""

import argparse
import asyncio
import secrets
import sys
from pathlib import Path

from redis.exceptions import RedisError
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal, engine
from app.errors import AppError
from app.models import Document, Role, User, Workspace, WorkspaceMember
from app.redis_client import close_redis, get_redis
from app.repositories.users import get_by_email
from app.security import hash_password
from app.services.auth import create_personal_workspace
from app.services.documents import add_document, enqueue_ingestion

DEMO_OWNER = "demo-owner@docmind.local"


async def seed_demo(docs_dir: Path, name: str) -> None:
    files = sorted(
        p for p in docs_dir.iterdir() if p.suffix.lower() in {".pdf", ".docx", ".txt", ".md"}
    )
    if not files:
        sys.exit(f"No PDF/DOCX/TXT/MD files in {docs_dir}")
    async with SessionLocal() as session:
        owner = await get_by_email(session, DEMO_OWNER)
        if owner is None:
            owner = User(
                email=DEMO_OWNER,
                full_name="DocMind Demo",
                hashed_password=hash_password(secrets.token_urlsafe(24)),  # nobody logs in as it
            )
            session.add(owner)
            await session.flush()
            await create_personal_workspace(session, owner)
        ws = (
            await session.execute(
                select(Workspace).where(Workspace.owner_id == owner.id, Workspace.name == name)
            )
        ).scalar_one_or_none()
        if ws is None:
            # Only one workspace can be the public demo.
            for other in (
                await session.execute(select(Workspace).where(Workspace.is_demo))
            ).scalars():
                other.is_demo = False
            await session.flush()
            ws = Workspace(name=name, owner_id=owner.id, is_demo=True)
            session.add(ws)
            await session.flush()
            session.add(WorkspaceMember(workspace_id=ws.id, user_id=owner.id, role=Role.owner))
        await session.commit()

        for path in files:
            try:
                doc = await add_document(
                    session, get_redis(), ws.id, owner, path.name, path.read_bytes()
                )
                print(f"  queued   {path.name}  ({doc.id})")
            except AppError as e:
                print(f"  skipped  {path.name}: {e.message}")
            except (RedisError, OSError):
                # Saved as "queued"; the worker re-enqueues queued documents when it starts.
                print(f"  saved    {path.name}  (queue unreachable: restart the worker to process)")

    print(f"\nDemo workspace ready: {ws.id}")
    print(f"Set DEMO_WORKSPACE_ID={ws.id} on the API so 'Try the demo' works.")
    print("Documents are processed by the worker; watch them in the UI or the worker logs.")


async def reindex(all_docs: bool) -> None:
    model = get_settings().embedding_model
    async with SessionLocal() as session:
        stmt = select(Document.id)
        if not all_docs:
            stmt = stmt.where(
                (Document.embedding_model != model) | Document.embedding_model.is_(None)
            )
        ids = list((await session.execute(stmt)).scalars())
    for doc_id in ids:
        await enqueue_ingestion(doc_id)
    print(f"Queued {len(ids)} document(s) for re-indexing with {model}")


async def _main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    full = sub.add_parser("seed", help="create demo users, workspaces, documents and chats")
    full.add_argument("--reset", action="store_true", help="delete existing demo data first")
    seed = sub.add_parser("seed-demo", help="create the public demo workspace from a folder")
    seed.add_argument("--docs", type=Path, required=True)
    seed.add_argument("--name", default="Demo: India Tax & GST")
    re = sub.add_parser("reindex", help="re-embed documents")
    re.add_argument(
        "--all", action="store_true", help="re-embed every document, not just stale ones"
    )
    args = parser.parse_args()
    try:
        if args.cmd == "seed":
            from app.seed.run import Seeder

            await Seeder(reset=args.reset).run()
        elif args.cmd == "seed-demo":
            await seed_demo(args.docs, args.name)
        elif args.cmd == "reindex":
            await reindex(args.all)
    finally:
        await close_redis()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(_main())
