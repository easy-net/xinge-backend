import pytest

from app.core.auth_tokens import extract_bearer_token, issue_access_token, parse_access_token
from app.core.errors import AuthError


def test_issue_and_parse_access_token_round_trip():
    token = issue_access_token(
        user_id=42,
        openid="openid-user-1",
        secret="0123456789abcdef0123456789abcdef",
        ttl_seconds=3600,
        now=1000,
    )

    payload = parse_access_token(
        token,
        secret="0123456789abcdef0123456789abcdef",
        now=1200,
    )

    assert payload["user_id"] == 42
    assert payload["openid"] == "openid-user-1"


def test_parse_access_token_rejects_expired_token():
    token = issue_access_token(
        user_id=42,
        openid="openid-user-1",
        secret="0123456789abcdef0123456789abcdef",
        ttl_seconds=10,
        now=1000,
    )

    with pytest.raises(AuthError, match="expired"):
        parse_access_token(
            token,
            secret="0123456789abcdef0123456789abcdef",
            now=1010,
        )


def test_extract_bearer_token():
    assert extract_bearer_token("Bearer abc.def") == "abc.def"
    assert extract_bearer_token("bearer abc.def") == "abc.def"
    assert extract_bearer_token("Token abc.def") == ""
