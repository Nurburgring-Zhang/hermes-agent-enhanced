#!/usr/bin/env python3
"""Tests for unified_dashboard.py — Flask API endpoints and helper functions."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

HERMES_DIR = Path(__file__).parent.parent
SCRIPTS_DIR = Path(__file__).parent
if str(HERMES_DIR) not in sys.path:
    sys.path.insert(0, str(HERMES_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# Import the module once, mocking dir creation during import
with patch("pathlib.Path.mkdir"), patch("pathlib.Path.exists", return_value=True):
    import unified_dashboard as ud

ud.app.config["TESTING"] = True


@pytest.fixture
def app(monkeypatch):
    """Flask app with get_db returning None (no DB available)."""
    monkeypatch.setattr(ud, "get_db", lambda path: None)
    return ud.app


@pytest.fixture
def client(app):
    return app.test_client()


# ============================================================

class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"
        assert "timestamp" in data
        assert "services" in data

    def test_health_services_keys(self, client):
        resp = client.get("/api/health")
        data = resp.get_json()
        svc = data["services"]
        assert "production" in svc


class TestStatsEndpoint:
    def test_stats_returns_json(self, client):
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "production" in data
        assert "intelligence" in data
        assert "airi" in data

    def test_stats_production_defaults_when_no_db(self, client):
        resp = client.get("/api/stats")
        data = resp.get_json()
        prod = data["production"]
        assert prod["pipelines"] == 0
        assert prod["requirements"] == 0
        assert prod["active"] == 0


class TestPipelinesEndpoint:
    def test_pipelines_returns_empty_list_when_no_db(self, client):
        resp = client.get("/api/pipelines")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "pipelines" in data
        assert data["pipelines"] == []

    def test_pipelines_is_json(self, client):
        resp = client.get("/api/pipelines")
        assert resp.is_json


class TestRequirementsEndpoint:
    def test_requirements_returns_empty_list_when_no_db(self, client):
        resp = client.get("/api/requirements")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "requirements" in data
        assert data["requirements"] == []

    def test_requirements_is_json(self, client):
        resp = client.get("/api/requirements")
        assert resp.is_json


class TestLogsEndpoint:
    def test_logs_returns_empty_list_when_no_db(self, client):
        resp = client.get("/api/logs")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "logs" in data
        assert data["logs"] == []

    def test_logs_accepts_limit_param(self, client):
        resp = client.get("/api/logs?limit=10")
        assert resp.status_code == 200


class TestEventsEndpoint:
    def test_events_returns_empty_list_when_no_db(self, client):
        resp = client.get("/api/events")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "events" in data
        assert data["events"] == []

    def test_events_pagination_params(self, client):
        # When no DB, events endpoint returns just {"events": []} without pagination keys
        resp = client.get("/api/events?page=1&limit=5")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "events" in data

    def test_events_filter_platform(self, client):
        resp = client.get("/api/events?platform=github")
        assert resp.status_code == 200

    def test_events_filter_level(self, client):
        resp = client.get("/api/events?level=4")
        assert resp.status_code == 200


class TestEventDetailEndpoint:
    def test_event_detail_not_found_when_no_db(self, client):
        resp = client.get("/api/event/99999")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "error" in data


class TestTrendsEndpoint:
    def test_trends_returns_empty_list_when_no_db(self, client):
        resp = client.get("/api/trends")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "trends" in data
        assert data["trends"] == []

    def test_trends_accepts_days_param(self, client):
        resp = client.get("/api/trends?days=30")
        assert resp.status_code == 200


class TestAIRIEndpoints:
    def test_airi_character_default_state_when_no_db(self, client):
        resp = client.get("/api/airi/character")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["state"] == "idle"

    def test_airi_conversation_empty_message(self, client):
        resp = client.post(
            "/api/airi/conversation",
            data=json.dumps({"message": "", "persona": "companion"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "error" in data


class TestGetDbHelper:
    def test_get_db_nonexistent_returns_none(self, client):
        # Restore original get_db for this test
        original = ud.get_db
        try:
            result = original("/nonexistent/path/to/db.sqlite")
            assert result is None
        finally:
            pass


class TestAppConfig:
    def test_app_secret_key_set(self, app):
        assert app.secret_key is not None
        assert len(app.secret_key) > 0

    def test_json_ascii_false(self, app):
        assert app.config.get("JSON_AS_ASCII") is False

    def test_template_and_static_folders(self, app):
        assert app.template_folder is not None
        assert app.static_folder is not None
