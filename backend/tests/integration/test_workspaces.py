from tests.factories import make_pdf

from .conftest import Api


async def _workspace_with_member(api: Api, role: str) -> tuple[dict, dict, str]:
    owner = await api.signup()
    member = await api.signup()
    r = await api.client.post("/api/workspaces", headers=owner["headers"], json={"name": "Team"})
    assert r.status_code == 201
    ws = r.json()["id"]
    r = await api.client.post(
        f"/api/workspaces/{ws}/invites", headers=owner["headers"], json={"role": role}
    )
    assert r.status_code == 201
    token = r.json()["token"]
    assert r.json()["url"].endswith(f"/invite/{token}")
    r = await api.client.get(f"/api/invites/{token}", headers=member["headers"])
    assert r.json()["workspace_name"] == "Team"
    r = await api.client.post(f"/api/invites/{token}/accept", headers=member["headers"])
    assert r.status_code == 200
    assert r.json()["role"] == role
    return owner, member, ws


async def test_invite_is_single_use(api: Api) -> None:
    owner = await api.signup()
    a, b = await api.signup(), await api.signup()
    ws = await api.personal_workspace(owner)
    token = (
        await api.client.post(f"/api/workspaces/{ws}/invites", headers=owner["headers"], json={})
    ).json()["token"]
    assert (
        await api.client.post(f"/api/invites/{token}/accept", headers=a["headers"])
    ).status_code == 200
    r = await api.client.post(f"/api/invites/{token}/accept", headers=b["headers"])
    assert r.status_code == 410
    assert r.json()["error"]["code"] == "invite_used"


async def test_viewer_cannot_upload_but_can_read(api: Api) -> None:
    _, viewer, ws = await _workspace_with_member(api, "viewer")
    r = await api.upload(viewer, ws, "a.pdf", make_pdf())
    assert r.status_code == 403
    assert (
        await api.client.get(f"/api/workspaces/{ws}/documents", headers=viewer["headers"])
    ).status_code == 200


async def test_editor_can_upload(api: Api) -> None:
    _, editor, ws = await _workspace_with_member(api, "editor")
    r = await api.upload(editor, ws, "a.pdf", make_pdf())
    assert r.status_code == 202


async def test_strangers_get_404_not_403(api: Api) -> None:
    owner = await api.signup()
    stranger = await api.signup()
    ws = await api.personal_workspace(owner)
    doc = (await api.upload(owner, ws, "a.pdf", make_pdf())).json()["id"]

    for path in (
        f"/api/workspaces/{ws}",
        f"/api/workspaces/{ws}/documents",
        f"/api/documents/{doc}",
        f"/api/documents/{doc}/file",
    ):
        r = await api.client.get(path, headers=stranger["headers"])
        assert r.status_code == 404, path
    r = await api.client.delete(f"/api/documents/{doc}", headers=stranger["headers"])
    assert r.status_code == 404
    r = await api.client.post(
        f"/api/workspaces/{ws}/search", headers=stranger["headers"], json={"query": "x"}
    )
    assert r.status_code == 404


async def test_only_owner_manages_members_and_last_owner_is_protected(api: Api) -> None:
    owner, editor, ws = await _workspace_with_member(api, "editor")
    eid, oid = editor["user"]["id"], owner["user"]["id"]

    r = await api.client.patch(
        f"/api/workspaces/{ws}/members/{oid}", headers=editor["headers"], json={"role": "viewer"}
    )
    assert r.status_code == 403
    r = await api.client.patch(
        f"/api/workspaces/{ws}/members/{oid}", headers=owner["headers"], json={"role": "viewer"}
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "last_owner"
    r = await api.client.patch(
        f"/api/workspaces/{ws}/members/{eid}", headers=owner["headers"], json={"role": "viewer"}
    )
    assert r.status_code == 200 and r.json()["role"] == "viewer"

    members = (
        await api.client.get(f"/api/workspaces/{ws}/members", headers=editor["headers"])
    ).json()
    assert {m["role"] for m in members} == {"owner", "viewer"}

    # a member can leave on their own
    assert (
        await api.client.delete(f"/api/workspaces/{ws}/members/{eid}", headers=editor["headers"])
    ).status_code == 204
    assert (
        await api.client.get(f"/api/workspaces/{ws}", headers=editor["headers"])
    ).status_code == 404


async def test_rename_and_delete_workspace(api: Api) -> None:
    owner = await api.signup()
    ws = (
        await api.client.post("/api/workspaces", headers=owner["headers"], json={"name": "Old"})
    ).json()["id"]
    r = await api.client.patch(
        f"/api/workspaces/{ws}", headers=owner["headers"], json={"name": "New"}
    )
    assert r.json()["name"] == "New"
    assert (
        await api.client.delete(f"/api/workspaces/{ws}", headers=owner["headers"])
    ).status_code == 204
    personal = await api.personal_workspace(owner)
    r = await api.client.delete(f"/api/workspaces/{personal}", headers=owner["headers"])
    assert r.status_code == 400
