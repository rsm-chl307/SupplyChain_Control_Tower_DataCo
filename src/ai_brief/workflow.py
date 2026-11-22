"""Local-only integration for an existing authorized synthetic Context.

No CLI, Streamlit hooks, filesystem output, automatic Run preparation or provider.
The caller owns prior fixture preparation and the lifetime of the harness.
"""
from dataclasses import dataclass
from src.synthetic_context import SyntheticHarness,SyntheticContext
from src.ai_brief.adapter import load_context,SourceBlocked,InvestigationSelection
from src.ai_brief.builder import build_draft
from src.ai_brief.contract import BriefRejected
from src.ai_brief.validation import validate_draft,ValidatedBrief
from src.ai_brief.preview import preview
from src.scenario_comparison import ComparisonResult


@dataclass(frozen=True,slots=True)
class BriefOutcome:
    status: str
    message: str
    review: ValidatedBrief | None = None
    markdown: str | None = None


def prepare_brief(harness: SyntheticHarness,context: SyntheticContext | None, *,
                  investigation: InvestigationSelection | None=None,
                  comparison: ComparisonResult | None=None,max_records: int=2) -> BriefOutcome:
    """Consume an already issued context. Never runs Planning or writes files."""
    if context is None:
        return BriefOutcome('UNAVAILABLE','No selected synthetic Run. Obtain an approved harness Context first.')
    try:
        source=load_context(harness,context,investigation=investigation,comparison=comparison)
        draft=build_draft(source,max_records=max_records)
        review=validate_draft(draft)
        return BriefOutcome('VALIDATED','Offline evidence checks passed. No AI interpretation was generated.',review,preview(review))
    except (SourceBlocked,BriefRejected,ValueError,KeyError,TypeError) as exc:
        # Do not echo raw source values, paths or chained exceptions to the user.
        return BriefOutcome('BLOCKED','Evidence, selection, privacy or size validation failed. Recheck the live synthetic Context and bounded selection; do not substitute a historical path.')
