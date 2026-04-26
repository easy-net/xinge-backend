from app.core.config import env_or_default


def test_env_or_default_uses_default_for_blank(monkeypatch):
    monkeypatch.setenv("WECHAT_TRANSFER_REMARK", "")

    assert env_or_default("WECHAT_TRANSFER_REMARK", "分销佣金提现") == "分销佣金提现"


def test_env_or_default_uses_default_for_whitespace(monkeypatch):
    monkeypatch.setenv("WECHAT_TRANSFER_REMARK", "   ")

    assert env_or_default("WECHAT_TRANSFER_REMARK", "分销佣金提现") == "分销佣金提现"
