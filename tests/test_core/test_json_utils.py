import pytest
from services import json_utils

def test_json_loads_dict():
    data = '{"key": "value"}'
    loaded = json_utils.loads(data)
    assert loaded == {"key": "value"}

def test_json_loads_bytes():
    data = b'{"key": "value"}'
    loaded = json_utils.loads(data)
    assert loaded == {"key": "value"}

def test_json_dumps():
    data = {"key": "value"}
    dumped = json_utils.dumps(data)
    assert isinstance(dumped, bytes)
    assert b'"key"' in dumped
    assert b'"value"' in dumped

def test_modes():
    assert json_utils.get_read_mode() == 'rb'
    assert json_utils.get_write_mode() == 'wb'
