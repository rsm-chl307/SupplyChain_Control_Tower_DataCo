"""Select bounded, traceable business definitions for a Cloud question."""
from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOCS = {
    "kpi": Path("docs/04_KPI_Definition.md"),
    "risk": Path("docs/02_Risk_Dictionary.md"),
    "service": Path("docs/06_Service_Risk_Definition.md"),
    "capability": Path("docs/PRODUCT_CAPABILITY_CATALOG_EN.md"),
}


def _topic(question: str) -> str:
    value = question.lower()
    if any(word in value for word in ("capacity", "bottleneck", "產能", "瓶頸")):
        return "capacity"
    if any(word in value for word in ("service", "服務")):
        return "service"
    if any(word in value for word in ("inventory", "replenish", "庫存", "補貨")):
        return "inventory"
    if any(word in value for word in ("demand", "需求")):
        return "demand"
    if any(word in value for word in ("profit", "獲利")):
        return "profitability"
    return "general"


def _section(content: str, topic: str) -> str:
    lines = content.splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith("## ") and topic in line.lower()]
    if not starts:
        return "\n".join(lines[:70])[:3000]
    start = starts[0]
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return "\n".join(lines[start:end])[:3000]


def select_business_context(question: str, *, root: Path = ROOT) -> list[dict[str, str]]:
    """Return at most two reviewed document excerpts, with full-source hashes."""
    topic = _topic(question)
    names = ("service", "risk") if topic == "service" else (
        ("risk", "kpi") if topic in {"capacity", "inventory", "demand"} else
        ("risk", "capability") if topic == "profitability" else ("capability", "kpi")
    )
    chosen = []
    for name in names:
        relative = DOCS[name]
        path = root / relative
        if (path.is_symlink() or any(parent.is_symlink() for parent in path.parents
                                     if parent == root or parent.is_relative_to(root))
                or not path.is_file() or path.resolve().parent != (root / relative.parent).resolve()
                or path.stat().st_size > 128 * 1024):
            raise ValueError("Reviewed business definition is unavailable")
        raw = path.read_bytes()
        content = raw.decode("utf-8")
        excerpt = _section(content, topic)
        chosen.append({"source": relative.as_posix(), "sha256": hashlib.sha256(raw).hexdigest(),
                       "excerpt": excerpt})
    return chosen
