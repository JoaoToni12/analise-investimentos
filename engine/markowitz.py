from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from config import TRADING_DAYS_PER_YEAR


def compute_log_returns(prices_df: pd.DataFrame) -> pd.DataFrame:
    """Compute daily log returns from a price DataFrame."""
    return np.log(prices_df / prices_df.shift(1)).dropna()


def compute_covariance_matrix(returns_df: pd.DataFrame) -> np.ndarray:
    """Annualized covariance matrix Σ."""
    return returns_df.cov().values * TRADING_DAYS_PER_YEAR


def compute_expected_returns(returns_df: pd.DataFrame) -> np.ndarray:
    """Annualized expected returns vector μ (mean of log returns)."""
    return returns_df.mean().values * TRADING_DAYS_PER_YEAR


def optimize_portfolio(
    mu: np.ndarray,
    sigma: np.ndarray,
    risk_free_rate: float = 0.1375,
) -> dict:
    """Find the maximum-Sharpe-ratio portfolio on the efficient frontier.

    Constraints: long-only (w >= 0), fully invested (sum(w) = 1).
    """
    n = len(mu)
    w0 = np.ones(n) / n

    def neg_sharpe(w: np.ndarray) -> float:
        port_ret = w @ mu
        port_vol = np.sqrt(w @ sigma @ w)
        if port_vol < 1e-12:
            return 0.0
        return -(port_ret - risk_free_rate) / port_vol

    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    bounds = [(0.0, 1.0)] * n

    result = minimize(neg_sharpe, w0, method="SLSQP", bounds=bounds, constraints=constraints)

    weights = result.x
    port_return = float(weights @ mu)
    port_vol = float(np.sqrt(weights @ sigma @ weights))
    sharpe = (port_return - risk_free_rate) / port_vol if port_vol > 1e-12 else 0.0

    return {
        "weights": weights,
        "return": port_return,
        "volatility": port_vol,
        "sharpe": sharpe,
    }


def minimize_variance(
    sigma: np.ndarray,
    target_return: float,
    mu: np.ndarray,
) -> dict:
    """Find the minimum-variance portfolio for a given target return."""
    n = len(mu)
    w0 = np.ones(n) / n

    def portfolio_variance(w: np.ndarray) -> float:
        return float(w @ sigma @ w)

    constraints = [
        {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
        {"type": "eq", "fun": lambda w: w @ mu - target_return},
    ]
    bounds = [(0.0, 1.0)] * n

    result = minimize(portfolio_variance, w0, method="SLSQP", bounds=bounds, constraints=constraints)

    weights = result.x
    port_vol = float(np.sqrt(weights @ sigma @ weights))
    return {"weights": weights, "return": target_return, "volatility": port_vol}


def generate_efficient_frontier(
    mu: np.ndarray,
    sigma: np.ndarray,
    n_points: int = 50,
) -> list[dict]:
    """Generate points along the efficient frontier from min to max feasible return."""
    min_ret = float(np.min(mu))
    max_ret = float(np.max(mu))

    if max_ret - min_ret < 1e-10:
        return []

    target_returns = np.linspace(min_ret, max_ret, n_points)
    frontier: list[dict] = []

    for target in target_returns:
        try:
            point = minimize_variance(sigma, float(target), mu)
            if point["volatility"] > 0:
                frontier.append(point)
        except Exception:
            continue

    return frontier


def suggest_targets(
    current_weights: dict[str, float],
    optimal_weights: dict[str, float],
    blend_factor: float,
) -> dict[str, float]:
    """Blend current allocation with Markowitz-optimal allocation.

    blend_factor: 0.0 = keep current, 1.0 = fully Markowitz.
    Returns suggested target weights (%).
    """
    blend_factor = max(0.0, min(1.0, blend_factor))
    all_tickers = set(current_weights) | set(optimal_weights)
    result: dict[str, float] = {}
    for ticker in all_tickers:
        curr = current_weights.get(ticker, 0.0)
        opt = optimal_weights.get(ticker, 0.0)
        result[ticker] = curr * (1 - blend_factor) + opt * blend_factor
    return result
