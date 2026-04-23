import time
from typing import Any, Dict, Optional


def _base_response() -> Dict[str, Any]:
    return {
        "code": 0,
        "message": "ok",
        "timestamp": int(time.time()),
    }


def public_response(data: Any) -> Dict[str, Any]:
    response = _base_response()
    response["data"] = data
    return response


def mp_response(data: Any, user_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    response = public_response(data)
    if user_info is not None:
        response["user_info"] = user_info
    return response


def error_response(code: int, message: str) -> Dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "timestamp": int(time.time()),
    }

