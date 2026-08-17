"""Stage 1 Planning Snapshot contract, mappings, and validation.

The module accepts source DataFrames and returns an in-memory sparse baseline
Planning Snapshot. It intentionally performs no file I/O and no scenario logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import pandas as pd

BUSINESS_KEY = ["Plant_ID", "Product Card Id", "Order_Date"]
PRIORITY_MAP = {"A": 3, "B": 2, "C": 1}
SNAPSHOT_COLUMNS = [
    "Plant_ID",
    "Product Card Id",
    "Product Name",
    "Order_Date",
    "Weekly_Demand",
    "Beginning_Inventory",
    "Weekly_Capacity",
    "Baseline_Available_Capacity",
    "ABC_Class",
    "Planning_Priority",
    "Planning_Key",
]


class PlanningDataValidationError(ValueError):
    """Raised when a hard Planning Snapshot validation rule fails."""


@dataclass
class ValidationReport:
    """Hard failures and non-fatal review warnings."""

    hard_errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.hard_errors

    def raise_if_invalid(self) -> None:
        if self.hard_errors:
            raise PlanningDataValidationError(
                "Planning Snapshot validation failed: "
                + "; ".join(self.hard_errors)
            )


def _missing_columns(frame: pd.DataFrame, required: Sequence[str]) -> list[str]:
    return [column for column in required if column not in frame.columns]


def _check_duplicates(
    report: ValidationReport,
    frame: pd.DataFrame,
    key: Sequence[str],
    label: str,
) -> None:
    count = int(frame.duplicated(list(key)).sum())
    if count:
        report.hard_errors.append(
            f"{label} contains {count} duplicate records at key {list(key)}"
        )


def _check_missing(report: ValidationReport, frame: pd.DataFrame, column: str) -> None:
    count = int(frame[column].isna().sum())
    if count:
        report.hard_errors.append(f"{column} contains {count} missing values")


def _check_nonnegative(
    report: ValidationReport, frame: pd.DataFrame, column: str
) -> None:
    values = pd.to_numeric(frame[column], errors="coerce")
    if int(values.isna().sum()):
        report.hard_errors.append(f"{column} contains non-numeric values")
    if int((values < 0).sum()):
        report.hard_errors.append(f"{column} contains negative values")


def validate_planning_snapshot(
    snapshot: pd.DataFrame,
    *,
    expected_sparse: bool = True,
) -> ValidationReport:
    """Validate a canonical baseline snapshot without repairing invalid data."""

    report = ValidationReport()
    required = [
        "Plant_ID",
        "Product Card Id",
        "Order_Date",
        "Weekly_Demand",
        "Beginning_Inventory",
        "Weekly_Capacity",
        "Baseline_Available_Capacity",
        "ABC_Class",
        "Planning_Priority",
    ]
    missing = _missing_columns(snapshot, required)
    if missing:
        report.hard_errors.append(f"snapshot missing columns: {missing}")
        return report

    _check_duplicates(report, snapshot, BUSINESS_KEY, "snapshot")
    _check_missing(report, snapshot, "Plant_ID")
    _check_missing(report, snapshot, "Product Card Id")
    _check_missing(report, snapshot, "Beginning_Inventory")

    dates = pd.to_datetime(snapshot["Order_Date"], errors="coerce")
    if int(dates.isna().sum()):
        report.hard_errors.append("Order_Date contains invalid or missing dates")

    for column in ("Weekly_Demand", "Weekly_Capacity", "Beginning_Inventory"):
        _check_nonnegative(report, snapshot, column)

    if int(snapshot["Weekly_Capacity"].isna().sum()):
        report.hard_errors.append("Weekly_Capacity is missing")

    missing_abc = int(snapshot["ABC_Class"].isna().sum())
    if missing_abc:
        report.warnings.append(
            f"ABC_Class is missing for {missing_abc} records; priority is unresolved"
        )
    invalid_abc = sorted(
        set(snapshot["ABC_Class"].dropna().astype(str)) - set(PRIORITY_MAP)
    )
    if invalid_abc:
        report.hard_errors.append(f"ABC_Class contains unexpected values: {invalid_abc}")

    if expected_sparse:
        observed = snapshot[["Product Card Id", "Order_Date"]].drop_duplicates().shape[0]
        report.warnings.append(
            "Sparse Product × Week observations are retained by design "
            f"({observed} observed combinations)"
        )

    return report


def _validate_source_frames(
    demand: pd.DataFrame,
    capacity: pd.DataFrame,
    inventory: pd.DataFrame,
    abc: pd.DataFrame,
    product_plant_mapping: pd.DataFrame,
) -> ValidationReport:
    """Validate source schemas and relationships before joining them."""

    report = ValidationReport()
    required_by_source = {
        "demand": (demand, BUSINESS_KEY + ["Product Name", "Weekly_Demand"]),
        "capacity": (
            capacity,
            ["Plant_ID", "Order_Date", "Weekly_Capacity", "Available_Capacity"],
        ),
        "inventory": (inventory, BUSINESS_KEY + ["Beginning_Inventory"]),
        "abc": (abc, ["Product Card Id", "ABC_Class"]),
        "product-plant mapping": (
            product_plant_mapping,
            ["Product Card Id", "Plant_ID"],
        ),
    }
    for label, (frame, required) in required_by_source.items():
        missing = _missing_columns(frame, required)
        if missing:
            report.hard_errors.append(f"{label} missing columns: {missing}")
    if report.hard_errors:
        return report

    _check_duplicates(report, demand, BUSINESS_KEY, "demand")
    _check_duplicates(report, inventory, BUSINESS_KEY, "inventory")
    _check_duplicates(report, capacity, ["Plant_ID", "Order_Date"], "capacity")
    _check_duplicates(report, abc, ["Product Card Id"], "abc")
    _check_duplicates(
        report,
        product_plant_mapping,
        ["Product Card Id"],
        "product-plant mapping",
    )
    _check_missing(report, demand, "Plant_ID")
    _check_missing(report, demand, "Product Card Id")
    _check_nonnegative(report, demand, "Weekly_Demand")
    _check_nonnegative(report, capacity, "Weekly_Capacity")

    demand_dates = pd.to_datetime(demand["Order_Date"], errors="coerce")
    capacity_dates = pd.to_datetime(capacity["Order_Date"], errors="coerce")
    if int(demand_dates.isna().sum()) or int(capacity_dates.isna().sum()):
        report.hard_errors.append("Demand or capacity contains invalid dates")
    if int(capacity["Weekly_Capacity"].isna().sum()):
        report.hard_errors.append("Capacity is missing for one or more Plant × Week records")

    mapping = product_plant_mapping[["Product Card Id", "Plant_ID"]]
    mapped = demand[["Product Card Id", "Plant_ID"]].merge(
        mapping,
        on="Product Card Id",
        how="left",
        suffixes=("_demand", "_mapping"),
    )
    if int(mapped["Plant_ID_mapping"].isna().sum()):
        report.hard_errors.append("Demand product is missing product-plant mapping")
    mismatch = mapped[
        mapped["Plant_ID_mapping"].notna()
        & (mapped["Plant_ID_demand"] != mapped["Plant_ID_mapping"])
    ]
    if len(mismatch):
        report.hard_errors.append("Demand Plant_ID conflicts with product-plant mapping")

    return report


def build_planning_snapshot(
    demand: pd.DataFrame,
    capacity: pd.DataFrame,
    inventory: pd.DataFrame,
    abc: pd.DataFrame,
    product_plant_mapping: pd.DataFrame,
) -> pd.DataFrame:
    """Build the sparse baseline snapshot from existing source DataFrames.

    The demand row set is preserved. Joins are key-based and no dense grid,
    horizon filter, scenario field, or file output is created.
    """

    source_report = _validate_source_frames(
        demand, capacity, inventory, abc, product_plant_mapping
    )
    source_report.raise_if_invalid()

    demand_base = demand.copy()
    capacity_base = capacity.copy()
    inventory_base = inventory.copy()
    for frame in (demand_base, capacity_base, inventory_base):
        frame["Order_Date"] = pd.to_datetime(frame["Order_Date"], errors="coerce")

    snapshot = demand_base[
        BUSINESS_KEY + ["Product Name", "Weekly_Demand"]
    ].merge(
        inventory_base[BUSINESS_KEY + ["Beginning_Inventory"]],
        on=BUSINESS_KEY,
        how="left",
        validate="one_to_one",
    ).merge(
        capacity_base[
            ["Plant_ID", "Order_Date", "Weekly_Capacity", "Available_Capacity"]
        ],
        on=["Plant_ID", "Order_Date"],
        how="left",
        validate="many_to_one",
    ).merge(
        abc[["Product Card Id", "ABC_Class"]],
        on="Product Card Id",
        how="left",
        validate="many_to_one",
    )
    snapshot["Planning_Priority"] = snapshot["ABC_Class"].map(PRIORITY_MAP)
    snapshot["Planning_Key"] = (
        snapshot["Plant_ID"].astype(str)
        + "|"
        + snapshot["Product Card Id"].astype(str)
        + "|"
        + snapshot["Order_Date"].dt.strftime("%Y-%m-%d")
    )
    snapshot = snapshot.rename(
        columns={"Available_Capacity": "Baseline_Available_Capacity"}
    )
    final = snapshot[SNAPSHOT_COLUMNS]

    final_report = validate_planning_snapshot(final)
    final_report.raise_if_invalid()
    return final
