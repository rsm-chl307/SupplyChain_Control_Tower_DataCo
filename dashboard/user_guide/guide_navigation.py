"""Stable user-guide navigation identifiers and translated labels."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GuideNavigationItem:
    section_id: str
    title_en: str
    title_zh_tw: str

    def title(self, locale: str) -> str:
        return self.title_zh_tw if locale == "zh-TW" else self.title_en


SECTIONS = (
    GuideNavigationItem("system_overview", "System Overview", "系統介紹"),
    GuideNavigationItem("dashboard", "Dashboard", "營運總覽"),
    GuideNavigationItem("planning", "Planning", "規劃作業"),
    GuideNavigationItem("wp1", "Operational Risk Investigation", "根因與營運風險分析"),
    GuideNavigationItem("wp2", "Scenario Comparison", "情境比較與決策分析"),
    GuideNavigationItem("data_reports", "Data Management and Reports", "資料與報表"),
    GuideNavigationItem("kpi_glossary", "KPI and Terminology Glossary", "KPI 與專業詞彙"),
    GuideNavigationItem("troubleshooting", "Troubleshooting and FAQ", "常見問題與排除方式"),
)


SECTION_IDS = tuple(item.section_id for item in SECTIONS)


def navigation(locale: str) -> tuple[tuple[str, str], ...]:
    """Return stable IDs paired with labels in the requested supported locale."""
    normalized = locale if locale in {"en", "zh-TW"} else "en"
    return tuple((item.section_id, item.title(normalized)) for item in SECTIONS)
