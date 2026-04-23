def auth_headers(login_code="login-code-user-1", device_uuid="device-1"):
    return {
        "X-Login-Code": login_code,
        "X-System-Version": "iOS 17.0",
        "X-Device-UUID": device_uuid,
    }


def create_logged_in_report(client):
    client.post("/api/v1/mp/auth/login", headers=auth_headers(), json={})
    return client.post(
        "/api/v1/mp/reports",
        headers=auth_headers(),
        json={
            "name": "张三",
            "school_name": "北京大学",
            "major_name": "计算机科学与技术",
            "study_path_priority": ["国内读研"],
            "employment_intention": ["名企大厂"],
            "target_major": ["软件工程"],
            "target_work_city": ["北京"],
        },
    )


def test_create_report_returns_201(client):
    response = create_logged_in_report(client)
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "张三"
    assert data["status"] == "draft"


def test_list_reports_returns_current_users_reports(client):
    create_logged_in_report(client)

    response = client.post("/api/v1/mp/reports/list", headers=auth_headers(), json={"page": 1, "page_size": 20})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert data["list"][0]["name"] == "张三"


def test_report_detail_returns_confirmed_shape(client):
    create_response = create_logged_in_report(client)
    report_id = create_response.json()["data"]["report_id"]

    response = client.post(
        "/api/v1/mp/reports/detail",
        headers=auth_headers(),
        json={"report_id": report_id},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["report_id"] == report_id
    assert data["status"] == "draft"
    assert data["report_type"] == "preview"
    assert data["is_paid"] is False
    assert data["form"]["school_name"] == "北京大学"


def test_report_detail_hides_other_users_report(client):
    create_response = create_logged_in_report(client)
    report_id = create_response.json()["data"]["report_id"]

    client.post("/api/v1/mp/auth/login", headers=auth_headers("login-code-user-2", "device-2"), json={})
    response = client.post(
        "/api/v1/mp/reports/detail",
        headers=auth_headers("login-code-user-2", "device-2"),
        json={"report_id": report_id},
    )

    assert response.status_code == 404
