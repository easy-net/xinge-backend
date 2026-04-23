from app.db.models.product_config import ProductConfig
from app.services.order_service import OrderService
from tests.fixtures.fakes import FakeWechatPayClient


class UserStub:
    def __init__(self, user_id, openid):
        self.id = user_id
        self.openid = openid


def seed_product_config(db_session):
    db_session.add(
        ProductConfig(
            current_amount=9900,
            current_amount_display="99.00",
            description="完整版学业规划报告",
            discount_rate=0.5,
            is_limited_time=True,
            limited_time_end="2026-05-01T00:00:00Z",
            original_amount=19900,
            original_amount_display="199.00",
            display_count=12345,
            display_text="已有12345位同学使用",
        )
    )
    db_session.commit()


def test_create_order_returns_payment_params(db_session):
    from app.services.auth_service import AuthService
    from tests.fixtures.fakes import FakeWechatAuthClient

    class Context:
        login_code = "login-code-user-1"
        system_version = "iOS 17.0"
        device_uuid = "device-1"

    auth_service = AuthService(
        db_session,
        FakeWechatAuthClient(session_map={"login-code-user-1": ("openid-user-1", "unionid-user-1")}),
    )
    _, user_info = auth_service.login(Context(), None)

    from app.services.report_service import ReportService

    report_service = ReportService(db_session)
    report = report_service.create_report(
        user=UserStub(user_info["user_id"], "openid-user-1"),
        payload={"name": "张三", "school_name": "北京大学"},
    )
    seed_product_config(db_session)

    service = OrderService(db_session, FakeWechatPayClient())
    data = service.create_order(user=UserStub(user_info["user_id"], "openid-user-1"), report_id=report["report_id"], amount=9900)

    assert data["amount"] == 9900
    assert data["payment_params"]["signType"] == "RSA"
    assert data["order_id"].startswith("ORD")

