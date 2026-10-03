import pytest

from app.services import auth as auth_service

from .conftest import Api


async def test_register_login_me(api: Api) -> None:
    user = await api.signup("Alice@Example.com")
    assert user["user"]["email"] == "alice@example.com"  # emails are lowercased
    r = await api.client.get("/api/auth/me", headers=user["headers"])
    assert r.status_code == 200
    assert r.json()["email"] == "alice@example.com"
    # a personal workspace is created on sign-up
    r = await api.client.get("/api/workspaces", headers=user["headers"])
    assert [w["name"] for w in r.json()["items"]] == ["Personal"]


async def test_duplicate_email_conflicts(api: Api) -> None:
    await api.signup("bob@example.com")
    r = await api.client.post(
        "/api/auth/register",
        json={"email": "BOB@example.com", "full_name": "Bob", "password": "password123"},
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "email_taken"
    assert r.json()["error"]["request_id"]


async def test_login_errors_do_not_reveal_which_emails_exist(api: Api) -> None:
    await api.signup("carol@example.com")
    wrong_pw = await api.client.post(
        "/api/auth/login", json={"email": "carol@example.com", "password": "nope-nope"}
    )
    no_user = await api.client.post(
        "/api/auth/login", json={"email": "nobody@example.com", "password": "nope-nope"}
    )
    assert wrong_pw.status_code == no_user.status_code == 401
    assert wrong_pw.json()["error"]["message"] == no_user.json()["error"]["message"]


async def test_protected_routes_need_a_valid_token(api: Api) -> None:
    assert (await api.client.get("/api/auth/me")).status_code == 401
    r = await api.client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "token_expired"


async def test_refresh_rotates_and_reuse_revokes_family(
    api: Api, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(auth_service, "REUSE_GRACE_SECONDS", 0)
    user = await api.signup()
    first = user["refresh_cookie"]
    assert first

    r1 = await api.refresh(first)
    assert r1.status_code == 200
    second = r1.cookies.get("docmind_refresh")
    assert second and second != first
    assert r1.json()["access_token"]

    # Replaying the rotated token = theft signal: it fails and kills the whole family...
    replay = await api.refresh(first)
    assert replay.status_code == 401
    assert replay.json()["error"]["code"] == "session_reused"
    # ...including the legitimately rotated token.
    r2 = await api.refresh(second)
    assert r2.status_code == 401


async def test_concurrent_refresh_within_grace_is_not_treated_as_theft(api: Api) -> None:
    user = await api.signup()
    first = user["refresh_cookie"]
    a = await api.refresh(first)
    b = await api.refresh(first)
    assert a.status_code == b.status_code == 200
    # The family is still alive
    c = await api.refresh(a.cookies["docmind_refresh"])
    assert c.status_code == 200


async def test_logout_revokes_refresh_token(api: Api) -> None:
    user = await api.signup()
    token = user["refresh_cookie"]
    api.client.cookies.set("docmind_refresh", token, path="/api/auth")
    r = await api.client.post("/api/auth/logout")
    assert r.status_code == 204
    r = await api.refresh(token)
    assert r.status_code == 401


async def test_password_rules(api: Api) -> None:
    r = await api.client.post(
        "/api/auth/register", json={"email": "d@example.com", "full_name": "D", "password": "short"}
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"
    r = await api.client.post(
        "/api/auth/register",
        json={"email": "d@example.com", "full_name": "D", "password": "é" * 40},
    )
    assert r.status_code == 422  # 80 bytes > bcrypt's 72-byte limit
