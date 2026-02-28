import numpy as np
import pytest

from engine.markowitz import (
    compute_covariance_matrix,
    compute_expected_returns,
    compute_log_returns,
    generate_efficient_frontier,
    optimize_portfolio,
    suggest_targets,
)


class TestComputeLogReturns:
    def test_shape(self, sample_prices_df):
        returns = compute_log_returns(sample_prices_df)
        assert returns.shape[0] == sample_prices_df.shape[0] - 1
        assert returns.shape[1] == sample_prices_df.shape[1]

    def test_no_nans(self, sample_prices_df):
        returns = compute_log_returns(sample_prices_df)
        assert not returns.isna().any().any()


class TestCovarianceMatrix:
    def test_symmetric(self, sample_prices_df):
        returns = compute_log_returns(sample_prices_df)
        sigma = compute_covariance_matrix(returns)
        assert np.allclose(sigma, sigma.T)

    def test_positive_semidefinite(self, sample_prices_df):
        returns = compute_log_returns(sample_prices_df)
        sigma = compute_covariance_matrix(returns)
        eigenvalues = np.linalg.eigvalsh(sigma)
        assert all(ev >= -1e-10 for ev in eigenvalues)

    def test_shape(self, sample_prices_df):
        returns = compute_log_returns(sample_prices_df)
        sigma = compute_covariance_matrix(returns)
        n = sample_prices_df.shape[1]
        assert sigma.shape == (n, n)


class TestExpectedReturns:
    def test_shape(self, sample_prices_df):
        returns = compute_log_returns(sample_prices_df)
        mu = compute_expected_returns(returns)
        assert len(mu) == sample_prices_df.shape[1]


class TestOptimizePortfolio:
    def test_weights_sum_to_one(self, sample_prices_df):
        returns = compute_log_returns(sample_prices_df)
        mu = compute_expected_returns(returns)
        sigma = compute_covariance_matrix(returns)
        result = optimize_portfolio(mu, sigma, 0.1375)
        assert abs(result["weights"].sum() - 1.0) < 1e-6

    def test_weights_nonnegative(self, sample_prices_df):
        returns = compute_log_returns(sample_prices_df)
        mu = compute_expected_returns(returns)
        sigma = compute_covariance_matrix(returns)
        result = optimize_portfolio(mu, sigma, 0.1375)
        assert all(w >= -1e-10 for w in result["weights"])

    def test_returns_volatility_sharpe(self, sample_prices_df):
        returns = compute_log_returns(sample_prices_df)
        mu = compute_expected_returns(returns)
        sigma = compute_covariance_matrix(returns)
        result = optimize_portfolio(mu, sigma, 0.1375)
        assert "return" in result
        assert "volatility" in result
        assert "sharpe" in result
        assert result["volatility"] >= 0


class TestEfficientFrontier:
    def test_generates_points(self, sample_prices_df):
        returns = compute_log_returns(sample_prices_df)
        mu = compute_expected_returns(returns)
        sigma = compute_covariance_matrix(returns)
        frontier = generate_efficient_frontier(mu, sigma, n_points=20)
        assert len(frontier) > 0

    def test_monotonic_risk(self, sample_prices_df):
        returns = compute_log_returns(sample_prices_df)
        mu = compute_expected_returns(returns)
        sigma = compute_covariance_matrix(returns)
        frontier = generate_efficient_frontier(mu, sigma, n_points=20)
        returns_list = [p["return"] for p in frontier]
        # Returns should generally increase along the frontier
        assert returns_list[-1] >= returns_list[0] - 0.01


class TestSuggestTargets:
    def test_blend_factor_zero_preserves_current(self):
        current = {"A": 50.0, "B": 50.0}
        optimal = {"A": 70.0, "B": 30.0}
        result = suggest_targets(current, optimal, 0.0)
        assert result["A"] == pytest.approx(50.0)
        assert result["B"] == pytest.approx(50.0)

    def test_blend_factor_one_equals_optimal(self):
        current = {"A": 50.0, "B": 50.0}
        optimal = {"A": 70.0, "B": 30.0}
        result = suggest_targets(current, optimal, 1.0)
        assert result["A"] == pytest.approx(70.0)
        assert result["B"] == pytest.approx(30.0)

    def test_blend_factor_half(self):
        current = {"A": 40.0, "B": 60.0}
        optimal = {"A": 60.0, "B": 40.0}
        result = suggest_targets(current, optimal, 0.5)
        assert result["A"] == pytest.approx(50.0)
        assert result["B"] == pytest.approx(50.0)

    def test_clamps_blend_factor(self):
        current = {"A": 50.0}
        optimal = {"A": 70.0}
        assert suggest_targets(current, optimal, -0.5)["A"] == pytest.approx(50.0)
        assert suggest_targets(current, optimal, 1.5)["A"] == pytest.approx(70.0)
