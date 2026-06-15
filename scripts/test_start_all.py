#!/usr/bin/env python3
"""Tests for start_all.py — module imports, config loading, and utility functions."""

import sys
from pathlib import Path

import pytest

# Ensure parent hermes dir on path so start_all imports work
HERMES_DIR = Path(__file__).parent.parent
SCRIPTS_DIR = Path(__file__).parent
if str(HERMES_DIR) not in sys.path:
    sys.path.insert(0, str(HERMES_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import start_all


class TestModuleImports:
    """Verify start_all.py can be imported and its constants are accessible."""

    def test_services_dict_exists(self):
        assert hasattr(start_all, "SERVICES")
        assert isinstance(start_all.SERVICES, dict)

    def test_services_has_at_least_two_entries(self):
        assert len(start_all.SERVICES) >= 2

    def test_services_expected_keys(self):
        # Core services that should exist
        core_keys = ["web_dashboard", "unified_dashboard"]
        for key in core_keys:
            assert key in start_all.SERVICES, f"Missing service: {key}"

    def test_each_service_has_port_and_path_and_name(self):
        for name, config in start_all.SERVICES.items():
            assert "port" in config, f"{name} missing port"
            assert "path" in config, f"{name} missing path"
            assert "name" in config, f"{name} missing name"
            assert isinstance(config["port"], int)
            assert config["port"] > 0
            assert isinstance(config["path"], Path)

    def test_services_have_unique_ports(self):
        ports = [c["port"] for c in start_all.SERVICES.values()]
        assert len(ports) == len(set(ports)), "Ports must be unique"

    def test_home_is_path(self):
        assert hasattr(start_all, "HOME")
        assert isinstance(start_all.HOME, Path)

    def test_main_function_exists(self):
        assert callable(start_all.main)

    def test_status_function_exists(self):
        assert callable(start_all.status)


class TestUtilityFunctions:
    """Test core utility functions from start_all.py."""

    def test_is_port_in_use_signature(self):
        assert callable(start_all.is_port_in_use)

    def test_kill_port_signature(self):
        assert callable(start_all.kill_port)

    def test_start_service_signature(self):
        assert callable(start_all.start_service)

    def test_stop_service_signature(self):
        assert callable(start_all.stop_service)

    def test_services_paths_are_under_hermes(self):
        for name, config in start_all.SERVICES.items():
            hermes_str = str(config["path"])
            assert ".hermes" in hermes_str, f"{name} path not under .hermes: {hermes_str}"


class TestServiceConfig:
    """Validate the SERVICES configuration dictionary."""

    def test_web_dashboard_port(self):
        assert start_all.SERVICES["web_dashboard"]["port"] == 4000

    def test_airi_assistant_port_if_present(self):
        if "airi_assistant" in start_all.SERVICES:
            assert start_all.SERVICES["airi_assistant"]["port"] == 4002

    def test_unified_dashboard_port(self):
        assert start_all.SERVICES["unified_dashboard"]["port"] == 4003

    def test_service_names_are_strings(self):
        for name, config in start_all.SERVICES.items():
            assert isinstance(config["name"], str)
            assert len(config["name"]) > 0
