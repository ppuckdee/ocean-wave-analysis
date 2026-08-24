"""
Tests for the cleaning logic.

Run with:  python -m pytest tests/ -v

I test the cleaning functions and not the analysis functions on purpose.
Cleaning is where a silent bug does the most damage: a wrong date format or a
missed broken code value produces numbers that look completely reasonable but are
wrong. A regression model producing a bad score, by contrast, is obvious.
"""

import pandas as pd
import pytest

from src import clean_data, config


# ----------------------------------------------------------------------
# Date format detection
# ----------------------------------------------------------------------

def test_detects_day_first_when_first_field_exceeds_12():
    """31 cannot be a month, so the first field must be the day."""
    dates = pd.Series(["31/01/2019 00:00", "05/01/2019 00:30"])
    assert clean_data.detect_date_format(dates) == "%d/%m/%Y %H:%M"


def test_detects_month_first_when_second_field_exceeds_12():
    """25 cannot be a month, so the second field must be the day."""
    dates = pd.Series(["01/25/2017 00:00", "01/05/2017 00:30"])
    assert clean_data.detect_date_format(dates) == "%m/%d/%Y %H:%M"


def test_raises_when_format_is_ambiguous():
    """
    If every value could be read either way, we must refuse to guess.

    This is the single most important test in the project. Guessing here is
    exactly what corrupted the first version of this analysis, so the correct
    behaviour is a loud failure, not a quiet assumption.
    """
    dates = pd.Series(["01/02/2017 00:00", "03/04/2017 00:30"])
    with pytest.raises(ValueError, match="ambiguous"):
        clean_data.detect_date_format(dates)


def test_raises_when_a_group_mixes_both_formats():
    """A group where both fields exceed 12 cannot have one single format."""
    dates = pd.Series(["31/01/2019 00:00", "01/25/2017 00:00"])
    with pytest.raises(ValueError, match="mixes"):
        clean_data.detect_date_format(dates)


# ----------------------------------------------------------------------
# Parsing the real file
# ----------------------------------------------------------------------

@pytest.fixture(scope="module")
def raw():
    from src import load_data
    return load_data.load_raw_waves()


def test_every_date_parses(raw):
    """
    The old pipeline lost 5,232 rows to failed date parsing. This guards
    against that regression: the correct pipeline loses none.
    """
    parsed = clean_data.parse_dates(raw)
    assert parsed["timestamp"].isna().sum() == 0


def test_timeline_is_regular(raw):
    """
    The strongest evidence the dates are right: the buoy samples every 30
    minutes, so a correctly parsed file has an unbroken 30-minute cadence.
    A wrong format would scramble the order and break this.
    """
    parsed = clean_data.parse_dates(raw)
    checks = clean_data.check_timeline(parsed)

    assert checks["gaps_not_30_minutes"] == 0
    assert checks["duplicate_timestamps"] == 0


def test_date_range_matches_the_filename(raw):
    """
    The source file is named "01-2017 to 06-2019". If our parsed dates run past
    June 2019, we have swapped a day for a month somewhere. The original
    pipeline produced a max date of 2019-12-06, which is this bug exactly.
    """
    parsed = clean_data.parse_dates(raw)
    assert parsed["timestamp"].min() == pd.Timestamp("2017-01-01 00:00")
    assert parsed["timestamp"].max() == pd.Timestamp("2019-06-30 23:30")


# ----------------------------------------------------------------------
# Sentinel removal
# ----------------------------------------------------------------------

def test_broken_readings_are_removed():
    frame = pd.DataFrame({
        "Hs": [1.0, -99.9, 2.0],
        "Hmax": [1.7, -99.9, 3.4],
        "Tz": [5.0, -99.9, 6.0],
        "Tp": [9.0, -99.9, 10.0],
        "Peak Direction": [90.0, -99.9, 100.0],
        "SST": [24.0, -99.9, 25.0],
    })
    cleaned = clean_data.remove_broken_readings(frame)
    assert len(cleaned) == 2
    assert config.MISSING_VALUE_CODE not in cleaned.values


def test_partly_broken_reading_is_also_removed():
    """
    A row is dropped if ANY column holds the failure code, not only if all do.
    In the real file 271 rows have a bad Peak Direction while Hs is fine --
    filtering only on Hs (as the first version did) leaves those in.
    """
    frame = pd.DataFrame({
        "Hs": [1.0, 1.5],
        "Hmax": [1.7, 2.5],
        "Tz": [5.0, 5.5],
        "Tp": [9.0, 9.5],
        "Peak Direction": [90.0, -99.9],   # only this one is bad
        "SST": [24.0, 25.0],
    })
    assert len(clean_data.remove_broken_readings(frame)) == 1


def test_no_broken_readings_survive_the_full_pipeline(raw):
    cleaned = clean_data.clean_waves(raw)
    measurements = cleaned[config.MEASUREMENT_COLUMNS]
    assert (measurements == config.MISSING_VALUE_CODE).sum().sum() == 0


def test_cleaning_keeps_most_of_the_data(raw):
    """Sanity check: cleaning should remove a fraction of a percent, not half."""
    cleaned = clean_data.clean_waves(raw)
    assert len(cleaned) / len(raw) > 0.99
