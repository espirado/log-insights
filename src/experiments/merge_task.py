"""
Data Engineer Certification - Practical Exam - Supplement (Solution Helper)

This module provides the `merge_all_data` function expected by the task
screenshots. It reads four CSV inputs, cleans and merges them into a single
daily dataset with the required columns and conversions.

Expected signature (per instructions panel):
    merge_all_data('user_health_data.csv',
                   'supplement_usage.csv',
                   'experiments.csv',
                   'user_profiles.csv')

Return value:
    pandas.DataFrame with columns exactly:
        ['user_id', 'date', 'email', 'user_age_group', 'experiment_name',
         'supplement_name', 'dosage_grams', 'is_placebo',
         'average_heart_rate', 'average_glucose', 'sleep_hours',
         'activity_level']

Notes and assumptions derived from the brief:
- Unique row per user/day per supplement usage. If no supplement on a day for a
  user, still include a row with `supplement_name` = 'No intake' and the rest of
  supplement-specific fields left missing (NaN/None), except `is_placebo` which
  remains missing as well.
- Convert dosage to grams: if `dosage_unit` == 'mg' divide by 1000; if 'g'
  keep as-is; otherwise leave missing.
- Bucket age into groups: 'Under 18', '18-25', '26-35', '36-45', '46-55',
  '56-65', 'Over 65', or 'Unknown' when age is missing.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd


AGE_BINS = [-float("inf"), 18, 26, 36, 46, 56, 66, float("inf")]
AGE_LABELS = [
    "Under 18",
    "18-25",
    "26-35",
    "36-45",
    "46-55",
    "56-65",
    "Over 65",
]


def _to_date(series: pd.Series) -> pd.Series:
    """Parse a series to pandas datetime.date, preserving NaT for invalids."""
    dt = pd.to_datetime(series, errors="coerce")
    return dt.dt.date


def _age_to_group(age_series: pd.Series) -> pd.Series:
    """Map numerical age to the required age groups; 'Unknown' for missing."""
    groups = pd.cut(age_series, bins=AGE_BINS, labels=AGE_LABELS, right=False)
    return groups.astype("object").fillna("Unknown")


def _compute_dosage_grams(dosage: pd.Series, unit: pd.Series) -> pd.Series:
    """Convert dosage to grams given unit series ('mg' or 'g')."""
    dosage_float = pd.to_numeric(dosage, errors="coerce")
    unit_clean = unit.astype("string").str.lower()
    grams = pd.Series(pd.NA, index=dosage.index, dtype="Float64")
    is_mg = unit_clean == "mg"
    is_g = unit_clean == "g"

    grams.loc[is_mg] = dosage_float.loc[is_mg] / 1000.0
    grams.loc[is_g] = dosage_float.loc[is_g]
    return grams


def merge_all_data(
    user_health_csv_path: str,
    supplement_usage_csv_path: str,
    experiments_csv_path: str,
    user_profiles_csv_path: str,
) -> pd.DataFrame:
    """Clean and merge the four datasets into the specified output schema.

    Parameters
    ----------
    user_health_csv_path : str
        Path to `user_health_data.csv`.
    supplement_usage_csv_path : str
        Path to `supplement_usage.csv`.
    experiments_csv_path : str
        Path to `experiments.csv`.
    user_profiles_csv_path : str
        Path to `user_profiles.csv`.

    Returns
    -------
    pd.DataFrame
        The merged dataset with the exact required columns and names.
    """

    # Load datasets
    user_health = pd.read_csv(user_health_csv_path)
    supplement_usage = pd.read_csv(supplement_usage_csv_path)
    experiments = pd.read_csv(experiments_csv_path)
    user_profiles = pd.read_csv(user_profiles_csv_path)

    # Normalize date columns
    user_health["date"] = _to_date(user_health.get("date"))
    supplement_usage["date"] = _to_date(supplement_usage.get("date"))

    # Compute age group
    user_profiles["user_age_group"] = _age_to_group(user_profiles.get("age"))

    # Convert dosage to grams
    supplement_usage["dosage_grams"] = _compute_dosage_grams(
        supplement_usage.get("dosage"), supplement_usage.get("dosage_unit")
    )

    # Map experiment_id to experiment_name
    exp_lookup = experiments[["experiment_id", "name"]].rename(
        columns={"name": "experiment_name"}
    )
    supplement_usage = supplement_usage.merge(
        exp_lookup, on="experiment_id", how="left"
    )

    # Ensure supplement_name present for days with usage; otherwise set to 'No intake'
    # We'll prepare a per-user/day skeleton from health data, then left-join usage.
    health_cols_needed = [
        "user_id",
        "date",
        "average_heart_rate",
        "average_glucose",
        "sleep_hours",
        "activity_level",
    ]
    health_df = user_health[health_cols_needed].copy()

    # Join health with possible multiple usage rows (one row per supplement entry)
    merged = health_df.merge(
        supplement_usage,
        on=["user_id", "date"],
        how="left",
        suffixes=("", "_usage"),
    )

    # Add email and age group from profiles
    merged = merged.merge(
        user_profiles[["user_id", "email", "user_age_group"]],
        on="user_id",
        how="left",
    )

    # Supplement name rules
    merged["supplement_name"] = merged["supplement_name"].fillna("No intake")

    # Coerce is_placebo to boolean where possible; keep missing when unknown
    if "is_placebo" in merged.columns:
        # Convert common truthy/falsey strings and ints
        placebos = merged["is_placebo"]
        if placebos.dtype == object:
            lower = placebos.astype("string").str.lower()
            mapped = lower.map({
                "true": True,
                "false": False,
                "1": True,
                "0": False,
                "yes": True,
                "no": False,
            })
            # Use native Python None for missing as per instructions
            merged["is_placebo"] = mapped.where(mapped.notna(), None)
        else:
            b = merged["is_placebo"].astype("boolean")
            merged["is_placebo"] = b.where(b.notna(), None)
    else:
        merged["is_placebo"] = None

    # Ensure experiment_name missing is represented as Python None
    if "experiment_name" in merged.columns:
        merged["experiment_name"] = merged["experiment_name"].where(
            merged["experiment_name"].notna(), None
        )

    # Select and order final columns exactly as required
    final_columns = [
        "user_id",
        "date",
        "email",
        "user_age_group",
        "experiment_name",
        "supplement_name",
        "dosage_grams",
        "is_placebo",
        "average_heart_rate",
        "average_glucose",
        "sleep_hours",
        "activity_level",
    ]
    # Some of these columns originate from supplement_usage; ensure they exist
    for col in ["experiment_name", "dosage_grams"]:
        if col not in merged.columns:
            merged[col] = pd.Series([pd.NA] * len(merged))

    # Enforce no missing emails (drop rows without a user profile email)
    merged = merged[merged["email"].notna()].copy()

    result = merged[final_columns].copy()

    # Sort for determinism
    result = result.sort_values(["user_id", "date", "supplement_name"]).reset_index(
        drop=True
    )
    return result


__all__ = ["merge_all_data"]


