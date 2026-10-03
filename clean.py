"""Cleaning and checks for SSB table 05375 (life expectancy by sex and age)."""

from __future__ import annotations

import pandas as pd

SEX_LABELS = {"1": "Men", "2": "Women"}


def clean_life_expectancy(raw: pd.DataFrame) -> pd.DataFrame:
    """Tidy the long JSON-stat table into analysis-ready columns.

    Output columns: year (int), sex (str), age (int), life_expectancy (float).
    """
    df = pd.DataFrame(
        {
            "year": raw["Tid_code"].astype(int),
            "sex": raw["Kjonn_code"].map(SEX_LABELS),
            "age": raw["Alder_code"].astype(int),  # "065" -> 65
            "life_expectancy": pd.to_numeric(raw["value"], errors="coerce"),
        }
    )

    n_missing = df["life_expectancy"].isna().sum()
    if n_missing:
        print(f"Note: dropping {n_missing} cells with no value")
        df = df.dropna(subset=["life_expectancy"])

    df = df.sort_values(["sex", "age", "year"]).reset_index(drop=True)
    validate(df)
    return df


def validate(df: pd.DataFrame) -> None:
    """Fail loudly if the data look wrong, instead of plotting nonsense."""
    if df["sex"].isna().any():
        raise ValueError("Unknown sex code in data")
    if df.duplicated(["year", "sex", "age"]).any():
        raise ValueError("Duplicate year/sex/age rows")
    remaining_years = df["life_expectancy"]
    if not remaining_years.between(0, 110).all():
        raise ValueError("Life expectancy outside plausible range 0-110")
    # Remaining life expectancy must fall with age within a sex and year
    for _, group in df.groupby(["sex", "year"]):
        ordered = group.sort_values("age")["life_expectancy"]
        if not ordered.is_monotonic_decreasing:
            raise ValueError("Remaining life expectancy does not decrease with age")


def sex_gap(df: pd.DataFrame) -> pd.DataFrame:
    """Women minus men, in years, for each year and age."""
    wide = df.pivot_table(index=["year", "age"], columns="sex", values="life_expectancy")
    out = (wide["Women"] - wide["Men"]).rename("gap_women_minus_men").reset_index()
    return out
