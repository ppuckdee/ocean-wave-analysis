"""
The three questions this project answers.

  1. How big are the waves usually?
  2. Which months have the biggest waves?
  3. Which direction do the waves come from?

Every function here does the same basic thing: group the readings somehow, then
count or average them. Nothing more complicated than that.

None of these functions draw charts. They only work out numbers, and plots.py
draws them. Keeping those two jobs apart is why the numbers in the README can
never disagree with the numbers in the charts.
"""

import pandas as pd

from . import config


# ----------------------------------------------------------------------
# Question 1: how big are the waves usually?
# ----------------------------------------------------------------------

def wave_height_summary(waves: pd.DataFrame) -> dict:
    """
    The basic facts about wave height: typical, smallest and biggest.

    I report the median as the "typical" wave rather than the average. The
    median is the middle value, so half the readings are below it and half
    above. That is a fairer description here because a few very big days pull
    the average upwards and make the ocean sound rougher than it usually is.
    """
    heights = waves[config.WAVE_HEIGHT]

    return {
        "readings": len(heights),
        "typical_m": round(heights.median(), 2),
        "average_m": round(heights.mean(), 2),
        "smallest_m": round(heights.min(), 2),
        "biggest_m": round(heights.max(), 2),
    }


def how_often_above_each_height(waves: pd.DataFrame) -> pd.DataFrame:
    """
    How often the waves are at least a given size.

    For each height in the list, count the readings that reached it and turn
    that into a percentage. This answers the practical question a surfer
    actually has: how often is it worth going out?
    """
    heights = waves[config.WAVE_HEIGHT]

    rows = []
    for level in config.HEIGHT_LEVELS:
        readings_at_least_this_big = (heights >= level).sum()
        percent = readings_at_least_this_big / len(heights) * 100

        rows.append({
            "at_least_m": level,
            "readings": int(readings_at_least_this_big),
            "percent_of_time": round(percent, 1),
        })

    return pd.DataFrame(rows)


# ----------------------------------------------------------------------
# Question 2: which months have the biggest waves?
# ----------------------------------------------------------------------

def averages_by_month(waves: pd.DataFrame) -> pd.DataFrame:
    """
    Average wave height and water temperature for each month of the year.

    One thing to be careful about: the data starts in January 2017 and stops in
    June 2019. So January to June appear three times in the data, while July to
    December only appear twice. Simply averaging everything would give the first
    half of the year more weight than the second.

    So this works it out two ways:

      - `simple_average`: every reading averaged together
      - `fair_average`:   each month is averaged within each complete year
                          first, then those yearly figures are averaged, so
                          2017 and 2018 count equally

    If both give the same answer, the pattern is real and not just a side effect
    of when the buoy happened to be recording.
    """
    # Method 1: average all the readings for each month together.
    simple = waves.groupby("month")[config.WAVE_HEIGHT].agg(["mean", "count"])
    simple.columns = ["simple_average", "readings"]

    # Method 2: average each month inside each complete year, then average those.
    complete_years = waves[waves["year"] < 2019]
    month_within_each_year = complete_years.groupby(["year", "month"])[config.WAVE_HEIGHT].mean()
    fair = month_within_each_year.groupby("month").mean()

    # Water temperature for the same months, so we can compare the two.
    temperature = waves.groupby("month")[config.WATER_TEMPERATURE].mean()

    result = simple.copy()
    result["fair_average"] = fair
    result["water_temp_c"] = temperature

    # Turn month numbers into names. The -1 is because months run 1 to 12 but
    # Python lists start counting at 0, so month 1 is MONTH_NAMES[0].
    result["month_name"] = [config.MONTH_NAMES[month - 1] for month in result.index]

    return result


def biggest_and_smallest_months(monthly: pd.DataFrame) -> dict:
    """Pull the headline numbers out of the monthly table."""
    biggest_month = monthly["fair_average"].idxmax()
    smallest_month = monthly["fair_average"].idxmin()

    biggest_height = monthly.loc[biggest_month, "fair_average"]
    smallest_height = monthly.loc[smallest_month, "fair_average"]

    return {
        "biggest_month": config.MONTH_NAMES[biggest_month - 1],
        "biggest_m": round(biggest_height, 2),
        "smallest_month": config.MONTH_NAMES[smallest_month - 1],
        "smallest_m": round(smallest_height, 2),
        "times_bigger": round(biggest_height / smallest_height, 1),
    }


# ----------------------------------------------------------------------
# Question 3: which direction do the waves come from?
# ----------------------------------------------------------------------

def _compass_direction(degrees: float) -> str:
    """
    Turn a direction in degrees into a compass name like "NE" or "SE".

    A compass is 360 degrees split into 8 directions of 45 degrees each.
    North is the awkward one because it wraps around zero: it runs from 337.5
    degrees, past 360, and on to 22.5. So north is checked first as a special
    case, and everything else is a simple "is it between these two numbers".
    """
    if degrees >= 337.5 or degrees < 22.5:
        return "N"

    for lower, upper, name in config.COMPASS_SECTORS:
        if lower <= degrees < upper:
            return name

    # Should never happen for a value between 0 and 360, but better to return
    # something obvious than to fail silently.
    return "unknown"


def count_by_direction(waves: pd.DataFrame) -> pd.DataFrame:
    """
    Count how many readings came from each compass direction.

    Also gives the average wave height per direction, which shows whether the
    biggest waves come from the same place as the most common ones.
    """
    waves = waves.copy()
    waves["direction"] = waves[config.WAVE_DIRECTION].apply(_compass_direction)

    grouped = waves.groupby("direction")[config.WAVE_HEIGHT].agg(["count", "mean"])
    grouped.columns = ["readings", "average_height_m"]

    grouped["percent_of_time"] = (grouped["readings"] / len(waves) * 100).round(1)
    grouped["average_height_m"] = grouped["average_height_m"].round(2)

    # Put them in compass order rather than alphabetical order.
    compass_order = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    directions_present = [d for d in compass_order if d in grouped.index]

    return grouped.loc[directions_present].reset_index()


def most_common_direction(direction_table: pd.DataFrame) -> dict:
    """Pull the headline numbers out of the direction table."""
    busiest = direction_table.loc[direction_table["readings"].idxmax()]

    return {
        "direction": busiest["direction"],
        "percent_of_time": busiest["percent_of_time"],
        "average_height_m": busiest["average_height_m"],
    }
