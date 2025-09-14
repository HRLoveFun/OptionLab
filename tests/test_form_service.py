import pytest
from services.form_service import FormService
from flask import Flask, request

class DummyRequest:
    def __init__(self, form_dict):
        self.form = form_dict
    def getlist(self, key):
        return self.form.get(key, [])

def test_extract_form_data_valid():
    form_dict = {
        'ticker': 'AAPL',
        'frequency': 'W',
        'period': ['12', '36'],
        'start_time': '202201',
        'risk_threshold': '90',
        'side_bias': 'Natural',
        'option_position': ''
    }
    req = DummyRequest(form_dict)
    data = FormService.extract_form_data(req)
    assert data['ticker'] == 'AAPL'
    assert data['frequency'] == 'W'
    assert data['periods'] == ['12', '36']
    assert data['start_time'] == '202201'
    assert data['parsed_start_time'].year == 2022
    assert data['risk_threshold'] == 90
    assert data['side_bias'] == 'Natural'
    assert data['option_data'] == []

def test_extract_form_data_invalid_date():
    form_dict = {
        'ticker': 'AAPL',
        'frequency': 'W',
        'period': ['12', '36'],
        'start_time': 'badval',
        'risk_threshold': '90',
        'side_bias': 'Natural',
        'option_position': ''
    }
    req = DummyRequest(form_dict)
    data = FormService.extract_form_data(req)
    assert data['parsed_start_time'] is None
