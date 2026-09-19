from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.core.settings import get_settings

_password_hash = PasswordHash.recommended()
_jwt_algorithm = "HS256"


class InvalidAccessToken(ValueError):
    """Raised when a bearer token cannot identify a valid user."""


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_hash.verify(password, password_hash)


def create_access_token(user_id: UUID) -> str:
    settings = get_settings()
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "exp": expires_at}
    return jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm=_jwt_algorithm)


def parse_access_token(token: str) -> UUID:
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[_jwt_algorithm],
            options={"require": ["sub", "exp"]},
        )
        return UUID(payload["sub"])
    except (InvalidTokenError, KeyError, ValueError) as error:
        raise InvalidAccessToken from error
