"""
Loading the raw buoy CSV.

This module does one job: get the raw file into a DataFrame, unchanged.
No cleaning happens here. Keeping "load" and "clean" separate means I can
always look at the untouched data to check what cleaning actually did.
"""

import pandas as pd

from . import config


def load_raw_waves() -> pd.DataFrame:
    """
    Read the raw Mooloolaba buoy CSV exactly as it is on disk.

    Deliberately does NOT parse dates. The date column in this file uses two
    different formats in different years, so letting pandas guess here would
    silently corrupt the data. Date parsing is handled explicitly in
    clean_data.parse_dates instead.

    Returns
    -------
    pd.DataFrame
        43,728 rows. The date column is still plain text at this point.
    """
    if config.RAW_CSV_PATH.exists():
        source = config.RAW_CSV_PATH
    else:
        # Fall back to downloading so the project runs on a fresh clone.
        source = config.RAW_CSV_URL

    dataframe = pd.read_csv(source, dtype={config.DATE_COLUMN: str})
    return dataframe


def describe_raw_structure(dataframe: pd.DataFrame) -> pd.DataFrame:
    """
    Build a small summary table describing each column.

    This is the first thing I look at with any new dataset: what each column
    means and how many of its readings are the buoy's -99.9 "broken" code.
    The broken count is the important one, because pandas reports zero missing
    values for this file, which is misleading.
    """
    rows = []
    for column_name in config.MEASUREMENT_COLUMNS:
        column = dataframe[column_name]
        broken_count = (column == config.MISSING_VALUE_CODE).sum()

        rows.append({
            "column": column_name,
            "meaning": config.COLUMN_MEANINGS[column_name],
            "dtype": str(column.dtype),
            "broken_readings": int(broken_count),
            "percent_broken": round(100 * broken_count / len(dataframe), 2),
        })

    return pd.DataFrame(rows)
