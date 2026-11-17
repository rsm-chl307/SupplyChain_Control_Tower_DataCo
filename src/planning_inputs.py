"""Small shared input checks for the sequential planning path (no file I/O)."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

WORKLOAD_ALLOCATION_POLICY = "PRIORITY_NET_UNITS_BACKLOG_FIRST_WITHIN_PRODUCT"
ITEM_KEY = ["Plant_ID", "Product Card Id"]
WEEK_KEY = ITEM_KEY + ["Order_Date"]


def require_frame(frame: pd.DataFrame, columns: list[str], key: list[str], name: str) -> None:
    """Reject incomplete schemas, null keys and duplicate business records."""
    missing = set(columns) - set(frame.columns)
    if missing:
        raise ValueError(f"{name}: missing columns {sorted(missing)}")
    if frame[key].isna().any().any() or frame.duplicated(key).any():
        raise ValueError(f"{name}: null or duplicate business key {key}")
    for column in key:
        if frame[column].dtype == object and frame[column].astype(str).str.strip().eq("").any():
            raise ValueError(f"{name}: empty key {column}")


def numeric(frame: pd.DataFrame, columns: list[str], *, positive: bool = False) -> None:
    """Require actual finite numeric values; never repair ambiguous input."""
    if frame.empty:
        return
    for column in columns:
        if not pd.api.types.is_numeric_dtype(frame[column]) or pd.api.types.is_bool_dtype(frame[column]):
            raise ValueError(f"{column}: numeric dtype required")
        values = frame[column].to_numpy(dtype=float)
        if not np.isfinite(values).all() or ((values <= 0) if positive else (values < 0)).any():
            raise ValueError(f"{column}: finite {'positive' if positive else 'nonnegative'} values required")


def weekly_dates(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with normalized Sunday-ending planning dates."""
    result = frame.copy(deep=True)
    dates = pd.to_datetime(result["Order_Date"], errors="coerce")
    if dates.isna().any() or not dates.eq(dates.dt.normalize()).all() or dates.dt.dayofweek.ne(6).any():
        raise ValueError("Order_Date must contain valid normalized Sunday week-ending dates")
    result["Order_Date"] = dates
    return result


def horizon(start: object, end: object) -> pd.DatetimeIndex:
    """Require explicit Sunday bounds and create only the requested week axis."""
    bounds = weekly_dates(pd.DataFrame({"Order_Date": [start, end]}))["Order_Date"]
    if bounds.iloc[0] > bounds.iloc[1]:
        raise ValueError("planning horizon is reversed")
    return pd.date_range(bounds.iloc[0], bounds.iloc[1], freq="W-SUN")


@dataclass
class CanonicalPlanningInputs:
    """Source-independent bundle consumed by the existing planning pipeline.

    Product Card Id is a retained internal compatibility label; adapters accept
    generic string Product_IDs, including SKUs and leading zeros.
    """
    ledger: pd.DataFrame
    weekly: pd.DataFrame
    coverage: pd.DataFrame
    demand: pd.DataFrame
    initial: pd.DataFrame
    receipts: pd.DataFrame
    factors: pd.DataFrame
    capacity: pd.DataFrame
    capacity_calendar: pd.DataFrame
    data_mode: str
    report: dict = field(default_factory=dict)
    scope: dict = field(default_factory=dict)
