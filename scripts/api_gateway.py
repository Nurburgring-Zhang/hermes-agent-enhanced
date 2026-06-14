#!/usr/bin/env python3
"""
Hermes API Gateway v1.0
========================
FastAPI-based API gateway with JWT auth, rate limiting, CORS, health checks,
and audit logging. Provides the unified HTTP entry point for Hermes services.

Core features:
  1. JWT Bearer token authentication middleware
  2. Sliding-window rate limiter per client IP/token
  3. CORS configuration for cross-origin requests
  4. Health check endpoint (/health)
  5. Audit log endpoint (/audit)
  6. 8+ API endpoints for agent management

Usage:
  uvicorn scripts.api_gateway:app --host 0.0.0.0 --port 8000
"""

import hashlib
import json
import logging
import os
import secrets
import threading
import time
from datetime import UTC, datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import jwt as pyjwt
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================

HERMES_HOME = Path.home() / ".hermes"
AUDIT_LOG_DIR = HERMES_HOME / "logs" / "api_audit"
AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)

JWT_SECRET = os.environ.get("HERMES_JWT_SECRET", secrets.token_hex(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = int(os.environ.get("HERMES_JWT_EXPIRY", "24"))

# Rate limit defaults
DEFAULT_RATE_LIMIT = int(os.environ.get("HERMES_RATE_LIMIT", "100"))  # requests
DEFAULT_RATE_WINDOW = int(os.environ.get("HERMES_RATE_WINDOW", "60"))  # seconds

# ============================================================================
# Sliding Window Rate Limiter
# ============================================================================


class SlidingWindowRateLimiter:
    """Sliding-window rate limiter with per-key tracking.

    Uses a deque-like approach: each key maps to a list of timestamps.
    On each request, stale timestamps outside the window are pruned,
    and the count of remaining timestamps is checked against the limit.

    Thread-safe via re-entrant lock.
    """

    def __init__(self, default_limit: int = 100, default_window: int = 60):
        self._default_limit = default_limit
        self._default_window = default_window
        self._windows: Dict[str, List[float]] = {}
        self._overrides: Dict[str, tuple] = {}  # key -> (limit, window_seconds)
        self._lock = threading.RLock()
        # GC runs every 5 minutes to clean up stale entries
        self._last_gc = time.monotonic()
        self._gc_interval = 300

    def set_override(self, key: str, limit: int, window_seconds: int) -> None:
        """Set a custom rate limit for a specific key."""
        with self._lock:
            self._overrides[key] = (limit, window_seconds)

    def remove_override(self, key: str) -> None:
        """Remove a custom rate limit override."""
        with self._lock:
            self._overrides.pop(key, None)

    def check(self, key: str) -> bool:
        """Check if the request from `key` is within rate limits.

        Returns True if allowed, False if rate-limited.
        Records the attempt regardless.
        """
        now = time.monotonic()
        with self._lock:
            # Periodic GC
            if now - self._last_gc > self._gc_interval:
                self._gc(now)
                self._last_gc = now

            limit, window = self._overrides.get(
                key, (self._default_limit, self._default_window)
            )

            if key not in self._windows:
                self._windows[key] = []

            timestamps = self._windows[key]

            # Prune stale entries outside the window
            cutoff = now - window
            while timestamps and timestamps[0] < cutoff:
                timestamps.pop(0)

            # Check limit
            if len(timestamps) >= limit:
                return False

            # Record this request
            timestamps.append(now)
            return True

    def remaining(self, key: str) -> int:
        """Return the number of remaining requests in the current window."""
        now = time.monotonic()
        with self._lock:
            limit, window = self._overrides.get(
                key, (self._default_limit, self._default_window)
            )
            if key not in self._windows:
                return limit
            timestamps = self._windows[key]
            cutoff = now - window
            while timestamps and timestamps[0] < cutoff:
                timestamps.pop(0)
            return max(0, limit - len(timestamps))

    def reset(self, key: str) -> None:
        """Reset the rate limit counter for a key."""
        with self._lock:
            self._windows.pop(key, None)

    def _gc(self, now: float) -> None:
        """Remove entries with no recent activity."""
        stale_keys = []
        for key, timestamps in self._windows.items():
            limit, window = self._overrides.get(
                key, (self._default_limit, self._default_window)
            )
            cutoff = now - window
            while timestamps and timestamps[0] < cutoff:
                timestamps.pop(0)
            if not timestamps and key not in self._overrides:
                stale_keys.append(key)
        for key in stale_keys:
            del self._windows[key]


# ============================================================================
# JWT Auth
# ============================================================================


def create_jwt_token(
    subject: str,
    payload: Optional[Dict[str, Any]] = None,
    expiry_hours: Optional[int] = None,
) -> str:
    """Create a signed JWT token."""
    now = datetime.now(UTC)
    exp = now + timedelta(hours=expiry_hours or JWT_EXPIRY_HOURS)
    data = {
        "sub": subject,
        "iat": now,
        "exp": exp,
        "jti": secrets.token_hex(8),
    }
    if payload:
        data.update(payload)
    return pyjwt.encode(data, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt_token(token: str) -> Dict[str, Any]:
    """Decode and verify a JWT token. Raises on invalid/expired token."""
    return pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def verify_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify JWT token, return payload or None on failure."""
    try:
        return decode_jwt_token(token)
    except (pyjwt.ExpiredSignatureError, pyjwt.InvalidTokenError):
        return None


# ============================================================================
# Audit Logging
# ============================================================================


class AuditLogger:
    """JSONL audit log for API requests."""

    def __init__(self, log_dir: Path = AUDIT_LOG_DIR):
        self._log_dir = log_dir
        self._lock = threading.Lock()

    def _log_path(self) -> Path:
        return self._log_dir / f"api_audit_{datetime.now(UTC).strftime('%Y%m%d')}.jsonl"

    def log(
        self,
        method: str,
        path: str,
        client_ip: str,
        status_code: int,
        user: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Write an audit log entry."""
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "method": method,
            "path": path,
            "client_ip": client_ip,
            "status_code": status_code,
            "user": user,
            "request_id": secrets.token_hex(8),
        }
        if extra:
            entry["extra"] = extra
        with self._lock:
            with open(self._log_path(), "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def query(
        self,
        date_str: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Query audit log entries."""
        if date_str is None:
            date_str = datetime.now(UTC).strftime("%Y%m%d")
        log_path = self._log_dir / f"api_audit_{date_str}.jsonl"
        if not log_path.exists():
            return []
        entries = []
        with open(log_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i < offset:
                    continue
                if len(entries) >= limit:
                    break
                try:
                    entries.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue
        return entries


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="Hermes API Gateway",
    description="Unified API gateway for the Hermes AI agent system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Rate limiter instance
rate_limiter = SlidingWindowRateLimiter(
    default_limit=DEFAULT_RATE_LIMIT,
    default_window=DEFAULT_RATE_WINDOW,
)

# Audit logger instance
audit_logger = AuditLogger()

# ============================================================================
# CORS Middleware
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("HERMES_CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-API-Key"],
    expose_headers=["X-RateLimit-Remaining", "X-RateLimit-Limit", "X-Request-ID"],
    max_age=600,
)

# ============================================================================
# JWT Authentication Middleware
# ============================================================================


@app.middleware("http")
async def jwt_auth_middleware(request: Request, call_next: Callable) -> Response:
    """JWT authentication middleware.

    Extracts Bearer token from Authorization header, verifies it,
    and attaches the decoded payload to request.state.user.
    Skips auth for /health, /docs, /redoc, /openapi.json, /token.
    """
    # Public paths (no auth required)
    public_paths = {"/health", "/docs", "/redoc", "/openapi.json", "/token"}
    if request.url.path in public_paths or request.url.path.startswith("/docs"):
        return await call_next(request)

    # Rate limiting
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"ip:{client_ip}"
    if not rate_limiter.check(rate_key):
        audit_logger.log(
            method=request.method,
            path=request.url.path,
            client_ip=client_ip,
            status_code=429,
            extra={"reason": "rate_limited"},
        )
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Try again later."},
        )

    # JWT verification
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        audit_logger.log(
            method=request.method,
            path=request.url.path,
            client_ip=client_ip,
            status_code=401,
            extra={"reason": "missing_token"},
        )
        return JSONResponse(
            status_code=401,
            content={"detail": "Missing or invalid Authorization header"},
        )

    token = auth_header[7:]  # Strip "Bearer "
    payload = verify_jwt_token(token)
    if payload is None:
        audit_logger.log(
            method=request.method,
            path=request.url.path,
            client_ip=client_ip,
            status_code=401,
            extra={"reason": "invalid_token"},
        )
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid or expired token"},
        )

    request.state.user = payload
    request.state.rate_key = rate_key

    # Proceed
    response = await call_next(request)

    # Post-request audit logging
    audit_logger.log(
        method=request.method,
        path=request.url.path,
        client_ip=client_ip,
        status_code=response.status_code,
        user=payload.get("sub"),
    )

    return response


# ============================================================================
# Dependencies
# ============================================================================


def get_current_user(request: Request) -> Dict[str, Any]:
    """FastAPI dependency: get the authenticated user payload."""
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# ============================================================================
# API Endpoints
# ============================================================================


@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint - no auth required."""
    return {
        "status": "healthy",
        "service": "hermes-api-gateway",
        "version": "1.0.0",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.post("/token", tags=["Auth"])
async def create_token(
    username: str = "hermes-agent",
    expiry_hours: Optional[int] = None,
):
    """Create a new JWT token. In production, this would validate credentials."""
    token = create_jwt_token(
        subject=username,
        payload={"role": "agent"},
        expiry_hours=expiry_hours,
    )
    payload = decode_jwt_token(token)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": datetime.fromtimestamp(
            payload["exp"], tz=UTC
        ).isoformat(),
    }


@app.get("/audit", tags=["System"])
async def get_audit_logs(
    request: Request,
    date: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """Query audit log entries. Requires authentication."""
    get_current_user(request)
    entries = audit_logger.query(date_str=date, limit=limit, offset=offset)
    return {
        "date": date or datetime.now(UTC).strftime("%Y%m%d"),
        "count": len(entries),
        "entries": entries,
    }


@app.get("/ratelimit/status", tags=["System"])
async def rate_limit_status(request: Request):
    """Check current rate limit status for the authenticated client."""
    get_current_user(request)
    rate_key = getattr(request.state, "rate_key", None)
    if rate_key is None:
        rate_key = f"ip:{request.client.host}" if request.client else "unknown"
    remaining = rate_limiter.remaining(rate_key)
    return {
        "remaining": remaining,
        "limit": DEFAULT_RATE_LIMIT,
        "window_seconds": DEFAULT_RATE_WINDOW,
    }


@app.get("/agents", tags=["Agents"])
async def list_agents(request: Request):
    """List registered Hermes agents. Requires authentication."""
    get_current_user(request)
    # In a real implementation, this would query the agent registry
    agents = [
        {
            "id": "hermes-main",
            "name": "Hermes Agent",
            "status": "active",
            "model": "deepseek-v4-pro",
            "started_at": datetime.now(UTC).isoformat(),
        }
    ]
    return {"agents": agents, "count": len(agents)}


@app.get("/agents/{agent_id}", tags=["Agents"])
async def get_agent(request: Request, agent_id: str):
    """Get a specific agent's details. Requires authentication."""
    get_current_user(request)
    if agent_id != "hermes-main":
        raise HTTPException(status_code=404, detail="Agent not found")
    return {
        "id": agent_id,
        "name": "Hermes Agent",
        "status": "active",
        "model": "deepseek-v4-pro",
        "config": {
            "max_turns": 999999999,
            "timeout": 180,
        },
    }


@app.post("/agents/{agent_id}/restart", tags=["Agents"])
async def restart_agent(request: Request, agent_id: str):
    """Request an agent restart. Requires authentication."""
    get_current_user(request)
    if agent_id != "hermes-main":
        raise HTTPException(status_code=404, detail="Agent not found")
    return {
        "message": "Restart requested",
        "agent_id": agent_id,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.get("/stats", tags=["System"])
async def get_stats(request: Request):
    """Get system statistics. Requires authentication."""
    get_current_user(request)
    return {
        "uptime_seconds": time.monotonic(),
        "jwt_secret_configured": bool(JWT_SECRET),
        "rate_limiter": {
            "default_limit": DEFAULT_RATE_LIMIT,
            "default_window": DEFAULT_RATE_WINDOW,
        },
        "audit_log_dir": str(AUDIT_LOG_DIR),
    }


@app.get("/", tags=["System"])
async def root():
    """API root - redirects to docs."""
    return {
        "service": "Hermes API Gateway",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


# ============================================================================
# Startup / Shutdown
# ============================================================================


@app.on_event("startup")
async def startup_event():
    """Log startup."""
    logger.info("Hermes API Gateway starting up")
    audit_logger.log(
        method="SYSTEM",
        path="/startup",
        client_ip="localhost",
        status_code=200,
        user="system",
        extra={"event": "gateway_startup"},
    )


@app.on_event("shutdown")
async def shutdown_event():
    """Log shutdown."""
    logger.info("Hermes API Gateway shutting down")
    audit_logger.log(
        method="SYSTEM",
        path="/shutdown",
        client_ip="localhost",
        status_code=200,
        user="system",
        extra={"event": "gateway_shutdown"},
    )


# ============================================================================
# Main entry point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "scripts.api_gateway:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
