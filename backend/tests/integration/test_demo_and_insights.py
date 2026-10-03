from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import Conversation, Document, Message, MessageFeedback, User, Workspace
from app.seed.run import DEMO_PASSWORD, Seeder
from tests.factories import make_pdf

from .conftest import Api, ingest


async def test_seed_creates_data_for_every_feature(api: Api) -> None:
    await Seeder(reset=False).run()
    async with SessionLocal() as s:
        demo = (await s.execute(select(Workspace).where(Workspace.is_demo))).scalar_one()
        assert demo.name.startswith("Demo")
        ready = await s.scalar(select(func.count()).where(Document.status == "ready"))
        assert ready >= 7
        assert await s.scalar(select(func.count()).select_from(Conversation)) > 20
        assert await s.scalar(select(func.count()).where(Message.not_found)) >= 1
        assert await s.scalar(select(func.count()).where(Message.cached)) >= 1
        assert await s.scalar(select(func.count()).select_from(MessageFeedback)) > 5
        # every citation in seeded answers points at a real chunk of a real document
        msgs = (await s.execute(select(Message).where(Message.role == "assistant"))).scalars().all()
        doc_ids = {str(d) for d in (await s.execute(select(Document.id))).scalars()}
        assert all(c["document_id"] in doc_ids for m in msgs for c in m.citations)

    # seeded users can log in; running the seeder again is a no-op
    r = await api.client.post(
        "/api/auth/login", json={"email": "aarav@docmind.dev", "password": DEMO_PASSWORD}
    )
    assert r.status_code == 200
    api.client.cookies.clear()
    await Seeder(reset=False).run()
    async with SessionLocal() as s:
        assert await s.scalar(select(func.count()).where(User.email == "aarav@docmind.dev")) == 1


async def test_demo_login_gives_guest_viewer_access_and_showcase_chats(api: Api) -> None:
    await Seeder(reset=False).run()
    r = await api.client.post("/api/auth/demo")
    api.client.cookies.clear()
    assert r.status_code == 200, r.text
    assert r.json()["user"]["is_guest"] is True
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    workspaces = (await api.client.get("/api/workspaces", headers=headers)).json()["items"]
    demo = next(w for w in workspaces if w["is_demo"])
    assert demo["role"] == "viewer"
    convs = (
        await api.client.get(f"/api/workspaces/{demo['id']}/conversations", headers=headers)
    ).json()["items"]
    assert len(convs) == 3
    detail = (await api.client.get(f"/api/conversations/{convs[0]['id']}", headers=headers)).json()
    assert any(m["citations"] for m in detail["messages"])

    # in the public demo, viewers may read analytics and insights; they still can't upload
    assert (
        await api.client.get(f"/api/workspaces/{demo['id']}/analytics", headers=headers)
    ).status_code == 200
    assert (
        await api.client.get(f"/api/workspaces/{demo['id']}/insights", headers=headers)
    ).status_code == 200
    r = await api.upload({"headers": headers}, demo["id"], "x.pdf", make_pdf())
    assert r.status_code == 403


async def test_demo_login_without_demo_workspace_explains_how_to_fix(api: Api) -> None:
    r = await api.client.post("/api/auth/demo")
    assert r.status_code == 404
    assert "make seed" in r.json()["error"]["message"]


async def test_viewer_of_normal_workspace_cannot_read_insights(api: Api) -> None:
    owner, viewer = await api.signup(), await api.signup()
    ws = (
        await api.client.post("/api/workspaces", headers=owner["headers"], json={"name": "T"})
    ).json()["id"]
    token = (
        await api.client.post(f"/api/workspaces/{ws}/invites", headers=owner["headers"], json={})
    ).json()["token"]
    await api.client.post(f"/api/invites/{token}/accept", headers=viewer["headers"])
    assert (
        await api.client.get(f"/api/workspaces/{ws}/insights", headers=viewer["headers"])
    ).status_code == 403
    assert (
        await api.client.get(f"/api/workspaces/{ws}/analytics", headers=viewer["headers"])
    ).status_code == 403


async def test_insights_projects_embeddings_and_analyses_answers(api: Api, ingestor) -> None:  # type: ignore[no-untyped-def]
    user = await api.signup()
    ws = await api.personal_workspace(user)
    doc = (await api.upload(user, ws, "tax-guide.pdf", make_pdf())).json()["id"]
    await ingest(ingestor, doc)
    conv = (
        await api.client.post(
            f"/api/workspaces/{ws}/conversations", headers=user["headers"], json={}
        )
    ).json()["id"]
    await api.ask(user, conv, "What deduction does section 80D allow for health insurance?")
    await api.ask(user, conv, "Who won the football world cup in 1998?")

    data = (await api.client.get(f"/api/workspaces/{ws}/insights", headers=user["headers"])).json()
    assert len(data["points"]) == 3
    for p in data["points"]:
        assert -1.0 <= p["x"] <= 1.0 and -1.0 <= p["y"] <= 1.0 and -1.0 <= p["z"] <= 1.0
        assert p["filename"] == "tax-guide.pdf"
    assert abs(sum(data["explained_variance"]) - 1.0) < 1e-3  # 3 points: 3 components explain all
    assert sum(data["retrieval_sources"].values()) >= 1
    assert sum(b["answered"] for b in data["confidence"]) == 1
    assert sum(b["not_found"] for b in data["confidence"]) == 1
    assert data["knowledge_gaps"][0]["question"].startswith("Who won")
    assert data["coverage"][0]["answers"] == 1
    assert data["highlights"]
