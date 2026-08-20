"""Generate deterministic Stage 3 planning scenarios in memory.

The generator consumes a validated Stage 2 baseline Planning Snapshot.  It
does not read or write files, allocate capacity, or calculate performance
metrics.  File I/O belongs to the surrounding pipeline or run script.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

import pandas as pd


PLANNING_SNAPSHOT_COLUMNS = [
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
SCENARIO_COLUMNS = PLANNING_SNAPSHOT_COLUMNS + [
    "Scenario",
    "Scenario_Demand",
    "Scenario_Capacity",
]
FORBIDDEN_SCENARIO_FIELDS = {
    "Allocated",
    "Allocated_Quantity",
    "Net_Demand",
    "Backlog",
    "Service_Level",
    "Utilization",
    "Allocation_Order",
    "Recommendation",
}


class ScenarioValidationError(ValueError):
    """Raised when the input, parameters, or generated scenario is invalid."""


def _finite_percentage(value: object, name: str, *, maximum: float | None = None) -> float:
    if isinstance(value, bool):
        raise ScenarioValidationError(f"{name} must be a finite numeric percentage")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ScenarioValidationError(f"{name} must be a finite numeric percentage") from exc
    if not math.isfinite(number):
        raise ScenarioValidationError(f"{name} must be finite")
    if number < 0 or (maximum is not None and number > maximum):
        limit = f" and <= {maximum:g}" if maximum is not None else ""
        raise ScenarioValidationError(f"{name} must be >= 0{limit}")
    return number


def _parse_week(value: object, name: str) -> pd.Timestamp:
    if value is None or isinstance(value, bool):
        raise ScenarioValidationError(f"{name} must be a valid date")
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        raise ScenarioValidationError(f"{name} must be a valid date")
    return pd.Timestamp(parsed).normalize()


def _percent_label(value: float) -> str:
    return (str(int(value)) if value.is_integer() else format(value, "g")) + "pct"


def _validate_input(snapshot: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(snapshot, pd.DataFrame):
        raise ScenarioValidationError("planning_snapshot must be a pandas DataFrame")
    if list(snapshot.columns) != PLANNING_SNAPSHOT_COLUMNS:
        raise ScenarioValidationError(
            "planning_snapshot must contain exactly the Stage 2 schema in approved order"
        )
    if snapshot["Planning_Key"].duplicated().any():
        raise ScenarioValidationError("Planning_Key must be unique in the input snapshot")
    dates = pd.to_datetime(snapshot["Order_Date"], errors="coerce")
    if dates.isna().any():
        raise ScenarioValidationError("Order_Date contains invalid or missing dates")
    for column in ("Weekly_Demand", "Weekly_Capacity", "Beginning_Inventory"):
        values = pd.to_numeric(snapshot[column], errors="coerce")
        if values.isna().any() or (values < 0).any():
            raise ScenarioValidationError(f"{column} must be numeric and non-negative")
    if snapshot["Plant_ID"].isna().any() or snapshot["Product Card Id"].isna().any():
        raise ScenarioValidationError("Plant_ID and Product Card Id are required")
    if snapshot["Weekly_Capacity"].isna().any():
        raise ScenarioValidationError("Weekly_Capacity is required")
    if any(field in snapshot.columns for field in FORBIDDEN_SCENARIO_FIELDS):
        raise ScenarioValidationError("planning_snapshot contains allocation/performance fields")
    result = snapshot.copy(deep=True)
    result["Order_Date"] = dates.dt.normalize()
    return result


def _normalise_parameters(
    scenario_parameters: Sequence[Mapping[str, object]],
    snapshot: pd.DataFrame,
) -> list[dict[str, object]]:
    if isinstance(scenario_parameters, (str, bytes)) or not isinstance(scenario_parameters, Sequence):
        raise ScenarioValidationError("scenario_parameters must be a sequence of mappings")
    if not scenario_parameters:
        raise ScenarioValidationError("at least one scenario must be provided")
    plants = set(snapshot["Plant_ID"].astype(str))
    available_start = snapshot["Order_Date"].min()
    available_end = snapshot["Order_Date"].max()
    normalised: list[dict[str, object]] = []
    identifiers: set[str] = set()
    for raw in scenario_parameters:
        if not isinstance(raw, Mapping):
            raise ScenarioValidationError("each scenario parameter must be a mapping")
        name = raw.get("scenario")
        if not isinstance(name, str) or not name:
            raise ScenarioValidationError("scenario name is required")
        if name.lower().replace(" ", "_") in {"priority_shift", "priorityshift"} or name.startswith("Priority_Shift"):
            raise ScenarioValidationError("Priority Shift is not part of Stage 3 MVP")
        if name == "Baseline":
            if len(raw) != 1:
                raise ScenarioValidationError("Baseline does not accept scenario parameters")
            identifier = "Baseline"
            item = {"scenario": identifier, "kind": "baseline"}
        elif name in {"Demand_Surge", "Demand_Surge_10pct"}:
            if "demand_increase_pct" not in raw:
                raise ScenarioValidationError("Demand Surge requires demand_increase_pct")
            pct = _finite_percentage(raw["demand_increase_pct"], "demand_increase_pct")
            identifier = f"Demand_Surge_{_percent_label(pct)}"
            item = {"scenario": identifier, "kind": "demand_surge", "pct": pct}
        elif name in {"Capacity_Disruption", "Capacity_Disruption_P1_20pct"}:
            required = {"capacity_reduction_pct", "plant_ids"}
            missing = required - raw.keys()
            if missing:
                raise ScenarioValidationError(f"Capacity Disruption missing parameters: {sorted(missing)}")
            pct = _finite_percentage(raw["capacity_reduction_pct"], "capacity_reduction_pct", maximum=100)
            plant_ids = raw["plant_ids"]
            if isinstance(plant_ids, (str, bytes)) or not isinstance(plant_ids, Sequence) or not plant_ids:
                raise ScenarioValidationError("plant_ids must be a non-empty sequence")
            plant_ids = [str(plant) for plant in plant_ids]
            unknown = sorted(set(plant_ids) - plants)
            if unknown:
                raise ScenarioValidationError(f"unknown plant_ids: {unknown}")
            has_start = "week_start" in raw and raw["week_start"] is not None
            has_end = "week_end" in raw and raw["week_end"] is not None
            if has_start != has_end:
                raise ScenarioValidationError("week_start and week_end must be provided together")
            start = end = None
            if has_start:
                start = _parse_week(raw["week_start"], "week_start")
                end = _parse_week(raw["week_end"], "week_end")
                if start > end:
                    raise ScenarioValidationError("week_start must be <= week_end")
                if start < available_start or end > available_end:
                    raise ScenarioValidationError(
                        "disruption week bounds must fall within input range "
                        f"{available_start.date()} through {available_end.date()}"
                    )
            suffix = "_" + "_".join(sorted(plant_ids)) + f"_{_percent_label(pct)}"
            if start is not None:
                suffix += f"_{start:%Y%m%d}_{end:%Y%m%d}"
            identifier = "Capacity_Disruption" + suffix
            item = {"scenario": identifier, "kind": "capacity_disruption", "pct": pct, "plants": set(plant_ids), "start": start, "end": end}
        else:
            raise ScenarioValidationError(f"unsupported scenario: {name}")
        if identifier in identifiers:
            raise ScenarioValidationError(f"duplicate scenario identifier: {identifier}")
        identifiers.add(identifier)
        normalised.append(item)
    return normalised


def _validate_output(
    output: pd.DataFrame,
    baseline: pd.DataFrame,
    parameters: Sequence[Mapping[str, object]],
) -> None:
    scenario_names = [item["scenario"] for item in parameters]
    if list(output.columns) != SCENARIO_COLUMNS:
        raise ScenarioValidationError("generated output does not match the approved scenario schema")
    if len(output) != len(baseline) * len(scenario_names):
        raise ScenarioValidationError("each scenario must preserve the complete input row set")
    if output.duplicated(["Scenario", "Planning_Key"]).any():
        raise ScenarioValidationError("Scenario + Planning_Key must be unique")
    if set(output["Scenario"]) != set(scenario_names):
        raise ScenarioValidationError("generated scenarios do not match requested scenarios")
    for column in ("Scenario_Demand", "Scenario_Capacity"):
        values = pd.to_numeric(output[column], errors="coerce")
        if values.isna().any() or (values < 0).any():
            raise ScenarioValidationError(f"{column} must be numeric and non-negative")

    base = baseline.set_index("Planning_Key")
    for item in parameters:
        rows = output[output["Scenario"] == item["scenario"]].set_index("Planning_Key")
        if set(rows.index) != set(base.index):
            raise ScenarioValidationError("scenario rows must preserve the baseline Planning_Key set")
        base_aligned = base.reindex(rows.index)
        for column in PLANNING_SNAPSHOT_COLUMNS[:-1]:
            if not rows[column].reset_index(drop=True).equals(base_aligned[column].reset_index(drop=True)):
                raise ScenarioValidationError(f"baseline field changed in scenario output: {column}")
        expected_demand = base_aligned["Weekly_Demand"]
        expected_capacity = base_aligned["Weekly_Capacity"].astype(float).copy()
        if item["kind"] == "demand_surge":
            expected_demand = expected_demand * (1 + item["pct"] / 100)
        elif item["kind"] == "capacity_disruption":
            mask = base_aligned["Plant_ID"].astype(str).isin(item["plants"])
            if item["start"] is not None:
                mask &= base_aligned["Order_Date"].between(item["start"], item["end"], inclusive="both")
            expected_capacity.loc[mask] = expected_capacity.loc[mask] * (1 - item["pct"] / 100)
        if not (rows["Scenario_Demand"].to_numpy() == expected_demand.to_numpy()).all():
            raise ScenarioValidationError(f"invalid Scenario_Demand values for {item['scenario']}")
        if not (rows["Scenario_Capacity"].to_numpy() == expected_capacity.to_numpy()).all():
            raise ScenarioValidationError(f"invalid Scenario_Capacity values for {item['scenario']}")


def generate_scenarios(
    planning_snapshot: pd.DataFrame,
    scenario_parameters: Sequence[Mapping[str, object]],
) -> pd.DataFrame:
    """Generate baseline, demand-surge, and capacity-disruption scenarios.

    ``scenario_parameters`` is a sequence of mappings. Each mapping has a
    ``scenario`` name and the required explicit parameters; no defaults are
    applied by this function. The input snapshot is never mutated.
    """
    baseline = _validate_input(planning_snapshot)
    parameters = _normalise_parameters(scenario_parameters, baseline)
    frames: list[pd.DataFrame] = []
    for item in parameters:
        frame = baseline.copy(deep=True)
        frame["Scenario"] = item["scenario"]
        frame["Scenario_Demand"] = frame["Weekly_Demand"]
        frame["Scenario_Capacity"] = frame["Weekly_Capacity"]
        if item["kind"] == "demand_surge":
            frame["Scenario_Demand"] = frame["Weekly_Demand"] * (1 + item["pct"] / 100)
        elif item["kind"] == "capacity_disruption":
            mask = frame["Plant_ID"].astype(str).isin(item["plants"])
            if item["start"] is not None:
                mask &= frame["Order_Date"].between(item["start"], item["end"], inclusive="both")
            frame.loc[mask, "Scenario_Capacity"] = frame.loc[mask, "Weekly_Capacity"] * (1 - item["pct"] / 100)
        frames.append(frame[SCENARIO_COLUMNS])
    output = pd.concat(frames, ignore_index=True)
    output = output.sort_values(
        ["Scenario", "Plant_ID", "Product Card Id", "Order_Date"],
        kind="mergesort",
    ).reset_index(drop=True)
    _validate_output(output, baseline, parameters)
    return output

