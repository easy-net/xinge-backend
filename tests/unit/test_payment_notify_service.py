from app.db.models.product_config import ProductConfig
from app.services.auth_service import AuthService
from app.services.order_service import OrderService
from app.services.payment_notify_service import PaymentNotifyService
from app.services.report_service import ReportService
from tests.fixtures.fakes import FakeWechatAuthClient, FakeWechatPayClient


class Context:
    login_code = "login-code-user-1"
    system_version = "iOS 17.0"
    device_uuid = "device-1"


class UserStub:
    def __init__(self, user_id, openid):
        self.id = user_id
        self.openid = openid


def seed_order_ready_state(db_session):
    auth_service = AuthService(
        db_session,
        FakeWechatAuthClient(session_map={"login-code-user-1": ("openid-user-1", "unionid-user-1")}),
    )
    _, user_info = auth_service.login(Context(), None)
    user = UserStub(user_info["user_id"], "openid-user-1")

    report = ReportService(db_session).create_report(
        user=user,
        payload={"name": "张三", "school_name": "北京大学"},
    )
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
    order = OrderService(db_session, FakeWechatPayClient()).create_order(user=user, report_id=report["report_id"], amount=9900)
    return user, report, order


def test_payment_notify_marks_order_paid_idempotently(db_session):
    _, _, order = seed_order_ready_state(db_session)
    service = PaymentNotifyService(db_session, FakeWechatPayClient())

    payload = {
        "notify_id": "notify-001",
        "order_id": order["order_id"],
        "amount": 9900,
        "status": "success",
        "paid_at": "2026-04-20T10:00:00Z",
    }
    first = service.process(payload)
    second = service.process(payload)

    assert first["code"] == "SUCCESS"
    assert second["code"] == "SUCCESS"
