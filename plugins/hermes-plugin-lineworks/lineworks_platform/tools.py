"""Hermes tools for LINE WORKS Calendar, Task, and Drive APIs."""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import time
import uuid
from dataclasses import replace
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, build_opener, urlopen

import jwt

from tools.registry import tool_error, tool_result

from .adapter import (
    LINEWORKS_API_BASE,
    LINEWORKS_AUTH_URL,
    AccessToken,
    LineWorksAccount,
    _account_from_extra,
    _accounts_from_config,
)

_TOOLSET = "lineworks"
_DEFAULT_SCOPES = (
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
_TOKEN_CACHE: dict[str, AccessToken] = {}


def _load_config() -> dict[str, Any]:
    try:
        from hermes_cli.config import load_config

        return load_config()
    except Exception:
        return {}


def _lineworks_extra() -> dict[str, Any]:
    cfg = _load_config()
    candidates = [
        ((cfg.get("gateway") or {}).get("platforms") or {}).get("lineworks"),
        (cfg.get("platforms") or {}).get("lineworks"),
        cfg.get("lineworks"),
    ]
    for raw in candidates:
        if isinstance(raw, dict):
            extra = dict(raw.get("extra") or raw)
            extra.pop("enabled", None)
            return extra
    return {}


def _account(account_id: Optional[str] = None) -> LineWorksAccount:
    extra = _lineworks_extra()
    accounts = _accounts_from_config(SimpleNamespace(extra=extra)) if extra else [_account_from_extra({}, "default")]
    enabled = [acc for acc in accounts if acc.enabled]
    if not enabled:
        raise RuntimeError("LINE WORKS config has no enabled accounts")
    if account_id:
        for acc in enabled:
            if acc.account_id == account_id:
                return acc
        raise RuntimeError(f"LINE WORKS account not found: {account_id}")
    return enabled[0]


def _check_lineworks_available() -> bool:
    try:
        return _account().has_credentials and bool(jwt)
    except Exception:
        return False


def _token_cache_key(account: LineWorksAccount, scopes: tuple[str, ...]) -> str:
    raw = "|".join([account.account_id, account.client_id, account.service_account, *scopes])
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _access_token(account: LineWorksAccount, scopes: tuple[str, ...] = _DEFAULT_SCOPES) -> AccessToken:
    now = time.time()
    scopes = tuple(dict.fromkeys([*scopes, *account.extra_scopes]))
    key = _token_cache_key(account, scopes)
    cached = _TOKEN_CACHE.get(key)
    if cached and cached.expires_at - now > 60:
        return cached
    assertion = jwt.encode(
        {"iss": account.client_id, "sub": account.service_account, "iat": int(now), "exp": int(now) + 3600},
        account.private_key,
        algorithm="RS256",
        headers={"typ": "JWT"},
    )
    data = urlencode(
        {
            "assertion": assertion,
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "client_id": account.client_id,
            "client_secret": account.client_secret,
            "scope": " ".join(scopes),
        }
    ).encode()
    req = Request(LINEWORKS_AUTH_URL, data=data, method="POST")
    req.add_header("content-type", "application/x-www-form-urlencoded")
    payload = _open_json(req)
    token = AccessToken(
        token=payload["access_token"],
        token_type=payload.get("token_type", "Bearer"),
        expires_at=time.time() + int(payload.get("expires_in", 3600)),
        scope=payload.get("scope"),
    )
    _TOKEN_CACHE[key] = token
    return token


def _headers(account: LineWorksAccount, scopes: tuple[str, ...] = _DEFAULT_SCOPES, *, json_content: bool = False) -> dict[str, str]:
    token = _access_token(account, scopes)
    headers = {"authorization": f"{token.token_type} {token.token}"}
    if json_content:
        headers["content-type"] = "application/json"
    return headers


def _open(req: Request) -> tuple[int, dict[str, str], bytes]:
    try:
        with urlopen(req, timeout=60) as resp:
            return resp.status, {k.lower(): v for k, v in resp.headers.items()}, resp.read()
    except HTTPError as exc:
        body = exc.read()
        raise RuntimeError(f"LINE WORKS API failed: {exc.code} {body.decode('utf-8', 'replace')}") from exc
    except URLError as exc:
        raise RuntimeError(f"LINE WORKS API request failed: {exc.reason}") from exc


class _NoRedirectHandler(__import__("urllib.request").request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def _open_no_redirect(req: Request) -> tuple[int, dict[str, str], bytes]:
    opener = build_opener(_NoRedirectHandler)
    try:
        with opener.open(req, timeout=60) as resp:
            return resp.status, {k.lower(): v for k, v in resp.headers.items()}, resp.read()
    except HTTPError as exc:
        if 300 <= exc.code < 400:
            return exc.code, {k.lower(): v for k, v in exc.headers.items()}, exc.read()
        body = exc.read()
        raise RuntimeError(f"LINE WORKS API failed: {exc.code} {body.decode('utf-8', 'replace')}") from exc
    except URLError as exc:
        raise RuntimeError(f"LINE WORKS API request failed: {exc.reason}") from exc


def _open_json(req: Request) -> dict[str, Any]:
    _, _, body = _open(req)
    if not body:
        return {"success": True}
    return json.loads(body.decode("utf-8"))


def _api(account: LineWorksAccount, method: str, path: str, *, query: Optional[dict[str, Any]] = None, body: Any = None, scopes: tuple[str, ...] = _DEFAULT_SCOPES) -> Any:
    qs = ""
    if query:
        qs = "?" + urlencode({k: v for k, v in query.items() if v is not None and v != ""}, doseq=True)
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = Request(f"{LINEWORKS_API_BASE}{path}{qs}", data=data, method=method.upper())
    for key, value in _headers(account, scopes, json_content=body is not None).items():
        req.add_header(key, value)
    return _open_json(req)


def _validate_31_days(start: str, end: str) -> None:
    def parse(value: str) -> date:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()

    if (parse(end) - parse(start)).days > 31:
        raise ValueError("LINE WORKS calendar list allows max 31 days per request")


def _multipart_body(file_path: str, field_name: str = "FileData") -> tuple[bytes, str]:
    path = Path(file_path).expanduser()
    boundary = f"----hermes-lineworks-{uuid.uuid4().hex}"
    mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    data = path.read_bytes()
    parts = [
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"resourceName\"\r\n\r\n{path.name}\r\n".encode(),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"{field_name}\"; filename=\"{path.name}\"\r\nContent-Type: {mime}\r\n\r\n".encode(),
        data,
        f"\r\n--{boundary}--\r\n".encode(),
    ]
    return b"".join(parts), boundary


def _upload_to_url(account: LineWorksAccount, upload_url: str, file_path: str) -> dict[str, Any]:
    body, boundary = _multipart_body(file_path)
    req = Request(upload_url, data=body, method="POST")
    for key, value in _headers(account, ("file",)).items():
        req.add_header(key, value)
    req.add_header("content-type", f"multipart/form-data; boundary={boundary}")
    req.add_header("content-length", str(len(body)))
    status, headers, raw = _open(req)
    payload: Any = {"success": True, "status_code": status}
    if raw:
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            payload = {"success": True, "status_code": status, "body": raw.decode("utf-8", "replace")}
    if headers.get("location"):
        payload["location"] = headers["location"]
    return payload


def handle_lineworks_calendar(args: dict, **_: Any) -> str:
    action = str(args.get("action") or "list").strip().lower()
    account = _account(args.get("account_id"))
    user_id = str(args.get("user_id") or "me")
    try:
        if action == "list":
            start = str(args.get("start") or args.get("from") or "")
            end = str(args.get("end") or args.get("to") or "")
            if not start or not end:
                return tool_error("start and end are required")
            _validate_31_days(start, end)
            calendar_id = args.get("calendar_id")
            if calendar_id:
                path = f"/users/{quote(user_id)}/calendars/{quote(str(calendar_id))}/events"
            else:
                path = f"/users/{quote(user_id)}/calendar/events"
            query = {"fromDateTime": start, "untilDateTime": end, "timezone": args.get("timezone")}
            return tool_result(_api(account, "GET", path, query=query, scopes=("calendar.read", "calendar")))
        if action == "create":
            calendar_id = args.get("calendar_id")
            path = f"/users/{quote(user_id)}/calendar/events" if not calendar_id else f"/users/{quote(user_id)}/calendars/{quote(str(calendar_id))}/events"
            body = args.get("event") or {k: v for k, v in args.items() if k not in {"action", "account_id", "user_id", "calendar_id"}}
            return tool_result(_api(account, "POST", path, body=body, scopes=("calendar",)))
        return tool_error(f"Unsupported calendar action: {action}")
    except Exception as exc:
        return tool_error(str(exc))


def handle_lineworks_task(args: dict, **_: Any) -> str:
    action = str(args.get("action") or "list").strip().lower()
    account = _account(args.get("account_id"))
    user_id = str(args.get("user_id") or "me")
    try:
        if action == "list":
            query = {k: args.get(k) for k in ("status", "assignorId", "assigneeId", "createdTimeFrom", "createdTimeTo", "limit", "cursor")}
            return tool_result(_api(account, "GET", f"/users/{quote(user_id)}/tasks", query=query, scopes=("task.read", "task")))
        if action == "create":
            body = args.get("task") or {k: v for k, v in args.items() if k not in {"action", "account_id", "user_id"}}
            return tool_result(_api(account, "POST", f"/users/{quote(user_id)}/tasks", body=body, scopes=("task",)))
        if action in {"update", "patch"}:
            task_id = str(args.get("task_id") or "")
            if not task_id:
                return tool_error("task_id is required")
            body = args.get("task") or {k: v for k, v in args.items() if k not in {"action", "account_id", "user_id", "task_id"}}
            return tool_result(_api(account, "PATCH", f"/tasks/{quote(task_id)}", body=body, scopes=("task",)))
        if action in {"complete", "done"}:
            task_id = str(args.get("task_id") or "")
            if not task_id:
                return tool_error("task_id is required")
            return tool_result(_api(account, "POST", f"/tasks/{quote(task_id)}/complete", scopes=("task",)))
        if action in {"incomplete", "todo", "reopen"}:
            task_id = str(args.get("task_id") or "")
            if not task_id:
                return tool_error("task_id is required")
            return tool_result(_api(account, "POST", f"/tasks/{quote(task_id)}/incomplete", scopes=("task",)))
        return tool_error(f"Unsupported task action: {action}")
    except Exception as exc:
        return tool_error(str(exc))


def handle_lineworks_drive(args: dict, **_: Any) -> str:
    action = str(args.get("action") or "list").strip().lower()
    account = _account(args.get("account_id"))
    user_id = str(args.get("user_id") or "me")
    try:
        if action in {"list", "children"}:
            file_id = str(args.get("file_id") or "root")
            query = {k: args.get(k) for k in ("count", "cursor", "orderBy", "direction")}
            return tool_result(_api(account, "GET", f"/users/{quote(user_id)}/drive/files/{quote(file_id)}/children", query=query, scopes=("file.read", "file")))
        if action == "download":
            file_id = str(args.get("file_id") or "")
            if not file_id:
                return tool_error("file_id is required")
            req = Request(f"{LINEWORKS_API_BASE}/users/{quote(user_id)}/drive/files/{quote(file_id)}/download", method="GET")
            for key, value in _headers(account, ("file.read", "file")).items():
                req.add_header(key, value)
            status, headers, raw = _open_no_redirect(req)
            out = args.get("output_path")
            redirect = headers.get("location")
            if out:
                path = Path(str(out)).expanduser()
                path.parent.mkdir(parents=True, exist_ok=True)
                if redirect:
                    download_req = Request(redirect, method="GET")
                    for key, value in _headers(account, ("file.read", "file")).items():
                        download_req.add_header(key, value)
                    _status, headers, raw = _open(download_req)
                path.write_bytes(raw)
                return tool_result({"success": True, "path": str(path), "bytes": len(raw), "content_type": headers.get("content-type")})
            return tool_result({"success": True, "status_code": status, "download_url": redirect, "bytes": len(raw), "content_type": headers.get("content-type")})
        if action == "create_upload_url":
            file_path = args.get("file_path")
            file_name = str(args.get("file_name") or (Path(str(file_path)).name if file_path else ""))
            file_size = int(args.get("file_size") or (Path(str(file_path)).expanduser().stat().st_size if file_path else 0))
            if not file_name or not file_size:
                return tool_error("file_name/file_size or file_path is required")
            body = {"fileName": file_name, "fileSize": file_size, "overwrite": bool(args.get("overwrite", False)), "resume": bool(args.get("resume", False))}
            parent = args.get("parent_file_id") or args.get("file_id")
            path = f"/users/{quote(user_id)}/drive/files" if not parent or str(parent) == "root" else f"/users/{quote(user_id)}/drive/files/{quote(str(parent))}"
            return tool_result(_api(account, "POST", path, body=body, scopes=("file",)))
        if action == "upload":
            file_path = str(args.get("file_path") or "")
            if not file_path:
                return tool_error("file_path is required")
            file = Path(file_path).expanduser()
            if not file.exists():
                return tool_error(f"file not found: {file}")
            init_args = dict(args)
            init_args.update({"action": "create_upload_url", "file_path": str(file), "file_name": args.get("file_name") or file.name, "file_size": file.stat().st_size})
            init_payload = json.loads(handle_lineworks_drive(init_args))
            if not init_payload.get("success", True):
                return tool_result(init_payload)
            upload_url = init_payload.get("uploadUrl") or init_payload.get("upload_url")
            if not upload_url:
                return tool_error(f"uploadUrl missing from LINE WORKS response: {init_payload}")
            uploaded = _upload_to_url(account, upload_url, str(file))
            return tool_result({"success": True, "upload_url_response": init_payload, "upload_response": uploaded})
        return tool_error(f"Unsupported drive action: {action}")
    except Exception as exc:
        return tool_error(str(exc))


LINEWORKS_CALENDAR_SCHEMA = {
    "name": "lineworks_calendar",
    "description": "List or create LINE WORKS calendar events. list requires start/end ISO datetimes and is limited to 31 days.",
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["list", "create"], "default": "list"},
            "user_id": {"type": "string", "description": "LINE WORKS userId; use 'me' only if the tenant accepts it."},
            "calendar_id": {"type": "string"},
            "start": {"type": "string", "description": "ISO datetime for list fromDateTime"},
            "end": {"type": "string", "description": "ISO datetime for list untilDateTime"},
            "timezone": {"type": "string"},
            "event": {"type": "object", "description": "Raw LINE WORKS event body for create"},
            "account_id": {"type": "string"},
        },
    },
}

LINEWORKS_TASK_SCHEMA = {
    "name": "lineworks_task",
    "description": "List/create/update/complete LINE WORKS tasks using the official Task REST API.",
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["list", "create", "update", "complete", "incomplete"], "default": "list"},
            "user_id": {"type": "string"},
            "task_id": {"type": "string"},
            "task": {"type": "object", "description": "Raw LINE WORKS task body for create/update"},
            "status": {"type": "string"},
            "limit": {"type": "integer"},
            "cursor": {"type": "string"},
            "account_id": {"type": "string"},
        },
    },
}

LINEWORKS_DRIVE_SCHEMA = {
    "name": "lineworks_drive",
    "description": "List, download, create upload URL, or upload files in LINE WORKS Drive.",
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["list", "download", "create_upload_url", "upload"], "default": "list"},
            "user_id": {"type": "string"},
            "file_id": {"type": "string", "description": "Folder/file ID. Defaults to root for list/upload URL."},
            "parent_file_id": {"type": "string"},
            "file_path": {"type": "string", "description": "Local file path for upload, or output_path for download uses output_path."},
            "output_path": {"type": "string"},
            "file_name": {"type": "string"},
            "file_size": {"type": "integer"},
            "overwrite": {"type": "boolean"},
            "resume": {"type": "boolean"},
            "count": {"type": "integer"},
            "cursor": {"type": "string"},
            "account_id": {"type": "string"},
        },
    },
}

LINEWORKS_TOOLS = (
    ("lineworks_calendar", LINEWORKS_CALENDAR_SCHEMA, handle_lineworks_calendar, "📅"),
    ("lineworks_task", LINEWORKS_TASK_SCHEMA, handle_lineworks_task, "✅"),
    ("lineworks_drive", LINEWORKS_DRIVE_SCHEMA, handle_lineworks_drive, "📁"),
)
