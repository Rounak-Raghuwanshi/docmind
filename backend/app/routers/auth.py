from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.deps import DB, CurrentUser, rate_limit
from app.errors import Unauthorized, error_body
from app.schemas.auth import LoginIn, RegisterIn, TokenOut, UserOut
from app.services import auth as service

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_refresh_cookie(response: Response, token: str) -> None:
    s = get_settings()
    response.set_cookie(
        s.refresh_cookie_name,
        token,
        max_age=s.refresh_token_days * 86400,
        httponly=True,
        secure=s.cookie_secure,
        samesite=s.cookie_samesite,
        path="/api/auth",  # the cookie is only ever sent to the auth endpoints
    )


def _clear_refresh_cookie(response: Response) -> None:
    s = get_settings()
    response.delete_cookie(
        s.refresh_cookie_name, path="/api/auth", secure=s.cookie_secure, samesite=s.cookie_samesite
    )


def _token_out(sess: service.Session, response: Response) -> TokenOut:
    _set_refresh_cookie(response, sess.refresh_token)
    response.headers["Cache-Control"] = "no-store"
    return TokenOut(
        access_token=sess.access_token,
        expires_in=sess.expires_in,
        user=UserOut.model_validate(sess.user),
    )


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=UserOut,
    dependencies=[Depends(rate_limit("login", per_user=False))],
)
async def register(body: RegisterIn, session: DB) -> UserOut:
    user = await service.register(session, body.email, body.full_name, body.password)
    return UserOut.model_validate(user)


@router.post(
    "/login", response_model=TokenOut, dependencies=[Depends(rate_limit("login", per_user=False))]
)
async def login(body: LoginIn, session: DB, response: Response) -> TokenOut:
    return _token_out(await service.login(session, body.email, body.password), response)


@router.post(
    "/demo", response_model=TokenOut, dependencies=[Depends(rate_limit("demo", per_user=False))]
)
async def demo_login(session: DB, response: Response) -> TokenOut:
    """Creates a guest account with viewer access to the public demo workspace."""
    return _token_out(await service.create_demo_guest(session), response)


@router.post("/refresh", response_model=TokenOut)
async def refresh(request: Request, session: DB, response: Response) -> TokenOut | JSONResponse:
    raw = request.cookies.get(get_settings().refresh_cookie_name)
    try:
        sess = await service.refresh(session, raw)
    except Unauthorized as e:
        # Clear the dead cookie so the browser stops presenting it.
        failed = JSONResponse(error_body(e.code, e.message), status_code=e.status_code)
        _clear_refresh_cookie(failed)
        return failed
    return _token_out(sess, response)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, session: DB) -> Response:
    await service.logout(session, request.cookies.get(get_settings().refresh_cookie_name))
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_refresh_cookie(response)
    return response


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
