import base64
import hashlib
import hmac
import json
import time

from app.core.errors import AuthError


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


def _sign(message: bytes, secret: str) -> str:
    return _b64url_encode(hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest())


def issue_access_token(*, user_id: int, openid: str, secret: str, ttl_seconds: int = 86400, now: int = None) -> str:
    now = now or int(time.time())
    payload = {
        "user_id": user_id,
        "openid": openid,
        "iat": now,
        "exp": now + ttl_seconds,
    }
    payload_segment = _b64url_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signature = _sign(payload_segment.encode("utf-8"), secret)
    return "{}.{}".format(payload_segment, signature)


def parse_access_token(token: str, *, secret: str, now: int = None) -> dict:
    now = now or int(time.time())
    try:
        payload_segment, signature = token.split(".", 1)
    except ValueError as exc:
        raise AuthError(message="invalid access token") from exc

    expected_signature = _sign(payload_segment.encode("utf-8"), secret)
    if not hmac.compare_digest(signature, expected_signature):
        raise AuthError(message="invalid access token")

    try:
        payload = json.loads(_b64url_decode(payload_segment).decode("utf-8"))
    except Exception as exc:
        raise AuthError(message="invalid access token") from exc

    if now >= int(payload.get("exp", 0)):
        raise AuthError(message="access token expired")
    if "user_id" not in payload or "openid" not in payload:
        raise AuthError(message="invalid access token")
    return payload


def extract_bearer_token(authorization: str) -> str:
    if not authorization:
        return ""
    prefix = "bearer "
    if authorization.lower().startswith(prefix):
        return authorization[len(prefix):].strip()
    return ""
