from app.core.response import error_response, mp_response, public_response


def test_public_response_has_swagger_shape():
    payload = public_response({"value": 1})
    assert payload["code"] == 0
    assert payload["message"] == "ok"
    assert payload["data"]["value"] == 1
    assert "timestamp" in payload


def test_mp_response_can_include_user_info():
    payload = mp_response({"value": 1}, user_info={"user_id": 42, "open_id": "openid"})
    assert payload["user_info"]["user_id"] == 42


def test_error_response_has_expected_fields():
    payload = error_response(1234, "boom")
    assert payload["code"] == 1234
    assert payload["message"] == "boom"

