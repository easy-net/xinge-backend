def test_admin_wechat_pay_balances_returns_all_accounts(client):
    response = client.get("/api/v1/admin/wechat-pay/balances?focus=OPERATION")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["focus"] == "OPERATION"
    assert data["balances"]["OPERATION"]["available_amount"] == 123456
    assert data["balances"]["BASIC"]["available_amount"] == 456789
    assert data["balances"]["FEES"]["available_amount"] == 7890
