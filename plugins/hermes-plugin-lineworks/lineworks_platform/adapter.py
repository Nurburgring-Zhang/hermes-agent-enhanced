"""LINE WORKS platform plugin for Hermes Agent."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import mimetypes
import os
import re
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Iterable, Optional
from urllib.parse import quote

try:
    import aiohttp
    from aiohttp import web

    AIOHTTP_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised by check_requirements only
    aiohttp = None  # type: ignore[assignment]
    web = None  # type: ignore[assignment]
    AIOHTTP_AVAILABLE = False

try:
    import jwt

    JWT_AVAILABLE = True
except ImportError:  # pragma: no cover
    jwt = None  # type: ignore[assignment]
    JWT_AVAILABLE = False

from gateway.config import Platform, PlatformConfig
from gateway.platforms.base import BasePlatformAdapter, MessageEvent, MessageType, SendResult

logger = logging.getLogger(__name__)

LINEWORKS_API_BASE = "https://www.worksapis.com/v1.0"
LINEWORKS_AUTH_URL = "https://auth.worksmobile.com/oauth2/v2.0/token"
LINEWORKS_SIGNATURE_HEADER = "x-works-signature"
DEFAULT_WEBHOOK_PATH = "/lineworks/webhook"
DEFAULT_PORT = 3981
TEXT_CHUNK_LIMIT = 4900
BASE_SCOPES = (
    "bot",
    "bot.read",
    "user.profile.read",
    "calendar",
    "calendar.read",
    "task",
    "task.read",
    "file",
    "file.read",
)
REFRESH_SKEW_SECONDS = 60


@dataclass
class LineWorksAccount:
    account_id: str = "default"
    enabled: bool = True
    client_id: str = ""
    client_secret: str = ""
    service_account: str = ""
    private_key: str = ""
    bot_id: str = ""
    bot_secret: str = ""
    domain_id: Optional[str] = None
    webhook_path: str = DEFAULT_WEBHOOK_PATH
    dm_policy: str = "pairing"
    group_policy: str = "allowlist"
    group_require_mention: bool = False
    bot_mention_handle: Optional[str] = None
    allow_from: list[str] = field(default_factory=list)
    group_allow_from: list[str] = field(default_factory=list)
    extra_scopes: list[str] = field(default_factory=list)
    sender_profile_enrichment: bool = True
    mail_pre_fetch_enabled: bool = False
    mail_pre_fetch_count: int = 10
    public_base_url: Optional[str] = None
    oauth_enabled: bool = False
    oauth_start_path: str = "/oauth/lineworks/start"
    oauth_callback_path: str = "/oauth/lineworks/callback"
    oauth_scopes: str = "mail,mail.read,task,task.read,file,file.read,calendar,calendar.read,user.profile.read,user.email.read"

    @property
    def has_credentials(self) -> bool:
        return all(
            [
                self.client_id,
                self.client_secret,
                self.service_account,
                self.private_key,
                self.bot_id,
                self.bot_secret,
            ]
        )


@dataclass
class AccessToken:
    token: str
    token_type: str
    expires_at: float
    scope: Optional[str] = None


def _config_or_env(extra: dict[str, Any], keys: tuple[str, ...], env_key: str, default: str = "") -> str:
    for key in keys:
        value = extra.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    env = os.getenv(env_key, "")
    return env.strip() if env else default


def _normalize_private_key(raw: str) -> str:
    value = (raw or "").replace("\r\n", "\n").replace("\r", "\n")
    if "\\n" in value and "\n" not in value:
        value = value.replace("\\n", "\n")
    value = value.strip()
    return value + "\n" if value else ""


def _load_private_key(extra: dict[str, Any]) -> str:
    inline = extra.get("private_key") or extra.get("privateKey")
    if isinstance(inline, str) and inline.strip():
        return _normalize_private_key(inline)

    private_key_file = extra.get("private_key_file") or extra.get("privateKeyFile")
    if isinstance(private_key_file, str) and private_key_file.strip():
        try:
            return _normalize_private_key(Path(private_key_file).expanduser().read_text())
        except OSError as exc:
            logger.warning("[lineworks] failed reading private_key_file=%s: %s", private_key_file, exc)

    env = os.getenv("LINEWORKS_PRIVATE_KEY", "")
    if env:
        return _normalize_private_key(env)
    env_file = os.getenv("LINEWORKS_PRIVATE_KEY_FILE", "")
    if env_file:
        try:
            return _normalize_private_key(Path(env_file).expanduser().read_text())
        except OSError as exc:
            logger.warning("[lineworks] failed reading LINEWORKS_PRIVATE_KEY_FILE=%s: %s", env_file, exc)
    return ""


def _normalize_list(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        return [part.strip() for part in raw.split(",") if part.strip()]
    if isinstance(raw, Iterable):
        return [str(item).strip() for item in raw if str(item).strip()]
    return []


def _account_from_extra(extra: dict[str, Any], account_id: str = "default") -> LineWorksAccount:
    # Hermes config style is snake_case. CamelCase aliases are accepted to ease
    # migration from the OpenClaw plugin README.
    def pick(*keys: str) -> Any:
        for key in keys:
            if key in extra:
                return extra[key]
        return None

    return LineWorksAccount(
        account_id=account_id,
        enabled=bool(pick("enabled") if pick("enabled") is not None else True),
        client_id=_config_or_env(extra, ("client_id", "clientId"), "LINEWORKS_CLIENT_ID"),
        client_secret=_config_or_env(extra, ("client_secret", "clientSecret"), "LINEWORKS_CLIENT_SECRET"),
        service_account=_config_or_env(extra, ("service_account", "serviceAccount"), "LINEWORKS_SERVICE_ACCOUNT"),
        private_key=_load_private_key(extra),
        bot_id=_config_or_env(extra, ("bot_id", "botId"), "LINEWORKS_BOT_ID"),
        bot_secret=_config_or_env(extra, ("bot_secret", "botSecret"), "LINEWORKS_BOT_SECRET"),
        domain_id=_config_or_env(extra, ("domain_id", "domainId"), "LINEWORKS_DOMAIN_ID") or None,
        webhook_path=(pick("webhook_path", "webhookPath") or DEFAULT_WEBHOOK_PATH),
        dm_policy=str(pick("dm_policy", "dmPolicy") or "pairing"),
        group_policy=str(pick("group_policy", "groupPolicy") or "allowlist"),
        group_require_mention=bool(pick("group_require_mention", "groupRequireMention") or False),
        bot_mention_handle=(str(pick("bot_mention_handle", "botMentionHandle") or "").lstrip("@") or None),
        allow_from=_normalize_list(pick("allow_from", "allowFrom")),
        group_allow_from=_normalize_list(pick("group_allow_from", "groupAllowFrom")),
        extra_scopes=_normalize_list(pick("extra_scopes", "extraScopes")),
        sender_profile_enrichment=bool(pick("sender_profile_enrichment", "senderProfileEnrichment") if pick("sender_profile_enrichment", "senderProfileEnrichment") is not None else True),
        mail_pre_fetch_enabled=bool(((pick("mail_pre_fetch", "mailPreFetch") or {}) if isinstance(pick("mail_pre_fetch", "mailPreFetch"), dict) else {}).get("enabled", False)),
        mail_pre_fetch_count=max(1, min(50, int(((pick("mail_pre_fetch", "mailPreFetch") or {}) if isinstance(pick("mail_pre_fetch", "mailPreFetch"), dict) else {}).get("count", 10)))),
        public_base_url=(str(pick("public_base_url", "publicBaseUrl") or "").rstrip("/") or None),
        oauth_enabled=bool(((pick("oauth") or {}) if isinstance(pick("oauth"), dict) else {}).get("enabled", False)),
        oauth_start_path=str(((pick("oauth") or {}) if isinstance(pick("oauth"), dict) else {}).get("startPath") or ((pick("oauth") or {}) if isinstance(pick("oauth"), dict) else {}).get("start_path") or "/oauth/lineworks/start"),
        oauth_callback_path=str(((pick("oauth") or {}) if isinstance(pick("oauth"), dict) else {}).get("callbackPath") or ((pick("oauth") or {}) if isinstance(pick("oauth"), dict) else {}).get("callback_path") or "/oauth/lineworks/callback"),
        oauth_scopes=str(((pick("oauth") or {}) if isinstance(pick("oauth"), dict) else {}).get("scopes") or "mail,mail.read,task,task.read,file,file.read,calendar,calendar.read,user.profile.read,user.email.read"),
    )


def _accounts_from_config(config: PlatformConfig) -> list[LineWorksAccount]:
    extra = getattr(config, "extra", {}) or {}
    accounts_cfg = extra.get("accounts") if isinstance(extra, dict) else None
    accounts: list[LineWorksAccount] = []
    if isinstance(accounts_cfg, dict) and accounts_cfg:
        for account_id, account_extra in accounts_cfg.items():
            merged = {k: v for k, v in extra.items() if k not in {"accounts", "default_account", "defaultAccount"}}
            if isinstance(account_extra, dict):
                merged.update(account_extra)
            account = _account_from_extra(merged, str(account_id))
            if account.enabled:
                accounts.append(account)
    else:
        account = _account_from_extra(extra, "default")
        if account.enabled:
            accounts.append(account)
    return accounts


def verify_signature(raw_body: bytes, signature_header: Optional[str], bot_secret: str) -> bool:
    if not signature_header or not bot_secret:
        return False
    expected = hmac.new(bot_secret.encode("utf-8"), raw_body, hashlib.sha256).digest()
    try:
        got = base64.b64decode(signature_header, validate=True)
    except Exception:
        return False
    return len(got) == len(expected) and hmac.compare_digest(got, expected)


def _content_from_event(raw: dict[str, Any]) -> tuple[str, MessageType, Optional[str], Optional[str]]:
    content = raw.get("content") if isinstance(raw.get("content"), dict) else {}
    ctype = content.get("type")
    if ctype == "text":
        return str(content.get("text") or ""), MessageType.TEXT, None, None
    if ctype == "image":
        return "[image]", MessageType.PHOTO, content.get("fileId") or content.get("resourceId"), None
    if ctype == "file":
        name = str(content.get("fileName") or "file")
        return f"[file: {name}]", MessageType.DOCUMENT, content.get("fileId") or content.get("resourceId"), name
    if ctype == "sticker":
        return f"[sticker {content.get('packageId', '')}:{content.get('stickerId', '')}]", MessageType.STICKER, None, None
    if ctype == "location":
        return (
            f"[location {content.get('title') or ''} {content.get('latitude')},{content.get('longitude')}]".strip(),
            MessageType.LOCATION,
            None,
            None,
        )
    if raw.get("type") == "postback" or content.get("postback"):
        return f"[postback] {content.get('postback') or content.get('data') or ''}", MessageType.TEXT, None, None
    return "", MessageType.TEXT, None, None


def _source_from_event(raw: dict[str, Any]) -> Optional[dict[str, Any]]:
    source = raw.get("source") if isinstance(raw.get("source"), dict) else None
    if not source:
        return None
    user_id = source.get("userId")
    channel_id = source.get("channelId")
    domain_id = source.get("domainId")
    if channel_id:
        return {"type": "channel", "channel_id": str(channel_id), "user_id": str(user_id or ""), "domain_id": str(domain_id or "")}
    if user_id:
        return {"type": "user", "user_id": str(user_id), "domain_id": str(domain_id or "")}
    return None


def _is_mentioning_bot(content: dict[str, Any], account: LineWorksAccount) -> bool:
    if content.get("type") != "text":
        return False
    for mention in content.get("mentionees") or []:
        if isinstance(mention, dict) and mention.get("accountId") in {account.bot_id, account.service_account}:
            return True
    text = str(content.get("text") or "")
    if account.bot_mention_handle:
        handle = re.escape(account.bot_mention_handle)
        return re.search(rf"(^|[^\w])@{handle}(?![\w])", text, re.IGNORECASE) is not None
    return re.search(r"(^|\s)@[^\s]", text) is not None




def _lineworks_platform():
    try:
        return Platform("lineworks")
    except Exception:
        # Direct unit tests may instantiate before PluginContext has registered
        # the dynamic platform. Runtime path uses the real Platform member.
        return SimpleNamespace(value="lineworks", name="LINEWORKS")


def _extract_directives(text: str) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]], Optional[dict[str, Any]]]:
    flex_messages: list[dict[str, Any]] = []
    locations: list[dict[str, Any]] = []
    quick_reply: Optional[dict[str, Any]] = None

    def flex_repl(match: re.Match[str]) -> str:
        inner = match.group(1)
        if "|||" not in inner:
            logger.warning("[lineworks] flex directive missing ||| separator")
            return ""
        alt, raw_json = inner.split("|||", 1)
        try:
            contents = json.loads(raw_json.strip())
        except Exception as exc:
            logger.warning("[lineworks] flex directive JSON parse failed: %s", exc)
            return ""
        flex_messages.append({"type": "flex", "altText": alt.strip()[:400], "contents": contents})
        return ""

    def location_repl(match: re.Match[str]) -> str:
        parts = [part.strip() for part in match.group(1).split("|")]
        if len(parts) != 4:
            logger.warning("[lineworks] location directive expects title | address | lat | lng")
            return ""
        title, address, lat, lng = parts
        try:
            locations.append({"type": "location", "title": title[:100], "address": address[:100], "latitude": float(lat), "longitude": float(lng)})
        except ValueError:
            logger.warning("[lineworks] location directive has non-numeric lat/lng")
        return ""

    def quick_repl(match: re.Match[str]) -> str:
        nonlocal quick_reply
        if quick_reply is not None:
            return ""
        items = []
        for raw in [x.strip() for x in match.group(1).split(",") if x.strip()][:13]:
            if ">" in raw:
                label, target = [x.strip() for x in raw.split(">", 1)]
                if re.match(r"^https?://", target, re.I):
                    action = {"type": "uri", "label": label[:20], "uri": target}
                elif target.lower().startswith("data:"):
                    action = {"type": "postback", "label": label[:20], "data": target[5:], "displayText": label}
                else:
                    action = {"type": "message", "label": label[:20], "text": target}
            else:
                action = {"type": "message", "label": raw[:20], "text": raw}
            items.append({"action": action})
        if items:
            quick_reply = {"items": items}
        return ""

    residual = re.sub(r"\[\[flex:\s*([\s\S]*?)\]\]", flex_repl, text or "")
    residual = re.sub(r"\[\[location:\s*([\s\S]*?)\]\]", location_repl, residual)
    residual = re.sub(r"\[\[quick_replies:\s*([\s\S]*?)\]\]", quick_repl, residual)
    residual = re.sub(r"[ \t]+\n", "\n", residual)
    residual = re.sub(r"\n{3,}", "\n\n", residual).strip()
    return residual, flex_messages, locations, quick_reply


def check_requirements() -> bool:
    return AIOHTTP_AVAILABLE and JWT_AVAILABLE


def validate_config(config) -> bool:
    try:
        return any(account.has_credentials for account in _accounts_from_config(config))
    except Exception:
        return False


def is_connected(config) -> bool:
    return validate_config(config)


class LineWorksClient:
    def __init__(self, session: "aiohttp.ClientSession", account: LineWorksAccount):
        self.session = session
        self.account = account
        self._token: Optional[AccessToken] = None
        self._token_lock = asyncio.Lock()

    async def get_access_token(self) -> AccessToken:
        now = time.time()
        if self._token and self._token.expires_at - now > REFRESH_SKEW_SECONDS:
            return self._token
        async with self._token_lock:
            now = time.time()
            if self._token and self._token.expires_at - now > REFRESH_SKEW_SECONDS:
                return self._token
            assertion = jwt.encode(
                {
                    "iss": self.account.client_id,
                    "sub": self.account.service_account,
                    "iat": int(now),
                    "exp": int(now) + 3600,
                },
                self.account.private_key,
                algorithm="RS256",
                headers={"typ": "JWT"},
            )
            scope = " ".join(dict.fromkeys([*BASE_SCOPES, *self.account.extra_scopes]))
            data = {
                "assertion": assertion,
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "client_id": self.account.client_id,
                "client_secret": self.account.client_secret,
                "scope": scope,
            }
            async with self.session.post(LINEWORKS_AUTH_URL, data=data) as resp:
                text = await resp.text()
                if resp.status >= 400:
                    raise RuntimeError(f"LINE WORKS auth failed: {resp.status} {text}")
                payload = json.loads(text)
            self._token = AccessToken(
                token=payload["access_token"],
                token_type=payload.get("token_type", "Bearer"),
                expires_at=time.time() + int(payload.get("expires_in", 3600)),
                scope=payload.get("scope"),
            )
            return self._token

    async def _headers(self) -> dict[str, str]:
        token = await self.get_access_token()
        return {"authorization": f"{token.token_type} {token.token}"}

    async def send_message(self, chat_id: str, content: dict[str, Any]) -> None:
        headers = await self._headers()
        headers["content-type"] = "application/json"
        if chat_id.startswith("user:"):
            url = f"{LINEWORKS_API_BASE}/bots/{quote(self.account.bot_id)}/users/{quote(chat_id[5:])}/messages"
        elif chat_id.startswith("channel:"):
            url = f"{LINEWORKS_API_BASE}/bots/{quote(self.account.bot_id)}/channels/{quote(chat_id[8:])}/messages"
        else:
            # Default to user IDs for backwards-compatible send_message(target='lineworks:<user>') usage.
            url = f"{LINEWORKS_API_BASE}/bots/{quote(self.account.bot_id)}/users/{quote(chat_id)}/messages"
        async with self.session.post(url, headers=headers, json={"content": content}) as resp:
            if resp.status >= 400:
                text = await resp.text()
                raise RuntimeError(f"LINE WORKS send failed: {resp.status} {text}")

    async def download_attachment(self, resource_id: str, max_bytes: int = 15 * 1024 * 1024) -> tuple[str, str]:
        headers = await self._headers()
        url = f"{LINEWORKS_API_BASE}/bots/{quote(self.account.bot_id)}/attachments/{quote(resource_id)}"
        async with self.session.get(url, headers=headers, allow_redirects=False) as resp:
            if 300 <= resp.status < 400 and resp.headers.get("location"):
                redirect = resp.headers["location"]
            elif resp.status < 400:
                data = await resp.read()
                content_type = resp.headers.get("content-type", "application/octet-stream")
                return _write_temp_attachment(data, content_type, max_bytes)
            else:
                text = await resp.text()
                raise RuntimeError(f"LINE WORKS attachment fetch failed: {resp.status} {text}")
        async with self.session.get(redirect, headers=headers) as resp:
            data = await resp.read()
            if resp.status >= 400:
                text = data.decode("utf-8", "replace")
                raise RuntimeError(f"LINE WORKS attachment fetch failed: {resp.status} {text}")
            content_type = resp.headers.get("content-type", "application/octet-stream")
            return _write_temp_attachment(data, content_type, max_bytes)

    async def get_user_profile(self, user_id: str) -> Optional[dict[str, Any]]:
        headers = await self._headers()
        url = f"{LINEWORKS_API_BASE}/users/{quote(user_id)}"
        async with self.session.get(url, headers=headers) as resp:
            if resp.status == 404:
                return None
            if resp.status >= 400:
                text = await resp.text()
                logger.warning("[lineworks] user profile fetch failed: %s %s", resp.status, text[:160])
                return None
            return await resp.json()

    async def upload_attachment(self, file_path: str) -> str:
        path = Path(file_path).expanduser()
        headers = await self._headers()
        headers["content-type"] = "application/json"
        async with self.session.post(
            f"{LINEWORKS_API_BASE}/bots/{quote(self.account.bot_id)}/attachments",
            headers=headers,
            json={"fileName": path.name},
        ) as resp:
            text = await resp.text()
            if resp.status >= 400:
                raise RuntimeError(f"LINE WORKS upload init failed: {resp.status} {text}")
            payload = json.loads(text)
        upload_url = payload["uploadUrl"]
        file_id = payload["fileId"]
        form = aiohttp.FormData()
        form.add_field(
            "FileData",
            path.read_bytes(),
            filename=path.name,
            content_type=mimetypes.guess_type(str(path))[0] or "application/octet-stream",
        )
        form.add_field("resourceName", path.name)
        headers = await self._headers()
        async with self.session.post(upload_url, headers=headers, data=form) as resp:
            if resp.status >= 400:
                text = await resp.text()
                raise RuntimeError(f"LINE WORKS upload bytes failed: {resp.status} {text}")
        return file_id


def _write_temp_attachment(data: bytes, content_type: str, max_bytes: int) -> tuple[str, str]:
    if len(data) > max_bytes:
        raise RuntimeError(f"LINE WORKS attachment exceeds max size ({len(data)} > {max_bytes})")
    ext = mimetypes.guess_extension(content_type.split(";", 1)[0].strip()) or ".bin"
    fd, path = tempfile.mkstemp(prefix="lineworks-media-", suffix=ext)
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)
    return path, content_type


class LineWorksAdapter(BasePlatformAdapter):
    MAX_MESSAGE_LENGTH = TEXT_CHUNK_LIMIT

    def __init__(self, config: PlatformConfig):
        super().__init__(config, _lineworks_platform())
        extra = getattr(config, "extra", {}) or {}
        self.host = str(extra.get("host") or os.getenv("LINEWORKS_HOST") or "0.0.0.0")
        self.port = int(extra.get("port") or os.getenv("LINEWORKS_PORT") or DEFAULT_PORT)
        self.accounts = _accounts_from_config(config)
        self._clients: dict[str, LineWorksClient] = {}
        self._session: Optional[aiohttp.ClientSession] = None
        self._runner: Optional[web.AppRunner] = None

    @property
    def name(self) -> str:
        return "LINE WORKS"

    async def connect(self) -> bool:
        if not AIOHTTP_AVAILABLE or not JWT_AVAILABLE:
            self._set_fatal_error("MISSING_DEPS", "Install dependencies: pip install aiohttp PyJWT cryptography", retryable=False)
            return False
        if not self.accounts or not any(account.has_credentials for account in self.accounts):
            self._set_fatal_error("MISSING_CREDENTIALS", "LINE WORKS credentials are required", retryable=False)
            return False

        self._session = aiohttp.ClientSession()
        self._clients = {account.account_id: LineWorksClient(self._session, account) for account in self.accounts}
        app = web.Application(client_max_size=1024 * 1024)
        app.router.add_get("/health", lambda _req: web.Response(text="ok"))
        for account in self.accounts:
            app.router.add_post(account.webhook_path, self._make_webhook_handler(account))
            logger.info("[lineworks] Registered webhook route %s for account %s", account.webhook_path, account.account_id)
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self.host, self.port)
        await site.start()
        self._mark_connected()
        logger.info("[lineworks] Webhook server listening on %s:%d", self.host, self.port)
        return True

    async def disconnect(self) -> None:
        if self._runner:
            await self._runner.cleanup()
            self._runner = None
        if self._session:
            await self._session.close()
            self._session = None
        self._clients = {}
        self._mark_disconnected()

    def _make_webhook_handler(self, account: LineWorksAccount):
        async def handler(request: "web.Request") -> "web.Response":
            raw_body = await request.read()
            signature = request.headers.get(LINEWORKS_SIGNATURE_HEADER) or request.headers.get("X-WORKS-Signature")
            if not verify_signature(raw_body, signature, account.bot_secret):
                logger.warning("[lineworks] invalid signature from %s", request.remote)
                return web.json_response({"error": "Invalid signature"}, status=401)
            try:
                payload = json.loads(raw_body.decode("utf-8"))
            except json.JSONDecodeError:
                return web.json_response({"error": "Invalid JSON body"}, status=400)
            asyncio.create_task(self._handle_payload(account, payload))
            return web.Response(status=204)

        return handler

    async def _handle_payload(self, account: LineWorksAccount, payload: dict[str, Any]) -> None:
        if payload.get("type") not in {"message", "postback"}:
            return
        source_info = _source_from_event(payload)
        if not source_info:
            return
        if source_info["type"] == "channel" and account.group_policy == "disabled":
            return
        if source_info["type"] == "channel" and account.group_policy == "allowlist":
            if source_info["channel_id"] not in set(account.group_allow_from):
                logger.info("[lineworks] dropping message from non-allowlisted channel %s", source_info["channel_id"])
                return
        if source_info["type"] == "user" and account.dm_policy == "disabled":
            return
        if source_info["type"] == "user" and account.dm_policy == "allowlist":
            if source_info["user_id"] not in set(account.allow_from):
                logger.info("[lineworks] dropping message from non-allowlisted user %s", source_info["user_id"])
                return

        content = payload.get("content") if isinstance(payload.get("content"), dict) else {}
        if source_info["type"] == "channel" and account.group_require_mention and not _is_mentioning_bot(content, account):
            return
        text, message_type, resource_id, file_name = _content_from_event(payload)
        if not text and not resource_id:
            return

        media_urls: list[str] = []
        media_types: list[str] = []
        if resource_id and message_type in {MessageType.PHOTO, MessageType.DOCUMENT}:
            try:
                path, content_type = await self._clients[account.account_id].download_attachment(resource_id)
                media_urls.append(path)
                media_types.append(content_type)
            except Exception as exc:
                logger.warning("[lineworks] failed downloading attachment %s: %s", resource_id, exc)

        if source_info["type"] == "channel":
            chat_id = f"channel:{source_info['channel_id']}"
            raw_chat_id = source_info["channel_id"]
            chat_type = "group"
            user_id = source_info.get("user_id") or "unknown"
        else:
            chat_id = f"user:{source_info['user_id']}"
            raw_chat_id = source_info["user_id"]
            chat_type = "dm"
            user_id = source_info["user_id"]

        user_name = user_id
        channel_prompt = None
        if account.sender_profile_enrichment and user_id and user_id != "unknown":
            try:
                profile = await self._clients[account.account_id].get_user_profile(user_id)
                if profile:
                    display_name = profile.get("displayName") or profile.get("nickName")
                    email = profile.get("email")
                    orgs = profile.get("organizations") if isinstance(profile.get("organizations"), list) else []
                    dept = ""
                    if orgs and isinstance(orgs[0], dict):
                        dept = str(orgs[0].get("name") or "")
                    user_name = str(display_name or email or user_id)
                    bits = [f"LINE WORKS sender: {user_name}"]
                    if email:
                        bits.append(f"email: {email}")
                    if dept:
                        bits.append(f"department: {dept}")
                    channel_prompt = "; ".join(bits)
            except Exception as exc:
                logger.debug("[lineworks] profile enrichment failed: %s", exc)

        source = self.build_source(
            chat_id=chat_id,
            chat_name=raw_chat_id,
            chat_type=chat_type,
            user_id=user_id,
            user_name=user_name,
            guild_id=source_info.get("domain_id") or account.domain_id,
            message_id=str(payload.get("messageId") or payload.get("eventId") or "") or None,
        )
        event = MessageEvent(
            text=text,
            message_type=message_type,
            source=source,
            raw_message=payload,
            message_id=str(payload.get("messageId") or payload.get("eventId") or "") or None,
            media_urls=media_urls,
            media_types=media_types,
            channel_prompt=channel_prompt,
        )
        await self.handle_message(event)

    def _default_client(self) -> LineWorksClient:
        if not self._clients:
            raise RuntimeError("LINE WORKS adapter is not connected")
        default_id = self.accounts[0].account_id if self.accounts else "default"
        return self._clients.get(default_id) or next(iter(self._clients.values()))

    async def send(self, chat_id: str, content: str, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult:
        try:
            residual, flex_messages, locations, quick_reply = _extract_directives(self.format_message(content))
            chunks = self.truncate_message(residual, self.MAX_MESSAGE_LENGTH) if residual else []
            for i, chunk in enumerate(chunks):
                message: dict[str, Any] = {"type": "text", "text": chunk}
                if quick_reply and i == len(chunks) - 1 and not flex_messages and not locations:
                    message["quickReply"] = quick_reply
                await self._default_client().send_message(chat_id, message)
            rich = [*flex_messages, *locations]
            for i, message in enumerate(rich):
                if quick_reply and i == len(rich) - 1:
                    message = {**message, "quickReply": quick_reply}
                await self._default_client().send_message(chat_id, message)
            if quick_reply and not chunks and not rich:
                await self._default_client().send_message(chat_id, {"type": "text", "text": "⋯", "quickReply": quick_reply})
            return SendResult(success=True)
        except Exception as exc:
            logger.error("[lineworks] send failed: %s", exc, exc_info=True)
            return SendResult(success=False, error=str(exc), retryable=True)

    async def send_image(self, chat_id: str, image_url: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult:
        try:
            if image_url.startswith("http://") or image_url.startswith("https://"):
                message = {"type": "image", "originalContentUrl": image_url, "previewImageUrl": image_url}
            else:
                file_id = await self._default_client().upload_attachment(image_url.removeprefix("file://"))
                message = {"type": "image", "fileId": file_id}
            await self._default_client().send_message(chat_id, message)
            if caption:
                await self.send(chat_id, caption, reply_to=reply_to, metadata=metadata)
            return SendResult(success=True)
        except Exception as exc:
            logger.error("[lineworks] send_image failed: %s", exc, exc_info=True)
            return SendResult(success=False, error=str(exc), retryable=True)

    async def send_image_file(self, chat_id: str, image_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, **kwargs) -> SendResult:
        return await self.send_image(chat_id, image_path, caption=caption, reply_to=reply_to)

    async def send_file(self, chat_id: str, file_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> SendResult:
        try:
            file_id = await self._default_client().upload_attachment(file_path.removeprefix("file://"))
            await self._default_client().send_message(chat_id, {"type": "file", "fileId": file_id, "fileName": Path(file_path).name})
            if caption:
                await self.send(chat_id, caption, reply_to=reply_to, metadata=metadata)
            return SendResult(success=True)
        except Exception as exc:
            logger.error("[lineworks] send_file failed: %s", exc, exc_info=True)
            return SendResult(success=False, error=str(exc), retryable=True)

    async def get_chat_info(self, chat_id: str) -> dict[str, Any]:
        if chat_id.startswith("channel:"):
            return {"name": chat_id[8:], "type": "group", "chat_id": chat_id}
        return {"name": chat_id.removeprefix("user:"), "type": "dm", "chat_id": chat_id}


def interactive_setup() -> None:
    from hermes_cli.config import get_env_value, print_info, print_success, print_warning, prompt, save_env_value

    print_info("LINE WORKS setup needs Developer Console app + bot + Service Account credentials.")
    print_info("Callback URL: https://<your-gateway-host>/lineworks/webhook")
    values = {
        "LINEWORKS_CLIENT_ID": "Client ID",
        "LINEWORKS_CLIENT_SECRET": "Client secret",
        "LINEWORKS_SERVICE_ACCOUNT": "Service Account email",
        "LINEWORKS_BOT_ID": "Bot ID",
        "LINEWORKS_BOT_SECRET": "Bot secret",
        "LINEWORKS_PRIVATE_KEY_FILE": "Private key PEM path (recommended)",
    }
    for env_key, label in values.items():
        current = get_env_value(env_key) or ""
        value = prompt(label, default=current, password="SECRET" in env_key)
        if value:
            save_env_value(env_key, value.strip())
        elif env_key != "LINEWORKS_PRIVATE_KEY_FILE":
            print_warning(f"{env_key} is required")
    port = prompt("Webhook port", default=get_env_value("LINEWORKS_PORT") or str(DEFAULT_PORT))
    if port:
        save_env_value("LINEWORKS_PORT", port.strip())
    print_success("LINE WORKS env saved. Add gateway.platforms.lineworks.enabled=true and restart gateway.")


def register(ctx) -> None:
    try:
        from .tools import LINEWORKS_TOOLS, _check_lineworks_available
    except Exception:
        LINEWORKS_TOOLS = ()
        _check_lineworks_available = check_requirements

    ctx.register_platform(
        name="lineworks",
        label="LINE WORKS",
        adapter_factory=lambda cfg: LineWorksAdapter(cfg),
        check_fn=check_requirements,
        validate_config=validate_config,
        is_connected=is_connected,
        required_env=[
            "LINEWORKS_CLIENT_ID",
            "LINEWORKS_CLIENT_SECRET",
            "LINEWORKS_SERVICE_ACCOUNT",
            "LINEWORKS_BOT_ID",
            "LINEWORKS_BOT_SECRET",
        ],
        install_hint="pip install aiohttp PyJWT cryptography",
        setup_fn=interactive_setup,
        allowed_users_env="LINEWORKS_ALLOWED_USERS",
        allow_all_env="LINEWORKS_ALLOW_ALL_USERS",
        max_message_length=TEXT_CHUNK_LIMIT,
        emoji="💬",
        allow_update_command=True,
        platform_hint=(
            "You are chatting via LINE WORKS. Keep replies concise. Markdown support is limited; "
            "plain text and simple bullets render best."
        ),
    )

    for name, schema, handler, emoji in LINEWORKS_TOOLS:
        ctx.register_tool(
            name=name,
            toolset="lineworks",
            schema=schema,
            handler=handler,
            check_fn=_check_lineworks_available,
            emoji=emoji,
        )
