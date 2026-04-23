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


def test_payment_notify_updates_order_and_report_status_flow(client, db_session):
    seed_product_config(db_session)
    report_response = create_logged_in_report(client)
    report_id = report_response.json()["data"]["report_id"]
    order_response = client.post("/api/v1/mp/orders", headers=auth_headers(), json={"report_id": report_id, "amount": 9900})
    order_id = order_response.json()["data"]["order_id"]

    notify_response = client.post(
        "/api/v1/mp/orders/notify/wechat",
        json={
            "notify_id": "notify-001",
            "order_id": order_id,
            "amount": 9900,
            "status": "success",
            "paid_at": "2026-04-20T10:00:00Z",
        },
    )
    assert notify_response.status_code == 200
    assert notify_response.json()["code"] == "SUCCESS"

    order_detail = client.post("/api/v1/mp/orders/detail", headers=auth_headers(), json={"order_id": order_id})
    assert order_detail.status_code == 200
    assert order_detail.json()["data"]["status"] == "paid"

    status_response = client.post("/api/v1/mp/reports/status", headers=auth_headers(), json={"report_id": report_id})
    assert status_response.status_code == 200
    assert status_response.json()["data"]["status"] == "completed"

    links_response = client.post("/api/v1/mp/reports/links", headers=auth_headers(), json={"report_id": report_id})
    assert links_response.status_code == 200
    links = links_response.json()["data"]
    assert links["is_paid"] is True
    assert links["preview_h5_url"].startswith("https://cos.example.com/")
    assert links["full_h5_url"].startswith("https://cos.example.com/")
    assert links["pdf_url"].startswith("https://cos.example.com/")


def test_links_for_unpaid_report_only_return_preview(client):
    create_response = create_logged_in_report(client)
    report_id = create_response.json()["data"]["report_id"]

    links_response = client.post("/api/v1/mp/reports/links", headers=auth_headers(), json={"report_id": report_id})
    assert links_response.status_code == 200
    links = links_response.json()["data"]
    assert links["is_paid"] is False
    assert links["preview_h5_url"].startswith("https://cos.example.com/")
    assert links["full_h5_url"] is None
    assert links["pdf_url"] is None
