"""Shared test fixtures for the ts-data-generator test suite."""

import pytest
import pandas as pd


@pytest.fixture
def sample_csv_with_index(tmp_path):
    """Create a sample CSV file with a datetime index column."""
    csv_content = """datetime,product,sales,quantity
2019-01-01 00:00:00,A,10.5,100
2019-01-01 00:05:00,B,20.3,200
2019-01-01 00:10:00,A,15.7,150
2019-01-01 00:15:00,C,25.1,175
2019-01-01 00:20:00,B,30.4,225
"""
    csv_file = tmp_path / "test_data.csv"
    csv_file.write_text(csv_content)
    return str(csv_file)


@pytest.fixture
def sample_csv_without_header(tmp_path):
    """Create a sample CSV file without a header row."""
    csv_content = """2019-01-01 00:00:00,A,10.5,100
2019-01-01 00:05:00,B,20.3,200
2019-01-01 00:10:00,A,15.7,150
2019-01-01 00:15:00,C,25.1,175
2019-01-01 00:20:00,B,30.4,225
"""
    csv_file = tmp_path / "test_data_no_header.csv"
    csv_file.write_text(csv_content)
    return str(csv_file)
