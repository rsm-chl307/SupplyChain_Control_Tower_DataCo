"""Presentation metadata only. Canonical frames, metrics and exports stay intact."""
from __future__ import annotations

from dataclasses import dataclass
import math
from dashboard.i18n import t, dictionary


@dataclass(frozen=True)
class MetricDisplay:
    canonical_id: str
    kind: str = 'quantity'
    precision: int = 2

    @property
    def label(self):
        return t('metric.' + self.canonical_id + '.label', locale='en')

    @property
    def zh_label(self):
        return t('metric.' + self.canonical_id + '.label', locale='zh-TW')

    @property
    def basis(self):
        return t('metric.' + self.canonical_id + '.help', locale='en')

    @property
    def zh_basis(self):
        return t('metric.' + self.canonical_id + '.help', locale='zh-TW')


METRICS = {
    'Production_Coverage_Rate': MetricDisplay('Production_Coverage_Rate', 'ratio', 1),
    'Demand_Fulfillment_Rate': MetricDisplay('Demand_Fulfillment_Rate', 'ratio', 1),
    'Horizon_Service_Level': MetricDisplay('Horizon_Service_Level', 'ratio', 1),
    'Weekly_Service_Level': MetricDisplay('Weekly_Service_Level', 'ratio', 1),
    'Terminal_Backlog': MetricDisplay('Terminal_Backlog', 'quantity', 2),
    'Ending_Backlog': MetricDisplay('Ending_Backlog', 'quantity', 2),
    'Ending_Inventory': MetricDisplay('Ending_Inventory', 'quantity', 2),
    'Lost_Sales': MetricDisplay('Lost_Sales', 'quantity', 2),
    'Lost_Sales_Qty': MetricDisplay('Lost_Sales_Qty', 'quantity', 2),
    'Allocated_Workload': MetricDisplay('Allocated_Workload', 'workload', 2),
    'Unmet_Workload': MetricDisplay('Unmet_Workload', 'workload', 2),
    'Capacity_Utilization': MetricDisplay('Capacity_Utilization', 'ratio', 1),
    'Delta': MetricDisplay('Delta', 'quantity', 2),
    'Required_Production_Qty': MetricDisplay('Required_Production_Qty', 'quantity', 2),
    'Scenario_Qualified_Demand': MetricDisplay('Scenario_Qualified_Demand', 'quantity', 2),
    'Fulfilled_Quantity': MetricDisplay('Fulfilled_Quantity', 'quantity', 2),
    'Current_Unfulfilled_Quantity': MetricDisplay('Current_Unfulfilled_Quantity', 'quantity', 2),
    'Terminal_Opening_Backlog': MetricDisplay('Terminal_Opening_Backlog', 'quantity', 2),
    'Terminal_Horizon_Backlog': MetricDisplay('Terminal_Horizon_Backlog', 'quantity', 2),
    'Service_Level': MetricDisplay('Service_Level', 'ratio', 1),
    'Allocation_Rate': MetricDisplay('Allocation_Rate', 'ratio', 1),
}
FIELDS = {key[6:]: key for key in dictionary('en') if key.startswith('field.')}
STATUS_CODES = ('COMPARABLE', 'DESCRIPTIVE_ONLY', 'BLOCKED', 'POLICY_CONTRAST', 'N/A')
COHORT_CODES = ('ALL', 'SELECTED', 'COMPLEMENT')
STATUS = {code: (t("status."+code+".label", locale="en"), t("status."+code+".label", locale="zh-TW"), t("status."+code+".help", locale="en"), t("status."+code+".help", locale="zh-TW")) for code in STATUS_CODES}
COHORTS = {code: (t("cohort."+code, locale="en"), t("cohort."+code, locale="zh-TW")) for code in COHORT_CODES}

def label(identifier: str, locale: str = 'en') -> str:
    item = METRICS.get(identifier)
    if item:
        return item.zh_label if locale == 'zh-TW' else item.label
    # Catalogs can change during a long-lived Streamlit process. Resolve the
    # display key from the same current catalog used by t(), not an import snapshot.
    key = 'field.' + identifier
    return t(key, locale=locale) if key in dictionary('en') else identifier


def help_text(identifier: str, locale: str = 'en') -> str:
    item = METRICS.get(identifier)
    return (item.zh_basis if locale == 'zh-TW' else item.basis) if item else identifier


def format_value(value, identifier: str, *, delta_unit: str | None = None) -> str:
    """Format an already calculated scalar; never recalculate or mutate it."""
    if value is None:
        return 'N/A'
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(number):
        return 'N/A'
    if identifier == 'Delta' and delta_unit == 'percentage points':
        return f'{number:+.2f} pp'
    item = METRICS.get(identifier)
    if item and item.kind == 'ratio':
        return f'{number:.{item.precision}%}'
    return f'{number:,.2f}'
