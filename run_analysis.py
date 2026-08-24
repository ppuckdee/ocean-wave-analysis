"""
Run the whole project from start to finish.

    python run_analysis.py

Prints every number and saves all the charts into the figures folder.
Reading this file from top to bottom tells you exactly what the project does.
"""

from src import analysis, clean_data, config, load_data, plots


def heading(text):
    print(f"\n{'=' * 66}\n{text}\n{'=' * 66}")


def main():
    # ------------------------------------------------------------------
    heading("STEP 1  Open the file and see what is in it")
    # ------------------------------------------------------------------
    raw = load_data.load_raw_waves()
    print(f"Opened {len(raw):,} readings, {len(raw.columns)} columns")

    print("\nIs anything missing? Python says no:")
    print(raw.isna().sum().to_string())

    print("\nBut that is misleading. Broken readings are written as -99.9:")
    broken_table = load_data.describe_raw_structure(raw)
    print(broken_table[["column", "meaning", "broken_readings"]].to_string(index=False))

    # ------------------------------------------------------------------
    heading("STEP 2  Fix the dates (the file uses two formats)")
    # ------------------------------------------------------------------
    format_table = clean_data.report_date_formats(raw)
    print(format_table.to_string(index=False))

    print("\nReading each year with its own format...")
    with_dates = clean_data.parse_dates(raw)

    print("\nChecking the dates came out right:")
    checks = clean_data.check_timeline(with_dates)
    for name, value in checks.items():
        print(f"  {name:24s} {value}")
    print("\n  The buoy records every 30 minutes, so if the dates are right,")
    print("  every gap should be exactly 30 minutes. They all are.")

    # ------------------------------------------------------------------
    heading("STEP 3  Remove the broken readings")
    # ------------------------------------------------------------------
    waves = clean_data.clean_waves(raw)
    removed = len(raw) - len(waves)
    print(f"Removed {removed} broken readings ({removed / len(raw) * 100:.2f}%)")
    print(f"Kept    {len(waves):,} readings ({len(waves) / len(raw) * 100:.1f}%)")

    print("\nWhat this did to the water temperature:")
    print(f"  before: average {raw['SST'].mean():.1f} C, coldest {raw['SST'].min():.1f} C")
    print(f"  after:  average {waves['SST'].mean():.1f} C, coldest {waves['SST'].min():.1f} C")

    plots.plot_data_problems(format_table, broken_table)

    # ------------------------------------------------------------------
    heading("QUESTION 1  How big are the waves usually?")
    # ------------------------------------------------------------------
    summary = analysis.wave_height_summary(waves)
    for name, value in summary.items():
        print(f"  {name:14s} {value}")

    print("\nHow often the waves reach each size:")
    height_table = analysis.how_often_above_each_height(waves)
    print(height_table.to_string(index=False))
    plots.plot_wave_heights(waves, height_table)

    # ------------------------------------------------------------------
    heading("QUESTION 2  Which months have the biggest waves?")
    # ------------------------------------------------------------------
    monthly = analysis.averages_by_month(waves)
    print(monthly[["month_name", "simple_average", "fair_average",
                   "water_temp_c", "readings"]].round(2).to_string(index=False))

    months = analysis.biggest_and_smallest_months(monthly)
    print(f"\n  Biggest waves:  {months['biggest_month']} ({months['biggest_m']} m)")
    print(f"  Smallest waves: {months['smallest_month']} ({months['smallest_m']} m)")
    print(f"  That is {months['times_bigger']} times bigger")
    plots.plot_by_month(monthly)

    # ------------------------------------------------------------------
    heading("QUESTION 3  Which direction do the waves come from?")
    # ------------------------------------------------------------------
    directions = analysis.count_by_direction(waves)
    print(directions.to_string(index=False))

    busiest = analysis.most_common_direction(directions)
    print(f"\n  Most waves come from the {busiest['direction']}: "
          f"{busiest['percent_of_time']}% of the time")
    plots.plot_by_direction(directions)

    # ------------------------------------------------------------------
    heading("FINISHED")
    # ------------------------------------------------------------------
    print(f"Charts saved into {config.FIGURES_DIR}")


if __name__ == "__main__":
    main()
