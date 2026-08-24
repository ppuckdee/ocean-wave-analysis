"""
Every setting and constant used in this project, kept in one place.

If a number is used in more than one file, it belongs here. That way there is
only ever one line to change, and no risk of two files disagreeing.
"""

from pathlib import Path

# --- Where things live -------------------------------------------------
# Path(__file__) is this file, .parent is the src folder, and .parent.parent
# is the main project folder. Building paths this way means the code works no
# matter which folder you run it from.
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
FIGURES_DIR = PROJECT_ROOT / "figures"

RAW_CSV_PATH = DATA_DIR / "waves_raw.csv"

# Used only if the local file is missing, so the project still runs.
RAW_CSV_URL = (
    "https://raw.githubusercontent.com/ppuckdee/mooloolaba-buoy-data/"
    "refs/heads/main/Coastal%20Data%20System%20-%20Waves%20(Mooloolaba)"
    "%2001-2017%20to%2006%20-%202019.csv"
)

# --- Things about the data ---------------------------------------------
# When an instrument on the buoy fails, it writes -99.9 instead of leaving the
# space blank. It is NOT a real measurement, and it has to be removed before
# anything is averaged.
MISSING_VALUE_CODE = -99.9

# The buoy takes a reading every 30 minutes. We use this to check that our
# dates were read correctly (see clean_data.check_timeline).
MINUTES_BETWEEN_READINGS = 30

DATE_COLUMN = "Date/Time"

# The columns of measurements, and what each one means.
MEASUREMENT_COLUMNS = ["Hs", "Hmax", "Tz", "Tp", "Peak Direction", "SST"]

COLUMN_MEANINGS = {
    "Hs": "Wave height (m)",
    "Hmax": "Biggest single wave in the reading (m)",
    "Tz": "Average seconds between waves",
    "Tp": "Seconds between the biggest waves",
    "Peak Direction": "Direction the waves come from (degrees)",
    "SST": "Water temperature (degrees C)",
}

WAVE_HEIGHT = "Hs"
WATER_TEMPERATURE = "SST"
WAVE_DIRECTION = "Peak Direction"

# --- Settings for the three questions ----------------------------------
# Wave heights we count how often we get. Chosen to cover flat days through to
# the biggest days in the data.
HEIGHT_LEVELS = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]

# A compass has 360 degrees split into 8 directions of 45 degrees each.
# North is left out of this list because it wraps around 0 (it runs from
# 337.5 through 360 and on to 22.5), so it is handled separately in the code.
COMPASS_SECTORS = [
    (22.5, 67.5, "NE"),
    (67.5, 112.5, "E"),
    (112.5, 157.5, "SE"),
    (157.5, 202.5, "S"),
    (202.5, 247.5, "SW"),
    (247.5, 292.5, "W"),
    (292.5, 337.5, "NW"),
]

# Some directions only have a handful of readings. An average of 3 readings
# is not meaningful, so directions below this many readings are left out of
# the average-height chart (they still appear in the counts).
MIN_READINGS_FOR_AVERAGE = 100

MONTH_NAMES = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]
