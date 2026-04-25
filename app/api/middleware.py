import json
import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from app.core.errors import AppError
from app.core.response import error_response

logger = logging.getLogger(__name__)


def _should_log_payloads(request: Request) -> bool:
    settings = request.app.state.settings
    if not settings.log_all_api_payloads:
        return False
    return request.url.path.startswith("/api/") or request.url.path in {"/healthz", "/readyz"}


def _decode_payload(body: bytes, content_type: str):
    if not body:
        return None
    if "application/json" in (content_type or ""):
        try:
            return json.loads(body.decode("utf-8"))
        except Exception:
            return body.decode("utf-8", errors="replace")
    if "text/" in (content_type or ""):
        return body.decode("utf-8", errors="replace")
    return "<{} bytes>".format(len(body))


def register_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        request.state.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.started_at = time.time()
        should_log_payloads = _should_log_payloads(request)
        request_body = b""

        if should_log_payloads:
            request_body = await request.body()

            async def receive():
                return {"type": "http.request", "body": request_body, "more_body": False}

            request._receive = receive
            logger.info(
                "api.request request_id=%s method=%s path=%s query=%s headers=%s body=%s",
                request.state.request_id,
                request.method,
                request.url.path,
                request.url.query,
                {
                    "X-Login-Code": request.headers.get("X-Login-Code"),
                    "X-System-Version": request.headers.get("X-System-Version"),
                    "X-Device-UUID": request.headers.get("X-Device-UUID"),
                    "X-Request-ID": request.headers.get("X-Request-ID"),
                },
                _decode_payload(request_body, request.headers.get("content-type", "")),
            )

        response = await call_next(request)

        if should_log_payloads:
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk
            logger.info(
                "api.response request_id=%s method=%s path=%s status_code=%s duration_ms=%s body=%s",
                request.state.request_id,
                request.method,
                request.url.path,
                response.status_code,
                int((time.time() - request.state.started_at) * 1000),
                _decode_payload(response_body, response.headers.get("content-type", "")),
            )
            response = Response(
                content=response_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
                background=response.background,
            )
        response.headers["X-Request-ID"] = request.state.request_id
        return response


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(exc.code, exc.message),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=error_response(5000, "internal server error"),
        )
