"""Load and validate localized guide sections from Markdown resources."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from dashboard.user_guide.guide_navigation import SECTIONS, SECTION_IDS


_SECTION_MARKER = re.compile(r"^<!-- section:([a-z0-9_]+) -->\s*$", re.MULTILINE)
_HEADING = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_SUBHEADING = re.compile(r"^###\s+(.+?)\s*$", re.MULTILINE)
_LOCALE_FILES = {"en": "en.md", "zh-TW": "zh-TW.md"}
_CONTENT_DIR = Path(__file__).parent / "locales"


class GuideContentError(ValueError):
    """Guide content is missing, incomplete, or inconsistent with navigation."""


@dataclass(frozen=True)
class GuideSubsection:
    title: str
    markdown: str


@dataclass(frozen=True)
class GuideSection:
    section_id: str
    title: str
    introduction: str
    subsections: tuple[GuideSubsection, ...]


def _parse_section(section_id: str, source: str, expected_title: str) -> GuideSection:
    headings = list(_HEADING.finditer(source))
    if len(headings) != 1:
        raise GuideContentError(f"{section_id}: expected exactly one section heading")
    heading = headings[0]
    if heading.group(1).strip() != expected_title:
        raise GuideContentError(f"{section_id}: heading does not match navigation title")
    body = source[heading.end():].strip()
    subheads = list(_SUBHEADING.finditer(body))
    if not subheads:
        raise GuideContentError(f"{section_id}: no subsections were provided")
    introduction = body[:subheads[0].start()].strip()
    if not introduction:
        raise GuideContentError(f"{section_id}: introduction is empty")
    subsections = []
    for index, subhead in enumerate(subheads):
        end = subheads[index + 1].start() if index + 1 < len(subheads) else len(body)
        content = body[subhead.end():end].strip()
        if not content:
            raise GuideContentError(f"{section_id}: subsection {subhead.group(1)!r} is empty")
        subsections.append(GuideSubsection(subhead.group(1).strip(), content))
    return GuideSection(section_id, expected_title, introduction, tuple(subsections))


def load_sections(locale: str) -> tuple[GuideSection, ...]:
    """Load complete sections for ``en`` or ``zh-TW``; never silently fallback."""
    if locale not in _LOCALE_FILES:
        raise GuideContentError(f"Unsupported guide locale: {locale}")
    path = _CONTENT_DIR / _LOCALE_FILES[locale]
    if not path.is_file():
        raise GuideContentError(f"Missing guide translation file: {_LOCALE_FILES[locale]}")
    text = path.read_text(encoding="utf-8")
    markers = list(_SECTION_MARKER.finditer(text))
    ids = [marker.group(1) for marker in markers]
    if len(ids) != len(set(ids)):
        raise GuideContentError(f"Duplicate section IDs in {_LOCALE_FILES[locale]}")
    if tuple(ids) != SECTION_IDS:
        missing = sorted(set(SECTION_IDS) - set(ids))
        extra = sorted(set(ids) - set(SECTION_IDS))
        raise GuideContentError(f"Guide section mismatch; missing={missing}, extra={extra}")
    nav = {item.section_id: item.title(locale) for item in SECTIONS}
    sections = []
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
        sections.append(_parse_section(marker.group(1), text[marker.end():end], nav[marker.group(1)]))
    return tuple(sections)


def section_ids(locale: str) -> tuple[str, ...]:
    """Return section IDs after performing the same completeness checks as UI load."""
    return tuple(section.section_id for section in load_sections(locale))
