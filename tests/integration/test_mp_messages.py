from app.db.models.message import Message

from tests.integration.test_mp_reports_crud import auth_headers


def seed_login_and_messages(client, db_session):
    login_response = client.post("/api/v1/mp/auth/login", headers=auth_headers(), json={})
    user_id = login_response.json()["user_info"]["user_id"]
    db_session.add(
        Message(
            user_id=user_id,
            type="system",
            title="系统通知",
            content="第一条消息",
            is_read=False,
        )
    )
    db_session.add(
        Message(
            user_id=user_id,
            type="distributor_approved",
            title="审核通过",
            content="第二条消息",
            is_read=True,
        )
    )
    db_session.commit()
    return user_id


def test_mp_messages_list_filters_by_is_read(client, db_session):
    seed_login_and_messages(client, db_session)

    response = client.post("/api/v1/mp/messages/list", headers=auth_headers(), json={"page": 1, "page_size": 20, "is_read": False})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert data["list"][0]["is_read"] is False


def test_mp_messages_read_marks_owned_message_read(client, db_session):
    seed_login_and_messages(client, db_session)
    list_response = client.post("/api/v1/mp/messages/list", headers=auth_headers(), json={"page": 1, "page_size": 20})
    message_id = list_response.json()["data"]["list"][0]["message_id"]

    response = client.post("/api/v1/mp/messages/read", headers=auth_headers(), json={"message_id": message_id})

    assert response.status_code == 200
    assert response.json()["data"]["is_read"] is True
