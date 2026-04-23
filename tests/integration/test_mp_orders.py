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


def test_mp_orders_create_returns_payment_params(client, db_session):
    seed_product_config(db_session)
    report_response = create_logged_in_report(client)
    report_id = report_response.json()["data"]["report_id"]

    response = client.post(
        "/api/v1/mp/orders",
        headers=auth_headers(),
        json={"report_id": report_id, "amount": 9900},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["report_id"] == report_id
    assert data["amount"] == 9900
    assert data["payment_params"]["signType"] == "RSA"


def test_mp_orders_create_rejects_amount_mismatch(client, db_session):
    seed_product_config(db_session)
    report_response = create_logged_in_report(client)
    report_id = report_response.json()["data"]["report_id"]

    response = client.post(
        "/api/v1/mp/orders",
        headers=auth_headers(),
        json={"report_id": report_id, "amount": 9800},
    )

    assert response.status_code == 400
    assert response.json()["message"] == "amount mismatch"


def test_mp_orders_create_rejects_duplicate_pending_order(client, db_session):
    seed_product_config(db_session)
    report_response = create_logged_in_report(client)
    report_id = report_response.json()["data"]["report_id"]

    first = client.post("/api/v1/mp/orders", headers=auth_headers(), json={"report_id": report_id, "amount": 9900})
    second = client.post("/api/v1/mp/orders", headers=auth_headers(), json={"report_id": report_id, "amount": 9900})

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["message"] == "duplicate pending order"


def test_mp_orders_detail_returns_order(client, db_session):
    seed_product_config(db_session)
    report_response = create_logged_in_report(client)
    report_id = report_response.json()["data"]["report_id"]
    create_order_response = client.post(
        "/api/v1/mp/orders",
        headers=auth_headers(),
        json={"report_id": report_id, "amount": 9900},
    )
    order_id = create_order_response.json()["data"]["order_id"]

    response = client.post(
        "/api/v1/mp/orders/detail",
        headers=auth_headers(),
        json={"order_id": order_id},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["order_id"] == order_id
    assert data["status"] == "pending"
