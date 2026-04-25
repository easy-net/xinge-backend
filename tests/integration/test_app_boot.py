def test_app_boot_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_static_report_preview_page_is_accessible(client):
    response = client.get("/static/report-preview.html")
    assert response.status_code == 200
    assert "报告预览" in response.text
