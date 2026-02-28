"""Smoke tests: verify UI modules can be imported without errors."""

import importlib


def test_import_sidebar():
    mod = importlib.import_module("ui.sidebar")
    assert hasattr(mod, "render_sidebar")


def test_import_dashboard():
    mod = importlib.import_module("ui.dashboard")
    assert hasattr(mod, "render_dashboard")


def test_import_charts():
    mod = importlib.import_module("ui.charts")
    assert hasattr(mod, "render_efficient_frontier")


def test_import_action_table():
    mod = importlib.import_module("ui.action_table")
    assert hasattr(mod, "render_action_table")


def test_import_portfolio_manager():
    mod = importlib.import_module("ui.portfolio_manager")
    assert hasattr(mod, "render_portfolio_manager")
