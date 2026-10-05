"""Summarization helpers for personalized cohort analysis."""

from __future__ import annotations

import numpy as np
import pandas as pd


def get_threshold_ends(
    thresholds: pd.DataFrame,
    *,
    low_col: str = "low",
    high_col: str = "high",
) -> dict[str, float]:
    """Return the threshold for each end ("low"/"high") in `thresholds`."""
    ends = {}
    for end, col in [("low", low_col), ("high", high_col)]:
        if col in thresholds.columns and pd.notna(thresholds[col].iloc[0]):
            ends[end] = float(thresholds[col].iloc[0])
    if not ends:
        raise ValueError(
            f"Thresholds must have a value in at least one of: {low_col}, {high_col}"
        )
    return ends


def summarize_measurements(
    lab_values: pd.DataFrame,
    thresholds: pd.DataFrame,
    shifts: pd.DataFrame,
    *,
    id_col: str = "id",
    value_col: str = "value",
    low_col: str = "low",
    high_col: str = "high",
    shift_col: str = "shift",
) -> pd.DataFrame:
    """Summarize each measurement as low/high against standard and personalized
    thresholds, and add a confusion matrix label for each measurement, with
    the personalized threshold as ground truth.
    """
    # TODO: later, may extend to allow thresholds to vary by category
    ends = get_threshold_ends(thresholds, low_col=low_col, high_col=high_col)

    classified = lab_values.merge(shifts[[id_col, shift_col]], on=id_col, how="inner")
    value = classified[value_col]
    for end, standard in ends.items():
        pers = standard - classified[shift_col]
        if end == "low":
            std_flag, pers_flag = value <= standard, value <= pers
        else:
            std_flag, pers_flag = value >= standard, value >= pers

        classified[end] = standard
        classified[f"pers_{end}"] = pers
        classified[f"conf_{end}"] = np.select(
            [std_flag & pers_flag, std_flag & ~pers_flag, ~std_flag & pers_flag],
            ["tp", "fp", "fn"],
            default="tn",
        )
    return classified


def summarize_warning_status(
    classified: pd.DataFrame,
    *,
    id_col: str = "id",
    date_col: str = "date",
) -> pd.DataFrame:
    """Summarize all measurements for each person, separately by threshold end."""
    ends = [end for end in ["low", "high"] if f"conf_{end}" in classified.columns]
    dates = pd.to_datetime(classified[date_col])

    status = pd.DataFrame({id_col: classified[id_col].unique()})
    for end in ends:
        conf = classified[f"conf_{end}"]
        first = (
            pd.DataFrame(
                {
                    id_col: classified[id_col],
                    "std": dates.where(conf.isin(["tp", "fp"])),
                    "pers": dates.where(conf.isin(["tp", "fn"])),
                }
            )
            .groupby(id_col, sort=False)
            .min()
            .reindex(status[id_col])
        )
        std, pers = first["std"], first["pers"]
        status[f"{end}_status"] = np.select(
            [
                std.isna() & pers.isna(),
                std.isna(),
                pers.isna(),
                pers < std,
            ],
            ["normal", "pers_only", "standard_only", "pers_early"],
            default="standard_same_or_early",
        )
    return status


def summarize_shifts(
    lab_values: pd.DataFrame,
    thresholds: pd.DataFrame,
    shifts: pd.DataFrame,
    *,
    id_col: str = "id",
    date_col: str = "date",
    value_col: str = "value",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return measurement- and person-level summaries against standard and
    personalized thresholds.
    """
    measurement_summary = summarize_measurements(
        lab_values, thresholds, shifts, id_col=id_col, value_col=value_col
    )
    status = summarize_warning_status(
        measurement_summary, id_col=id_col, date_col=date_col
    )
    person_summary = shifts.merge(status, on=id_col, how="left")
    return person_summary, measurement_summary
