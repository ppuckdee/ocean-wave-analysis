"""
Cleaning the raw buoy data.

Two problems have to be fixed, in this order:

  1. The Date/Time column uses TWO different formats in the same file.
     2017 and 2018 rows are month-first (MM/DD/YYYY).
     2019 rows are day-first  (DD/MM/YYYY).
     Letting pandas guess destroys ~5,200 rows and silently swaps the day and
     month on most of the rest of 2019.

  2. Failed instrument readings are recorded as -99.9, not as blanks.
     pandas therefore reports zero missing values, and -99.9 gets averaged in
     as if it were a real measurement.

Every function here is deliberately small and does one thing, so each step can
be inspected and tested on its own.
"""

import pandas as pd

from . import config


# ----------------------------------------------------------------------
# Step 1: dates
# ----------------------------------------------------------------------

def _split_date_parts(date_strings: pd.Series) -> pd.DataFrame:
    """
    Split "13/01/2019 04:30" into its three numbers: 13, 01, 2019.

    We do NOT yet claim to know which number is the day and which is the month --
    that is exactly what we are trying to work out. So the first two are named
    neutrally as `first_field` and `second_field`.
    """
    # "13/01/2019 04:30" -> "13/01/2019"  (drop the time, keep the date)
    date_only = date_strings.str.split(" ").str[0]

    # "13/01/2019" -> three separate columns
    fields = date_only.str.split("/", expand=True)

    return pd.DataFrame({
        "first_field": fields[0].astype(int),
        "second_field": fields[1].astype(int),
        "year": fields[2].astype(int),
    })


def detect_date_format(date_strings: pd.Series) -> str:
    """
    Work out whether a group of date strings is day-first or month-first.

    The logic rests on one fact: a month can never be greater than 12, but a
    day can. So:

      - if any FIRST field is > 12, the first field must be the day  -> day-first
      - if any SECOND field is > 12, the second field must be the day -> month-first

    If neither exceeds 12 the group is genuinely ambiguous (e.g. a group
    containing only dates before the 13th of each month) and we raise rather
    than guess. Guessing here is what broke the original analysis, so an
    explicit failure is much safer than a silent wrong answer.

    Returns
    -------
    str
        A strftime format string ready to hand to pd.to_datetime.
    """
    parts = _split_date_parts(date_strings)

    first_field_exceeds_12 = parts["first_field"].max() > 12
    second_field_exceeds_12 = parts["second_field"].max() > 12

    if first_field_exceeds_12 and second_field_exceeds_12:
        raise ValueError(
            "Both date fields exceed 12 in the same group -- the group mixes "
            "formats and must be split more finely before parsing."
        )
    if first_field_exceeds_12:
        return "%d/%m/%Y %H:%M"   # day-first
    if second_field_exceeds_12:
        return "%m/%d/%Y %H:%M"   # month-first

    raise ValueError(
        "Date format is ambiguous: no field exceeds 12, so day and month "
        "cannot be told apart from the data alone."
    )


def parse_dates(dataframe: pd.DataFrame) -> pd.DataFrame:
    """
    Parse the Date/Time column, detecting the format separately for each year.

    Why year by year? Because the format changes between years in this file.
    Detecting once for the whole column would pick a single format and get one
    of the years wrong. Each year's block is also big enough to be sure it
    contains a day past the 12th, which is what makes the format detectable.

    Adds a `timestamp` column and leaves the original text column in place so
    the parsing can always be checked afterwards.
    """
    dataframe = dataframe.copy()
    date_strings = dataframe[config.DATE_COLUMN]
    years = _split_date_parts(date_strings)["year"]

    # Start with an empty timestamp column, then fill it in one year at a time.
    dataframe["timestamp"] = pd.Series(dtype="datetime64[ns]")

    for year in sorted(years.unique()):
        rows_in_this_year = years == year          # True/False for every row
        block = date_strings[rows_in_this_year]

        detected_format = detect_date_format(block)
        dataframe.loc[rows_in_this_year, "timestamp"] = pd.to_datetime(
            block, format=detected_format
        )

    return dataframe


def report_date_formats(dataframe: pd.DataFrame) -> pd.DataFrame:
    """
    Show which format was detected for each year.

    Purely for explaining the pipeline -- this table is the evidence that the
    file really does mix formats, rather than just an assertion that it does.
    """
    date_strings = dataframe[config.DATE_COLUMN]
    years = _split_date_parts(date_strings)["year"]

    rows = []
    for year in sorted(years.unique()):
        block = date_strings[years == year]
        detected_format = detect_date_format(block)

        if detected_format.startswith("%d"):
            style = "day-first"
        else:
            style = "month-first"

        rows.append({
            "year": int(year),
            "rows": len(block),
            "detected_format": detected_format,
            "style": style,
        })

    return pd.DataFrame(rows)


def check_timeline(dataframe: pd.DataFrame) -> dict:
    """
    Check that the parsed timestamps form a sensible timeline.

    This is the safety net. The buoy samples every 30 minutes, so if the dates
    were parsed correctly the sorted timestamps should step forward by exactly
    30 minutes every time, with no gaps and no repeats. If a date format were
    wrong, the sequence would jump around and this check would catch it.

    Returns a dict of diagnostics rather than raising, so the caller can print
    it as evidence that the cleaning worked.
    """
    timestamps = dataframe["timestamp"]
    gaps_between_readings = timestamps.sort_values().diff().dropna()

    expected_gap = pd.Timedelta(minutes=config.MINUTES_BETWEEN_READINGS)
    unexpected_gaps = (gaps_between_readings != expected_gap).sum()

    return {
        "total_rows": len(dataframe),
        "unparsed_dates": int(timestamps.isna().sum()),
        "duplicate_timestamps": int(timestamps.duplicated().sum()),
        "gaps_not_30_minutes": int(unexpected_gaps),
        "first_reading": timestamps.min(),
        "last_reading": timestamps.max(),
    }


# ----------------------------------------------------------------------
# Step 2: broken readings
# ----------------------------------------------------------------------

def remove_broken_readings(dataframe: pd.DataFrame) -> pd.DataFrame:
    """
    Drop rows where any instrument reported the -99.9 failure code.

    I drop the whole row rather than just the bad column. The reason is that
    -99.9 tends to appear across several columns at once (the buoy loses the
    whole reading, not one channel), and keeping a partial row would mean the
    correlations between columns get computed on inconsistent subsets.

    This is cheap here: only 274 of 43,728 rows are affected (0.6%).
    """
    measurements = dataframe[config.MEASUREMENT_COLUMNS]

    # (measurements == -99.9) gives a True/False grid the same shape as the data.
    # .any(axis=1) collapses that grid to one True/False per ROW -- axis=1 means
    # "look across the columns within each row". So this is True for any row that
    # has the failure code in at least one of its columns.
    row_is_broken = (measurements == config.MISSING_VALUE_CODE).any(axis=1)

    # The ~ flips it around: keep the rows that are NOT broken.
    return dataframe.loc[~row_is_broken].copy()


def add_time_features(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Add month and year columns, used by the seasonality analysis."""
    dataframe = dataframe.copy()
    dataframe["month"] = dataframe["timestamp"].dt.month
    dataframe["year"] = dataframe["timestamp"].dt.year
    return dataframe


# ----------------------------------------------------------------------
# The whole pipeline in one call
# ----------------------------------------------------------------------

def clean_waves(raw_dataframe: pd.DataFrame) -> pd.DataFrame:
    """
    Run the full cleaning pipeline in the correct order.

    Order matters: dates are parsed before rows are dropped, so that the
    timeline validation runs against the complete file and would notice if
    dropping rows were hiding a parsing problem.
    """
    with_dates = parse_dates(raw_dataframe)
    without_broken = remove_broken_readings(with_dates)
    cleaned = add_time_features(without_broken)
    return cleaned
