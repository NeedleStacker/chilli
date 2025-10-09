import pytest
from sensors import read_soil_percent_from_voltage

def test_read_soil_percent_from_voltage_with_none_input():
    """
    Verifies that read_soil_percent_from_voltage returns 0.0 when
    the input voltage is None. This simulates a failed sensor reading.
    """
    assert read_soil_percent_from_voltage(None) == 0.0

def test_read_soil_percent_from_voltage_with_valid_input(monkeypatch):
    """
    Verifies that read_soil_percent_from_voltage calculates the
    percentage correctly with a valid voltage input, using a mocked
    calibration function to ensure the test is self-contained.
    """
    # Mock the load_calibration function to return predictable values
    monkeypatch.setattr('sensors.load_calibration', lambda: {"dry_v": 1.6, "wet_v": 0.2})

    # Formula: 100 * (dry_v - voltage) / (dry_v - wet_v)
    # 100 * (1.6 - 0.9) / (1.6 - 0.2) = 100 * 0.7 / 1.4 = 50.0
    assert read_soil_percent_from_voltage(0.9) == pytest.approx(50.0)

    # Test clamping at 100%
    # A voltage of 0.1V would calculate to >100%, so it should be clamped to 100.0
    assert read_soil_percent_from_voltage(0.1) == 100.0

    # Test clamping at 0%
    # A voltage of 1.7V would calculate to <0%, so it should be clamped to 0.0
    assert read_soil_percent_from_voltage(1.7) == 0.0