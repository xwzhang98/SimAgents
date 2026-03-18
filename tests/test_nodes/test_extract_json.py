"""Tests for the _extract_json helper in formatter."""
import pytest
from simagents.nodes.formatter import _extract_json

def test_extract_json_raw():
    result = _extract_json('{"genic": {"BoxSize": 100000}, "status": "complete"}')
    assert result["genic"]["BoxSize"] == 100000

def test_extract_json_code_block():
    text = 'Here is the result:\n```json\n{"genic": {}, "status": "complete"}\n```'
    result = _extract_json(text)
    assert result["status"] == "complete"

def test_extract_json_embedded_in_prose():
    text = 'The parameters are: {"genic": {"Ngrid": 64}, "status": "incomplete"} as shown above.'
    result = _extract_json(text)
    assert result["genic"]["Ngrid"] == 64

def test_extract_json_failure():
    with pytest.raises(ValueError, match="Could not extract JSON"):
        _extract_json("This has no JSON at all.")
