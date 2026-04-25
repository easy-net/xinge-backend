import logging


def auth_headers(login_code="login-code-user-1", device_uuid="device-1"):
    return {
        "X-Login-Code": login_code,
        "X-System-Version": "iOS 17.0",
        "X-Device-UUID": device_uuid,
    }


def bearer_headers(access_token):
    return {
        "Authorization": "Bearer {}".format(access_token),
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


def test_create_report_logs_request_and_response_when_enabled(client, test_settings, caplog):
    test_settings.log_mp_report_payloads = True
    client.post("/api/v1/mp/auth/login", headers=auth_headers(), json={})

    with caplog.at_level(logging.INFO):
        response = client.post(
            "/api/v1/mp/reports",
            headers=auth_headers(),
            json={
                "name": "张三",
                "school_name": "北京大学",
                "notes": "这里是需要调试的备注",
                "study_path_priority": ["国内读研"],
                "employment_intention": ["名企大厂"],
                "target_major": ["软件工程"],
                "target_work_city": ["北京"],
            },
        )

    assert response.status_code == 201
    messages = [record.getMessage() for record in caplog.records]
    request_log = next(message for message in messages if "mp.create_report.request" in message)
    response_log = next(message for message in messages if "mp.create_report.response" in message)
    assert "payload=" in request_log
    assert "'name': '张*'" in request_log
    assert "<redacted:10 chars>" in request_log
    assert "report_id" in response_log


def test_reports_create_and_list_accept_bearer_token(client):
    login_response = client.post("/api/v1/mp/auth/login", headers=auth_headers(), json={})
    access_token = login_response.json()["data"]["access_token"]

    create_response = client.post(
        "/api/v1/mp/reports",
        headers=bearer_headers(access_token),
        json={
            "name": "张三",
            "school_name": "北京大学",
            "study_path_priority": ["国内读研"],
            "employment_intention": ["名企大厂"],
            "target_major": ["软件工程"],
            "target_work_city": ["北京"],
        },
    )
    assert create_response.status_code == 201
    report_id = create_response.json()["data"]["report_id"]

    list_response = client.post(
        "/api/v1/mp/reports/list",
        headers=bearer_headers(access_token),
        json={"page": 1, "page_size": 20},
    )
    assert list_response.status_code == 200
    assert any(item["report_id"] == report_id for item in list_response.json()["data"]["list"])
