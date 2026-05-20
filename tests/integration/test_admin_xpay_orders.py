from app.db.models.product_config import ProductConfig

from tests.integration.test_mp_reports_crud import auth_headers, create_logged_in_report


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


def test_admin_query_xpay_order_returns_wechat_and_local_order(client, db_session):
    seed_product_config(db_session)
    report_response = create_logged_in_report(client)
    report_id = report_response.json()["data"]["report_id"]
    order_response = client.post(
        "/api/v1/mp/orders",
        headers=auth_headers(),
        json={"report_id": report_id, "amount": 9900},
    )
    order_id = order_response.json()["data"]["order_id"]

    response = client.get(
        "/api/v1/admin/xpay/orders/query",
        params={"order_id": order_id, "openid": "openid-user-1"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["query"]["order_id"] == order_id
    assert data["xpay_order"]["is_paid"] is True
    assert data["xpay_order"]["amount"] == 9900
    assert data["local_order"]["order_id"] == order_id
    assert data["local_order"]["status"] == "pending"
    assert data["report"]["report_id"] == report_id
    assert data["user"]["openid"] == "openid-user-1"
