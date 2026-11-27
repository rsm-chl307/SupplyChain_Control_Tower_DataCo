"""Versioned local state boundary for the approved P5 eight-case evaluation.

Creating a namespace never changes the historical count workflow or paid Ledger.
The legacy gate must be checked separately before live preparation.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import sqlite3
import uuid

from src.ai_copilot.eight_call_campaign import CASE_IDS, PAID_CORPUS_SHA256
from src.ai_copilot.p5_token_count_orchestrator import P5TokenCountOrchestrator
from src.ai_copilot.windows_runner_exchange import DEFAULT_EXCHANGE_PATH, EXCHANGE_PATH_ENV
from tools.windows_api_runner.api_runner import canonical_json_bytes


NAMESPACE_ID = "p5-eight-scenario-evaluation-v1"
CAMPAIGN_ID = "paid-p5-eight-scenario-evaluation-v1"
SPEC_VERSION = "p5-eight-scenario-evaluation-1"
MODEL_ID = "gpt-6-luna"
REGISTRY_SHA256 = "182d77d84b9ca047a90ea3491bf8a09efd192bc7639d496dbd3fc56c257e67b3"
WINDOWS_EXCHANGE_ROOT = PureWindowsPath(r"C:\SupplyChainCopilot\api_exchange")


class NamespaceBlocked(ValueError):
    pass


def _approved_registry() -> tuple[str, str]:
    path = Path(__file__).resolve().parents[2] / "docs/ai_copilot/p5_offline_evaluation/cases.v2.json"
    raw = path.read_bytes()
    corpus_digest = hashlib.sha256(raw).hexdigest()
    if corpus_digest != PAID_CORPUS_SHA256:
        raise NamespaceBlocked("Pinned evaluation corpus changed")
    corpus = json.loads(raw)
    cases = corpus["cases"]
    if tuple(case["id"] for case in cases) != CASE_IDS:
        raise NamespaceBlocked("Approved case roster changed")
    registry = [{"id": case["id"], "case_version": case["case_version"]} for case in cases]
    registry_digest = hashlib.sha256(canonical_json_bytes(registry)).hexdigest()
    if registry_digest != REGISTRY_SHA256:
        raise NamespaceBlocked("Approved registry identity changed")
    return registry_digest, corpus_digest


@dataclass(frozen=True)
class EvaluationNamespace:
    """Explicit Container/Host mapping; Host deployment is a separate action."""

    legacy_exchange: Path
    container_exchange: Path
    windows_exchange: PureWindowsPath
    namespace_id: str = NAMESPACE_ID
    campaign_id: str = CAMPAIGN_ID

    @classmethod
    def mapping(cls, *, legacy_exchange: str | Path = DEFAULT_EXCHANGE_PATH,
                windows_root: str | PureWindowsPath = WINDOWS_EXCHANGE_ROOT
                ) -> "EvaluationNamespace":
        legacy = Path(legacy_exchange).resolve()
        host_root = PureWindowsPath(windows_root)
        if not host_root.is_absolute() or not host_root.drive:
            raise NamespaceBlocked("Windows exchange root must be absolute")
        return cls(legacy, legacy / "evaluations" / NAMESPACE_ID,
                   host_root / "evaluations" / NAMESPACE_ID)

    def metadata(self) -> dict:
        registry_digest, corpus_digest = _approved_registry()
        return {
            "namespace_id": self.namespace_id,
            "campaign_id": self.campaign_id,
            "registry_sha256": registry_digest,
            "corpus_sha256": corpus_digest,
            "spec_version": SPEC_VERSION,
            "model": MODEL_ID,
            "case_ids": list(CASE_IDS),
            "container_exchange": str(self.container_exchange),
            "windows_exchange": str(self.windows_exchange),
        }

    def create(self) -> None:
        """Provision only the new namespace metadata; never overwrite an old root."""
        if not self.legacy_exchange.is_dir() or self.legacy_exchange.is_symlink():
            raise NamespaceBlocked("Historical exchange root is missing or unsafe")
        wire = canonical_json_bytes(self.metadata())
        parent = self.container_exchange.parent
        parent.mkdir(mode=0o700, exist_ok=True)
        if parent.is_symlink() or self.container_exchange.exists():
            raise NamespaceBlocked("Evaluation namespace already exists or is unsafe")
        self.container_exchange.mkdir(mode=0o700)
        target = self.container_exchange / "namespace.json"
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(wire)
            stream.flush()
            os.fsync(stream.fileno())

    def verify(self) -> None:
        target = self.container_exchange / "namespace.json"
        if target.is_symlink() or not target.is_file() or target.read_bytes() != canonical_json_bytes(self.metadata()):
            raise NamespaceBlocked("Evaluation namespace identity is missing or changed")

    def count_environment(self) -> dict[str, str]:
        self.verify()
        self.assert_legacy_resolved()
        return {EXCHANGE_PATH_ENV: str(self.container_exchange)}

    def assert_legacy_resolved(self) -> None:
        """Read-only global gate; a new namespace never hides an old UNKNOWN."""
        self.verify()
        old_db = self.legacy_exchange / ".p5_token_count_workflow.sqlite3"
        if not old_db.is_file() or old_db.is_symlink():
            raise NamespaceBlocked("Historical workflow state is unavailable")
        workflow = P5TokenCountOrchestrator(exchange_path=self.legacy_exchange,
                                            state_path=old_db)
        try:
            with sqlite3.connect(old_db.as_uri() + "?mode=ro", uri=True) as db:
                db.row_factory = sqlite3.Row
                rows = db.execute("SELECT * FROM token_count_workflow").fetchall()
                if any(not workflow._workflow_is_resolved(db, row) for row in rows):
                    raise NamespaceBlocked("Historical count workflow remains unresolved")
        except sqlite3.Error as exc:
            raise NamespaceBlocked("Historical workflow state cannot be verified") from exc

    def assert_request_id_unshared(self, request_id: str) -> None:
        """Reject a candidate UUID found in historical or sibling namespaces."""
        self.verify()
        try:
            if str(uuid.UUID(request_id)) != request_id:
                raise ValueError
        except (ValueError, TypeError, AttributeError) as exc:
            raise NamespaceBlocked("Request UUID is invalid") from exc
        roots = [self.legacy_exchange]
        parent = self.container_exchange.parent
        roots.extend(path for path in parent.iterdir() if path.is_dir() and path != self.container_exchange)
        for root in roots:
            if any((root / folder / f"{request_id}.json").exists()
                   for folder in ("requests", "responses")):
                raise NamespaceBlocked("Request UUID collides with historical exchange")
            state = root / ".p5_token_count_workflow.sqlite3"
            if state.is_file():
                try:
                    with sqlite3.connect(state.as_uri() + "?mode=ro", uri=True) as db:
                        if db.execute("SELECT 1 FROM token_count_workflow WHERE request_id=?",
                                      (request_id,)).fetchone():
                            raise NamespaceBlocked("Request UUID collides with historical state")
                except sqlite3.Error as exc:
                    raise NamespaceBlocked("Other workflow identity cannot be verified") from exc
