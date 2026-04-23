from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.middleware import register_exception_handlers
from app.core.errors import ValidationError


def test_app_error_is_mapped_to_swagger_style_json():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    def boom():
        raise ValidationError("bad request")

    client = TestClient(app)
    response = client.get("/boom")

    assert response.status_code == 400
    assert response.json()["code"] == 1001
    assert response.json()["message"] == "bad request"

