import logging

from app.core.config import Settings
from app.main import create_app


def test_app_boot_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_static_report_preview_page_is_accessible(client):
    response = client.get("/static/report-preview.html")
    assert response.status_code == 200
    assert "报告预览" in response.text


def test_static_admin_distributor_page_is_accessible(client):
    response = client.get("/static/admin-distributor.html")
    assert response.status_code == 200
    assert "分销申请审批台" in response.text


def test_static_admin_quota_allocation_page_is_accessible(client):
    response = client.get("/static/admin-quota-allocation.html")
    assert response.status_code == 200
    assert "分销配额分配台" in response.text


def test_static_admin_downline_assignment_page_is_accessible(client):
    response = client.get("/static/admin-downline-assignment.html")
    assert response.status_code == 200
    assert "下级代理分配台" in response.text


def test_static_admin_dashboard_page_is_accessible(client):
    response = client.get("/static/admin-dashboard.html")
    assert response.status_code == 200
    assert "管理后台" in response.text


def test_static_admin_withdrawals_page_is_accessible(client):
    response = client.get("/static/admin-withdrawals.html")
    assert response.status_code == 200
    assert "提现审核台" in response.text


def test_static_admin_operation_balance_page_is_accessible(client):
    response = client.get("/static/admin-operation-balance.html")
    assert response.status_code == 200
    assert "运营账户余额看板" in response.text


def test_app_startup_logs_environment(caplog, tmp_path):
    settings = Settings(
        app_env="development",
        database_url="sqlite+pysqlite:///{}".format(tmp_path / "startup.db"),
        encryption_key="0123456789abcdef0123456789abcdef",
        allow_ephemeral_db=True,
    )

    with caplog.at_level(logging.INFO):
        app = create_app(settings)

    try:
        messages = [record.getMessage() for record in caplog.records]
        assert any("startup.settings" in message for message in messages)
        assert any("startup.wechat_auth_client NullWechatAuthClient" in message for message in messages)
        env_logs = [message for message in messages if "startup.environ " in message]
        assert env_logs
        assert all("startup.environ " in message and "=" in message for message in env_logs)
    finally:
        app.state.engine.dispose()
