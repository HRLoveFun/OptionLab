"""Tests for services.game_service — input validation layer."""

from services.game_service import GameService


class TestGameServiceValidation:
    def test_missing_ticker(self):
        result = GameService.run({})
        assert result["status"] == "error"
        assert "Ticker" in result["message"]

    def test_budget_too_low(self):
        result = GameService.run({"ticker": "AAPL", "budget": 10})
        assert result["status"] == "error"
        assert "budget" in result["message"]

    def test_budget_too_high(self):
        result = GameService.run({"ticker": "AAPL", "budget": 999_999_999})
        assert result["status"] == "error"
        assert "budget" in result["message"]

    def test_invalid_target_move_positive(self):
        result = GameService.run({"ticker": "AAPL", "target_move_pct": 0.05})
        assert result["status"] == "error"
        assert "target_move_pct" in result["message"]

    def test_invalid_vol_timing(self):
        result = GameService.run({"ticker": "AAPL", "vol_timing": "INSTANT"})
        assert result["status"] == "error"
        assert "vol_timing" in result["message"]

    def test_conviction_out_of_range(self):
        result = GameService.run({"ticker": "AAPL", "directional_conviction": 1.5})
        assert result["status"] == "error"
        assert "directional_conviction" in result["message"]

    def test_horizon_out_of_range(self):
        result = GameService.run({"ticker": "AAPL", "time_horizon_days": 0})
        assert result["status"] == "error"
        assert "time_horizon_days" in result["message"]
