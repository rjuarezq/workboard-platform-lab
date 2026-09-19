from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from app.core.security import InvalidAccessToken, create_access_token, parse_access_token
from app.core.settings import get_settings


def test_token_roundtrip():
    user_id = uuid4()
    assert parse_access_token(create_access_token(user_id)) == user_id


@pytest.mark.parametrize(
    "payload",
    [
        {"sub": str(uuid4())},
        {"exp": datetime.now(UTC) + timedelta(minutes=10)},
        {"sub": "not-a-uuid", "exp": datetime.now(UTC) + timedelta(minutes=10)},
        {"sub": str(uuid4()), "exp": datetime.now(UTC) - timedelta(minutes=1)},
        {"sub": None, "exp": datetime.now(UTC) + timedelta(minutes=10)},
    ],
)
def test_invalid_claims_are_rejected(payload):
    token = jwt.encode(payload, get_settings().jwt_secret.get_secret_value(), algorithm="HS256")
    with pytest.raises(InvalidAccessToken):
        parse_access_token(token)


def test_invalid_signature_is_rejected():
    token = jwt.encode(
        {"sub": str(uuid4()), "exp": datetime.now(UTC) + timedelta(minutes=10)},
        "different-signing-secret-long-enough",
        algorithm="HS256",
    )
    with pytest.raises(InvalidAccessToken):
        parse_access_token(token)
