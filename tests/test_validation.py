"""Tests for services/validation_service.py."""
import pytest

from services.validation_service import ValidationService


def _base_form(**overrides):
    """Return a minimal valid form_data dict, with optional overrides."""
    data = {
        "ticker": "AAPL",
        "parsed_start_time": "2023-01-01",
        "start_time": "202301",
        "frequency": "ME",
        "risk_threshold": 90,
        "rolling_window": 120,
        "side_bias": "Neutral",
    }
    data.update(overrides)
    return data


class TestValidateInputData:
    def test_valid_input_returns_none(self):
        assert ValidationService.validate_input_data(_base_form()) is None

    def test_empty_ticker(self):
        err = ValidationService.validate_input_data(_base_form(ticker=""))
        assert err is not None
        assert "ticker" in err.lower()

    def test_invalid_frequency(self):
        err = ValidationService.validate_input_data(_base_form(frequency="X"))
        assert err is not None
        assert "frequency" in err.lower()

    def test_risk_threshold_out_of_range(self):
        assert ValidationService.validate_input_data(_base_form(risk_threshold=101)) is not None
        assert ValidationService.validate_input_data(_base_form(risk_threshold=-1)) is not None

    def test_risk_threshold_boundary(self):
        assert ValidationService.validate_input_data(_base_form(risk_threshold=0)) is None
        assert ValidationService.validate_input_data(_base_form(risk_threshold=100)) is None

    def test_invalid_side_bias(self):
        err = ValidationService.validate_input_data(_base_form(side_bias="Bull"))
        assert err is not None

    def test_rolling_window_zero(self):
        err = ValidationService.validate_input_data(_base_form(rolling_window=0))
        assert err is not None


class TestPositionSizingValidation:
    def test_valid_account_size(self):
        assert ValidationService.validate_position_sizing_params({"account_size": 50000}) is None

    def test_negative_account_size(self):
        err = ValidationService.validate_position_sizing_params({"account_size": -100})
        assert err is not None

    def test_account_size_exceeds_max(self):
        err = ValidationService.validate_position_sizing_params({"account_size": 2_000_000_000})
        assert err is not None

    def test_risk_pct_valid(self):
        assert ValidationService.validate_position_sizing_params({"max_risk_pct": 2.0}) is None

    def test_risk_pct_too_low(self):
        err = ValidationService.validate_position_sizing_params({"max_risk_pct": 0.05})
        assert err is not None

    def test_risk_pct_too_high(self):
        err = ValidationService.validate_position_sizing_params({"max_risk_pct": 25.0})
        assert err is not None

    def test_none_params_accepted(self):
        assert ValidationService.validate_position_sizing_params({}) is None
