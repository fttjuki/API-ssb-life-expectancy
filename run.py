"""Download SSB table 05375, clean it, and draw the figure.

Usage:
    python run.py            # fetch fresh data from SSB
    python run.py --offline  # re-use the newest saved raw file in data/raw/
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))

from ssb_life.api import fetch_table, jsonstat_to_dataframe, load_json, save_json  # noqa: E402
from ssb_life.clean import clean_life_expectancy, sex_gap  # noqa: E402
from ssb_life.plot import plot_life_expectancy  # noqa: E402

TABLE_ID = "05375"
SELECTION = {
    "Kjonn": ["1", "2"],        # 1 = men, 2 = women
    "Alder": ["000", "065"],    # age 0 (at birth) and age 65
    "ContentsCode": ["Levetid"],
    "Tid": "*",                 # all years
}

RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
FIGURE_PATH = ROOT / "figures" / "life_expectancy.png"


def get_raw(offline: bool) -> tuple[dict, Path]:
    if offline:
        files = sorted(RAW_DIR.glob(f"{TABLE_ID}_*.json"))
        if not files:
            sys.exit("No saved raw data. Run once without --offline.")
        return load_json(files[-1]), files[-1]

    data = fetch_table(TABLE_ID, SELECTION)
    path = RAW_DIR / f"{TABLE_ID}_{date.today().isoformat()}.json"
    save_json(data, path)
    return data, path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--offline", action="store_true",
                        help="use the newest saved raw file instead of calling the API")
    args = parser.parse_args()

    raw_json, raw_path = get_raw(args.offline)
    print(f"Raw data: {raw_path.relative_to(ROOT)} (SSB updated {raw_json.get('updated', '?')})")

    df = clean_life_expectancy(jsonstat_to_dataframe(raw_json))
    gap = sex_gap(df)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED_DIR / "life_expectancy.csv", index=False)
    gap.to_csv(PROCESSED_DIR / "sex_gap.csv", index=False)

    note = (f"Source: Statistics Norway (SSB), table {TABLE_ID}, via PxWebApi v2. "
            f"Data updated {raw_json.get('updated', '')[:10]}.")
    plot_life_expectancy(df, FIGURE_PATH, note)

    first, last = df["year"].min(), df["year"].max()
    at_birth = gap[gap["age"] == 0].set_index("year")["gap_women_minus_men"]
    print(f"{len(df)} rows, {first}–{last}")
    print(f"Gap at birth (women − men): {at_birth[first]:.2f} years in {first}, "
          f"{at_birth[last]:.2f} years in {last}")
    print(f"Figure: {FIGURE_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
