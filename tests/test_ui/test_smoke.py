"""Smoke tests: verify UI modules can be imported and have expected interfaces."""

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
    assert hasattr(mod, "render_class_allocation_pie")
    assert hasattr(mod, "render_allocation_chart")
    assert hasattr(mod, "render_deviation_chart")
    assert hasattr(mod, "render_correlation_heatmap")


def test_import_action_table():
    mod = importlib.import_module("ui.action_table")
    assert hasattr(mod, "render_action_table")


def test_import_portfolio_manager():
    mod = importlib.import_module("ui.portfolio_manager")
    assert hasattr(mod, "render_portfolio_manager")


def test_import_reserves():
    mod = importlib.import_module("ui.reserves")
    assert hasattr(mod, "render_emergency_reserve")
    assert hasattr(mod, "render_capital_allocation")
    assert hasattr(mod, "get_reserve_value")


def test_import_tesouro_client():
    mod = importlib.import_module("ingestion.tesouro_client")
    assert hasattr(mod, "get_tesouro_prices")


def test_import_mcp_client():
    mod = importlib.import_module("ingestion.mcp_client")
    assert hasattr(mod, "get_stock_fundamentals")
    assert hasattr(mod, "check_mcp_status")
    assert hasattr(mod, "is_npx_installed")
