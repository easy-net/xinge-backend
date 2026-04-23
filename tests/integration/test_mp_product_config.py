from app.db.models.product_config import ProductConfig


def test_mp_product_config_returns_current_price(client, db_session):
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

    response = client.post("/api/v1/mp/config/product", json={})

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["price"]["current_amount"] == 9900
    assert payload["user_stats"]["display_count"] == 12345

