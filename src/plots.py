"""
Every chart in this project.

Each function takes some numbers, draws one chart, saves it as a picture, and
gives back where it saved it. No working out happens here -- these functions
only draw what analysis.py has already worked out.
"""

import matplotlib
matplotlib.use("Agg")   # save charts to files instead of opening a window
import matplotlib.pyplot as plt

from . import config

# The same few colours everywhere, so all the charts look like a set.
BLUE = "#1f6f8b"
ORANGE = "#e07a3f"
GREY = "#9bb4bd"
RED = "#c0392b"


def _tidy_up(chart, title, x_label, y_label):
    """Apply the same tidying to every chart so they all match."""
    chart.set_title(title, fontsize=13, fontweight="bold", pad=12)
    chart.set_xlabel(x_label, fontsize=10)
    chart.set_ylabel(y_label, fontsize=10)
    chart.spines["top"].set_visible(False)
    chart.spines["right"].set_visible(False)
    chart.grid(axis="y", alpha=0.25, linestyle="--")
    chart.set_axisbelow(True)


def _save(figure, filename):
    """Save a finished chart into the figures folder."""
    config.FIGURES_DIR.mkdir(exist_ok=True)
    path = config.FIGURES_DIR / filename
    figure.tight_layout()
    figure.savefig(path, dpi=140, bbox_inches="tight")
    plt.close(figure)
    return path


def plot_data_problems(format_table, broken_readings_table):
    """The two problems in the data that had to be fixed first."""
    figure, (left, right) = plt.subplots(1, 2, figsize=(12, 4))

    # Left: which years used which date format.
    colours = []
    for style in format_table["style"]:
        if style == "day-first":
            colours.append(ORANGE)
        else:
            colours.append(BLUE)

    labels = []
    for year, style in zip(format_table["year"], format_table["style"]):
        labels.append(f"{year}\n{style}")

    left.bar(labels, format_table["rows"], color=colours)
    _tidy_up(left, "The file uses two different date formats", "", "Readings")

    # Right: how many readings had the -99.9 broken code in each column.
    bars = right.bar(broken_readings_table["column"],
                     broken_readings_table["broken_readings"], color=RED)
    right.bar_label(bars, fontsize=9, padding=2)
    _tidy_up(right, "Readings with the -99.9 broken code", "", "Readings")
    right.tick_params(axis="x", rotation=30)

    figure.suptitle("Neither problem shows up as an error or a missing value",
                    fontsize=10, y=1.02, color="#555")
    return _save(figure, "01_data_problems.png")


def plot_wave_heights(waves, height_table):
    """How big the waves usually are, and how often they reach each size."""
    figure, (left, right) = plt.subplots(1, 2, figsize=(12, 4.5))

    # Left: the spread of wave heights.
    heights = waves[config.WAVE_HEIGHT]
    left.hist(heights, bins=40, color=BLUE, edgecolor="white")
    left.axvline(heights.median(), color=ORANGE, linestyle="--", linewidth=2,
                 label=f"typical wave: {heights.median():.2f} m")
    left.legend(frameon=False, fontsize=9)
    _tidy_up(left, "Most waves are small", "Wave height (m)", "Readings")

    # Right: how often waves reach each size.
    labels = []
    for level in height_table["at_least_m"]:
        labels.append(f"{level} m")

    bars = right.bar(labels, height_table["percent_of_time"], color=BLUE)
    right.bar_label(bars, fmt="%.1f%%", fontsize=9, padding=2)
    right.set_ylim(0, 110)
    _tidy_up(right, "How often waves reach each size",
             "At least this big", "Percent of the time")

    return _save(figure, "02_wave_heights.png")


def plot_by_month(monthly):
    """Average wave height for each month, plus water temperature."""
    figure, (left, right) = plt.subplots(1, 2, figsize=(12, 4.5))

    # Left: the two ways of averaging, side by side.
    positions = range(len(monthly))
    bar_width = 0.4
    left_positions = [p - bar_width / 2 for p in positions]
    right_positions = [p + bar_width / 2 for p in positions]

    left.bar(left_positions, monthly["simple_average"], bar_width,
             label="all readings averaged", color=GREY)
    left.bar(right_positions, monthly["fair_average"], bar_width,
             label="each year counted equally", color=BLUE)

    left.set_xticks(list(positions))
    left.set_xticklabels(monthly["month_name"])
    left.legend(frameon=False, fontsize=9)
    _tidy_up(left, "Wave height by month", "", "Average wave height (m)")

    # Right: water temperature for the same months.
    right.bar(monthly["month_name"], monthly["water_temp_c"], color=ORANGE)
    right.set_ylim(18, 28)
    _tidy_up(right, "Water temperature by month", "", "Degrees C")

    figure.suptitle("The biggest waves arrive when the water is warmest",
                    fontsize=10, y=1.0, color="#555")
    return _save(figure, "03_by_month.png")


def plot_by_direction(direction_table):
    """Which direction the waves come from, and how big they are."""
    figure, (left, right) = plt.subplots(1, 2, figsize=(12, 4.5))

    bars = left.bar(direction_table["direction"],
                    direction_table["percent_of_time"], color=BLUE)
    left.bar_label(bars, fmt="%.1f%%", fontsize=9, padding=2)
    _tidy_up(left, "Where the waves come from", "Compass direction",
             "Percent of the time")

    # Only average the directions that have enough readings to be meaningful.
    # A direction with 3 readings would otherwise get an equally tall bar.
    enough_readings = direction_table[
        direction_table["readings"] >= config.MIN_READINGS_FOR_AVERAGE
    ]

    bars = right.bar(enough_readings["direction"],
                     enough_readings["average_height_m"], color=GREY)
    right.bar_label(bars, fmt="%.2f m", fontsize=9, padding=2)
    _tidy_up(right, f"Average height (directions with {config.MIN_READINGS_FOR_AVERAGE}+ readings)",
             "Compass direction", "Wave height (m)")

    figure.suptitle("Almost all the waves arrive from the east",
                    fontsize=10, y=1.0, color="#555")
    return _save(figure, "04_by_direction.png")
