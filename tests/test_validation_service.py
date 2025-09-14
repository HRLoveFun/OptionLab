from services.validation_service import ValidationService

# Helper to build minimal valid form_data

def build_form_data(**overrides):
    base = {
        'ticker': 'AAPL',
        'frequency': 'W',
        'periods': ['12','36'],
        'start_time': '202401',
        'parsed_start_time': __import__('datetime').date(2024,1,1),
        'risk_threshold': 90,
        'side_bias': 'Natural',
        'target_bias': None,
        'option_data': []
    }
    base.update(overrides)
    return base

def test_validation_passes_valid_payload():
    data = build_form_data()
    assert ValidationService.validate_input_data(data) is None

def test_validation_requires_ticker():
    data = build_form_data(ticker='')
    msg = ValidationService.validate_input_data(data)
    assert 'please_enter_a_ticker_symbol' in msg

def test_validation_invalid_start_time():
    data = build_form_data(parsed_start_time=None)
    msg = ValidationService.validate_input_data(data)
    assert 'invalid_start_time_format' in msg

def test_validation_invalid_frequency():
    data = build_form_data(frequency='X')
    msg = ValidationService.validate_input_data(data)
    assert 'invalid_frequency_selected' in msg

def test_validation_risk_threshold_bounds():
    data_low = build_form_data(risk_threshold=-1)
    data_high = build_form_data(risk_threshold=101)
    assert 'risk_threshold_must_be_between_0_and_100' in ValidationService.validate_input_data(data_low)
    assert 'risk_threshold_must_be_between_0_and_100' in ValidationService.validate_input_data(data_high)

def test_validation_invalid_side_bias():
    data = build_form_data(side_bias='Bullish')
    msg = ValidationService.validate_input_data(data)
    assert 'invalid_side_bias_selected' in msg
