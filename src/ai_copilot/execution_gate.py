"""Read-only request binding plus explicit local approval/reservation service.

There is intentionally no provider execute method in this service.
"""
from __future__ import annotations

from src.ai_brief.validation import ValidatedBrief
from src.ai_copilot.approval import ApprovalBlocked, ApprovalRecord, ApprovalStore, OwnerVerifier
from src.ai_copilot.ledger import CostPolicy, ExecutionLedger, LedgerEntry
from src.ai_copilot.provider import ProviderRequest, build_request


class LocalExecutionGate:
    def __init__(self, db_path: str, owner_verifier: OwnerVerifier):
        self.ledger = ExecutionLedger(db_path)
        if self.ledger.approvals._verifier != owner_verifier:
            raise ApprovalBlocked("Configured Owner verifier does not match provisioned store")
        self.owner_verifier = owner_verifier

    @staticmethod
    def bind(review: ValidatedBrief, request: ProviderRequest) -> None:
        """Revalidate the live Brief and all digest-bound request content."""
        rebuilt = build_request(review, model_snapshot=request.model_snapshot,
                                max_output_tokens=request.max_output_tokens,
                                timeout_seconds=request.timeout_seconds)
        if rebuilt != request:
            raise ApprovalBlocked("Brief or outbound request changed")

    def approve(self, review: ValidatedBrief, request: ProviderRequest, password: str,
                *, ttl_seconds: int = 300, now: int | None = None,
                policy: CostPolicy | None = None) -> ApprovalRecord:
        self.bind(review, request)
        cost = policy.validate(request) if policy is not None else None
        return self.ledger.approvals.approve(request, password,
                                             ttl_seconds=ttl_seconds, now=now,
                                             approved_cost_usd=cost,
                                             pricing_basis=policy.pricing_basis if policy else None)

    def approval_status(self, review: ValidatedBrief, request: ProviderRequest,
                        reference: str | None, *, now: int | None = None) -> bool:
        self.bind(review, request)
        record = self.ledger.approvals.get(reference) if reference else None
        return record is not None and record.valid_for(request, now=now)

    def reserve(self, review: ValidatedBrief, request: ProviderRequest, reference: str,
                policy: CostPolicy, *, now: int | None = None) -> LedgerEntry:
        self.bind(review, request)
        return self.ledger.reserve(review, request, reference, policy, now=now)
