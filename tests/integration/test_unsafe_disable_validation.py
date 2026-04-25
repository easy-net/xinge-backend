from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.base import Base
from app.main import create_app


def test_unsafe_disable_validation_allows_create_report_without_login_or_headers(tmp_path):
    settings = Settings(
        app_env="development",
        database_url="sqlite+pysqlite:///{}".format(tmp_path / "unsafe.db"),
        encryption_key="0123456789abcdef0123456789abcdef",
        allow_ephemeral_db=True,
        unsafe_disable_validation=True,
    )
    app = create_app(settings)
    Base.metadata.create_all(app.state.engine)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/mp/reports",
                json={
                    "name": "张三",
                    "school_name": "北京大学",
                    "study_path_priority": ["国内读研"],
                    "employment_intention": ["名企大厂"],
                    "target_major": ["软件工程"],
                    "target_work_city": ["北京"],
                },
            )

        assert response.status_code == 201
        payload = response.json()
        assert payload["data"]["name"] == "张三"
        assert payload["user_info"]["open_id"] == "unsafe-openid-unsafe-login-code"
    finally:
        Base.metadata.drop_all(app.state.engine)
        app.state.engine.dispose()


def test_unsafe_disable_validation_returns_mock_links_for_missing_report(tmp_path):
    settings = Settings(
        app_env="development",
        database_url="sqlite+pysqlite:///{}".format(tmp_path / "unsafe-links.db"),
        encryption_key="0123456789abcdef0123456789abcdef",
        allow_ephemeral_db=True,
        unsafe_disable_validation=True,
    )
    app = create_app(settings)
    Base.metadata.create_all(app.state.engine)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/mp/reports/links",
                json={"report_id": 9999},
            )

        assert response.status_code == 200
        payload = response.json()["data"]
        assert payload["report_id"] == 9999
        assert payload["is_paid"] is True
        assert payload["preview_h5_url"].endswith("/static/report-preview.html?report_id=9999&mode=preview")
        assert payload["full_h5_url"].endswith("/static/report-preview.html?report_id=9999&mode=full")
        assert payload["pdf_url"].endswith("/static/report-preview.html?report_id=9999&mode=pdf")
    finally:
        Base.metadata.drop_all(app.state.engine)
        app.state.engine.dispose()
