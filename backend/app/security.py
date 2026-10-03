"""Password hashing, JWT access tokens and opaque refresh/invite tokens."""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.config import get_settings

BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    raw = password.encode()
    if len(raw) > BCRYPT_MAX_BYTES:
        # Validated at the schema layer too; bcrypt silently truncates otherwise.
        raise ValueError("password exceeds 72 bytes")
    return bcrypt.hashpw(raw, bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, hashed: str) -> bool:
    raw = password.encode()
    if len(raw) > BCRYPT_MAX_BYTES:
        return False
    return bcrypt.checkpw(raw, hashed.encode())


# A real bcrypt hash used to burn the same CPU time when the email doesn't exist,
# so response timing doesn't reveal which emails are registered.
_DUMMY_HASH = bcrypt.hashpw(b"timing-equaliser", bcrypt.gensalt(rounds=12)).decode()


def burn_password_check(password: str) -> None:
    verify_password(password, _DUMMY_HASH)


def create_access_token(user_id: uuid.UUID) -> tuple[str, int]:
    s = get_settings()
    now = datetime.now(UTC)
    expires_in = s.access_token_minutes * 60
    claims = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
        "jti": secrets.token_hex(8),
    }
    token = jwt.encode(claims, s.jwt_secret_key.get_secret_value(), algorithm=s.jwt_algorithm)
    return token, expires_in


def decode_access_token(token: str) -> uuid.UUID | None:
    s = get_settings()
    try:
        claims = jwt.decode(
            token,
            s.jwt_secret_key.get_secret_value(),
            algorithms=[s.jwt_algorithm],
            options={"require": ["exp", "sub", "type"]},
        )
    except jwt.PyJWTError:
        return None
    if claims.get("type") != "access":
        return None
    try:
        return uuid.UUID(claims["sub"])
    except ValueError:
        return None


def new_opaque_token() -> str:
    """256 bits of randomness, URL-safe."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Opaque tokens are stored only as SHA-256; a DB leak doesn't leak usable tokens."""
    return hashlib.sha256(token.encode()).hexdigest()
