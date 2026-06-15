import base64
import hashlib
import hmac
from types import SimpleNamespace

import pytest

from lineworks_platform.adapter import (
    LINEWORKS_AUTH_URL,
    LineWorksAdapter,
    _account_from_extra,
    _extract_directives,
    register,
    validate_config,
    verify_signature,
)


class MockContext:
    def __init__(self):
        self.kwargs = None
        self.tools = []

    def register_platform(self, **kwargs):
        self.kwargs = kwargs

    def register_tool(self, **kwargs):
        self.tools.append(kwargs)


def test_verify_signature_accepts_valid_hmac():
    raw = b'{"type":"message"}'
    secret = "bot-secret"
    sig = base64.b64encode(hmac.new(secret.encode(), raw, hashlib.sha256).digest()).decode()
    assert verify_signature(raw, sig, secret) is True


def test_verify_signature_rejects_invalid_hmac():
    assert verify_signature(b"{}", "not-base64!!!", "secret") is False
    assert verify_signature(b"{}", None, "secret") is False
    assert verify_signature(b"{}", base64.b64encode(b"wrong").decode(), "secret") is False


def test_account_accepts_snake_and_camel_config(tmp_path, monkeypatch):
    monkeypatch.delenv("LINEWORKS_CLIENT_ID", raising=False)
    key = tmp_path / "key.pem"
    key.write_text("-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----\n")
    account = _account_from_extra(
        {
            "clientId": "cid",
            "clientSecret": "secret",
            "serviceAccount": "svc@example",
            "privateKeyFile": str(key),
            "botId": "bot",
            "botSecret": "botsecret",
            "allowFrom": [123, "u2"],
            "groupAllowFrom": "c1,c2",
        }
    )
    assert account.client_id == "cid"
    assert account.client_secret == "secret"
    assert account.service_account == "svc@example"
    assert account.bot_id == "bot"
    assert account.bot_secret == "botsecret"
    assert account.allow_from == ["123", "u2"]
    assert account.group_allow_from == ["c1", "c2"]
    assert account.has_credentials is True


def test_validate_config_requires_credentials(tmp_path):
    key = tmp_path / "key.pem"
    key.write_text("-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----\n")
    cfg = SimpleNamespace(
        extra={
            "client_id": "cid",
            "client_secret": "secret",
            "service_account": "svc@example",
            "private_key_file": str(key),
            "bot_id": "bot",
            "bot_secret": "botsecret",
        }
    )
    assert validate_config(cfg) is True
    assert validate_config(SimpleNamespace(extra={})) is False


def test_register_platform_contract():
    ctx = MockContext()
    register(ctx)
    assert ctx.kwargs is not None
    assert ctx.kwargs["name"] == "lineworks"
    assert ctx.kwargs["label"] == "LINE WORKS"
    assert callable(ctx.kwargs["adapter_factory"])
    assert callable(ctx.kwargs["check_fn"])
    adapter = ctx.kwargs["adapter_factory"](SimpleNamespace(extra={}, enabled=True))
    assert isinstance(adapter, LineWorksAdapter)
    assert adapter.name == "LINE WORKS"
    assert {tool["name"] for tool in ctx.tools} == {"lineworks_calendar", "lineworks_task", "lineworks_drive"}
    assert all(tool["toolset"] == "lineworks" for tool in ctx.tools)


def test_auth_url_matches_npm_0_5_5():
    assert LINEWORKS_AUTH_URL == "https://auth.worksmobile.com/oauth2/v2.0/token"


def test_extract_directives_supports_npm_0_5_5_rich_messages():
    text = 'hello [[flex: Card ||| {"type":"bubble","body":{"type":"box"}}]] [[location: Taipei 101 | Xinyi | 25.033 | 121.565]] [[quick_replies: Yes, More > https://example.com, payload > data:x=1]]'
    residual, flex, locations, quick = _extract_directives(text)
    assert residual == "hello"
    assert flex == [{"type": "flex", "altText": "Card", "contents": {"type": "bubble", "body": {"type": "box"}}}]
    assert locations[0]["type"] == "location"
    assert locations[0]["latitude"] == 25.033
    assert quick["items"][0]["action"] == {"type": "message", "label": "Yes", "text": "Yes"}
    assert quick["items"][1]["action"]["type"] == "uri"
    assert quick["items"][2]["action"]["type"] == "postback"


def test_calendar_31_day_guard():
    from lineworks_platform.tools import _validate_31_days

    _validate_31_days("2026-05-01T00:00:00+09:00", "2026-05-31T00:00:00+09:00")
    with pytest.raises(ValueError):
        _validate_31_days("2026-05-01T00:00:00+09:00", "2026-06-02T00:00:00+09:00")


def test_lineworks_tool_schemas_expose_calendar_task_drive():
    from lineworks_platform.tools import LINEWORKS_TOOLS

    names = [name for name, _schema, _handler, _emoji in LINEWORKS_TOOLS]
    assert names == ["lineworks_calendar", "lineworks_task", "lineworks_drive"]
    schemas = {name: schema for name, schema, _handler, _emoji in LINEWORKS_TOOLS}
    assert "create" in schemas["lineworks_calendar"]["input_schema"]["properties"]["action"]["enum"]
    assert "complete" in schemas["lineworks_task"]["input_schema"]["properties"]["action"]["enum"]
    assert "upload" in schemas["lineworks_drive"]["input_schema"]["properties"]["action"]["enum"]
