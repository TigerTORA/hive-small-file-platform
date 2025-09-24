"""
Simple test to verify pytest setup
"""

import pytest


def test_basic_math():
    """Basic test to verify pytest works"""
    assert 1 + 1 == 2


def test_string_operations():
    """Test string operations"""
    result = "hello" + " world"
    assert result == "hello world"
    assert len(result) == 11


@pytest.mark.unit
def test_list_operations():
    """Test list operations with marker"""
    data = [1, 2, 3]
    data.append(4)
    assert len(data) == 4
    assert 4 in data


if __name__ == "__main__":
    pytest.main([__file__])
