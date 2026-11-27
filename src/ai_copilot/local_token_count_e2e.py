"""One-process operator workflow for a local P5 Input Token Count.

This command prepares synthetic trusted context and a Windows handoff, then
waits for the Windows background Worker to return a response. It never opens
credentials or dispatches an API request from the Container.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

from src.ai_brief.adapter import load_context
from src.ai_brief.workflow import prepare_brief
from src.ai_copilot.p5_token_count_orchestrator import (
    P5TokenCountOrchestrator,
    TokenCountWorkflowBlocked,
    TokenCountWorkflowState,
)
from src.ai_copilot.provider import build_request
from src.ai_copilot.quality_evaluation import CORPUS_VERSION
from src.scenario_comparison import (
    ComparisonInput,
    ComparisonScope,
    compare_published_results,
)
from src.synthetic_context import SyntheticHarness
from src.ai_copilot.windows_runner_exchange import RunnerExchangeBlocked


CORPUS_PATH = (Path(__file__).resolve().parents[2]
               / "docs/ai_copilot/p5_offline_evaluation/cases.v2.json")
DEFAULT_CASE = "EV-01"


def _load_case(case_id: str) -> dict:
    try:
        corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
        if corpus.get("dataset_version") != CORPUS_VERSION:
            raise ValueError
        case = next(item for item in corpus["cases"] if item.get("id") == case_id)
        required = {"id", "fixture_id", "scenario", "max_records", "comparison"}
        if (set(case).issuperset(required) is False
                or type(case["max_records"]) is not int
                or type(case["comparison"]) is not bool):
            raise ValueError
        return case
    except (OSError, ValueError, KeyError, TypeError, StopIteration) as exc:
        raise TokenCountWorkflowBlocked(
            "Pinned P5 case definition is unavailable or invalid") from exc


def _make_trusted_request(case: dict):
    """Issue only the pinned synthetic Run and its source-validated Brief."""
    harness = SyntheticHarness(fixture_id=case["fixture_id"])
    try:
        context = harness.issue(case["scenario"])
        comparison = None
        if case["comparison"]:
            bundle = load_context(harness, context)
            manifest, tables = bundle.manifest(), bundle.tables()
            scope = ComparisonScope(
                tuple(manifest["Scope"]["Product_IDs"]),
                tuple(tables["initial_state"].Plant_ID.unique()),
                *manifest["Scope"]["Planning_Horizon"],
                (3,),
            )
            comparison = compare_published_results(
                ComparisonInput(manifest, tables, "Baseline"),
                ComparisonInput(manifest, tables, "Demand_Surge"),
                scope,
            )
        outcome = prepare_brief(
            harness, context, comparison=comparison,
            max_records=case["max_records"])
        if outcome.status != "VALIDATED" or outcome.review is None:
            raise TokenCountWorkflowBlocked(
                "Pinned synthetic Brief did not pass validation")
        request = build_request(
            outcome.review,
            model_snapshot="gpt-6-luna",
            max_output_tokens=25000,
            timeout_seconds=180,
            execution_profile="P5_PAID_ACCEPTANCE",
        )
        return harness, outcome.review, request
    except BaseException:
        harness.close()
        raise


def _print_status(workflow: P5TokenCountOrchestrator) -> int:
    rows = workflow.records()
    if not rows:
        print("P5 token-count workflow: no recorded requests")
        return 0
    print("P5 token-count workflows:")
    for row in rows:
        print(f"{row.case_id}  {row.state.value}  UUID={row.request_id}  Run={row.run_id}")
    if any(not workflow.workflow_resolved(row.request_id) for row in rows):
        print("An unresolved request blocks new preparation. Reconcile its original UUID; do not retry.")
        return 2
    return 0


def _print_reconciliation_evidence(workflow: P5TokenCountOrchestrator,
                                   request_id: str) -> int:
    evidence = workflow.inspect_reconciliation(request_id)
    print("Original failure evidence (read-only):")
    for key in ("request_id", "case_id", "run_id", "state", "request_package_sha256",
                "response_package_sha256", "payload_sha256", "count_projection_sha256",
                "http_status", "openai_request_id", "runner_execution_status",
                "error_type", "error_code", "error_param"):
        print(f"{key}: {evidence[key]}")
    print("No request was sent. Reconciliation does not invoke the Runner or a provider.")
    return 0


def _reconcile_confirmed_failure(workflow: P5TokenCountOrchestrator, args) -> int:
    if not args.request_sha256 or not args.response_sha256 or not args.reason:
        raise TokenCountWorkflowBlocked(
            "--reconcile-failed requires --request-sha256, --response-sha256, and --reason")
    evidence = workflow.inspect_reconciliation(args.reconcile_failed)
    print("Evidence will be re-read and revalidated before the atomic close-out:")
    print(f"Request SHA-256: {evidence['request_package_sha256']}")
    print(f"Response SHA-256: {evidence['response_package_sha256']}")
    import getpass
    owner_password = getpass.getpass("Existing Owner Verifier password: ")
    authorization = workflow.authorize_confirmed_failure(
        args.reconcile_failed,
        expected_request_sha256=args.request_sha256,
        expected_response_sha256=args.response_sha256,
        reason=args.reason,
        owner_password=owner_password,
    )
    confirmation = input(
        f"Type CONFIRM_FAILED {args.reconcile_failed} to close this confirmed HTTP 400: ")
    record = workflow.reconcile_confirmed_failure(
        args.reconcile_failed,
        expected_request_sha256=args.request_sha256,
        expected_response_sha256=args.response_sha256,
        reason=args.reason,
        confirmation=confirmation,
        authorization=authorization,
        owner_password=owner_password,
    )
    print(f"Reconciled: {record.state.value}; UUID={record.request_id}; Case={record.case_id}")
    print("The original Case ID remains permanently reserved. No API or Runner was invoked.")
    return 0


def _mark_unknown_if_active(workflow: P5TokenCountOrchestrator,
                            request_id: str | None) -> None:
    if request_id is None:
        return
    record = workflow.record_for_request(request_id)
    if record is None or record.state not in {
            TokenCountWorkflowState.PREPARED,
            TokenCountWorkflowState.AWAITING_HOST_EXECUTION,
            TokenCountWorkflowState.RESPONSE_PENDING,
    }:
        return
    try:
        workflow.mark_unknown(request_id)
    except TokenCountWorkflowBlocked:
        pass


def run_workflow(case_id: str, windows_exchange: str, *,
                 poll_seconds: float = 3.0, wait_timeout_seconds: float = 1800.0) -> int:
    workflow = P5TokenCountOrchestrator()
    prepared = None
    harness = None
    try:
        # This persistent gate runs before issuing a new Run, so a restarted
        # process cannot obscure an unresolved UUID with fresh synthetic context.
        workflow.assert_new_workflow_allowed(case_id)
        case = _load_case(case_id)
        harness, review, request = _make_trusted_request(case)
        prepared = workflow.prepare(case_id, review, request)
        handoff = workflow.create_windows_handoff(
            prepared.request_id, windows_exchange_path=windows_exchange)
        record = workflow.record_for_request(prepared.request_id)
        print("P5 Input Token Count workflow prepared")
        print(f"State: {record.state.value}")
        print(f"Request UUID: {handoff.request_id}")
        print(f"Operation: {handoff.operation}; model: {handoff.model}")
        print(f"Payload SHA-256: {handoff.payload_sha256}")
        print(f"Windows Worker exchange: {handoff.windows_exchange_path}")
        print("Waiting for the Windows background Worker. P5 will validate and collect the matching response automatically.")

        response_path = workflow.exchange_path / "responses" / f"{prepared.request_id}.json"
        deadline = time.monotonic() + wait_timeout_seconds
        while not response_path.exists():
            if time.monotonic() >= deadline:
                _mark_unknown_if_active(workflow, prepared.request_id)
                print(f"UNKNOWN: no matching host result before timeout; UUID {prepared.request_id} is preserved. Do not resubmit.",
                      file=sys.stderr)
                return 2
            try:
                time.sleep(poll_seconds)
            except KeyboardInterrupt:
                _mark_unknown_if_active(workflow, prepared.request_id)
                print(f"\nUNKNOWN: original UUID {prepared.request_id} is preserved; do not resubmit.",
                      file=sys.stderr)
                return 130

        workflow.mark_response_pending(prepared.request_id)

        record, evidence = workflow.collect_response(
            prepared.request_id, case_id, review, request)
        print("P5 Input Token Count workflow collected successfully")
        print(f"State: {record.state.value}")
        print(f"Case: {evidence.case_id}")
        print(f"Run: {evidence.run_id}")
        print(f"Runner UUID: {evidence.runner_request_id}")
        print(f"OpenAI Request ID: {evidence.request_id}")
        print(f"Model: {evidence.model}")
        print(f"Execution profile: {request.execution_profile}")
        print(f"Exact input_tokens: {evidence.input_tokens}")
        print("Input token cap: 25000")
        print(f"Run manifest SHA-256: {evidence.run_manifest_sha256}")
        print(f"Brief SHA-256: {evidence.brief_digest}")
        print(f"Provider Brief SHA-256: {evidence.provider_brief_digest}")
        print(f"ProviderRequest SHA-256: {evidence.provider_request_digest}")
        print(f"Full payload SHA-256: {evidence.full_payload_sha256}")
        print(f"Count projection SHA-256: {evidence.count_projection_sha256}")
        print(f"Payload bytes: {evidence.payload_bytes}")
        print(f"Response package SHA-256: {evidence.response_package_sha256}")
        print(f"HTTP status: {evidence.http_status}")
        print(f"Returned model ID: {evidence.returned_model_id}")
        print(f"Evidence timestamp UTC: {evidence.timestamp_utc}")
        print(f"Evidence source: {evidence.evidence_source}")
        print("Evidence gate: PASS")
        return 0
    except KeyboardInterrupt:
        request_id = prepared.request_id if prepared is not None else None
        _mark_unknown_if_active(workflow, request_id)
        if request_id:
            print(f"\nUNKNOWN: original UUID {request_id} is preserved; do not resubmit.",
                  file=sys.stderr)
        else:
            print("Stopped before a request UUID was created.", file=sys.stderr)
        return 130
    except (TokenCountWorkflowBlocked, RunnerExchangeBlocked) as exc:
        _mark_unknown_if_active(
            workflow, prepared.request_id if prepared is not None else None)
        print(f"BLOCKED: {exc}", file=sys.stderr)
        if prepared is not None:
            record = workflow.record_for_request(prepared.request_id)
            print(f"Original UUID: {prepared.request_id}; state: {record.state.value if record else 'UNKNOWN'}",
                  file=sys.stderr)
        else:
            for record in workflow.records():
                if record.state != TokenCountWorkflowState.COLLECTED:
                    print(f"Existing UUID: {record.request_id}; state: {record.state.value}; "
                          "reconcile this request; do not prepare another.", file=sys.stderr)
        return 2
    except Exception:
        _mark_unknown_if_active(
            workflow, prepared.request_id if prepared is not None else None)
        print("BLOCKED: unexpected local workflow error; inspect status and reconcile the same UUID.",
              file=sys.stderr)
        if prepared is not None:
            print(f"Original UUID: {prepared.request_id}; no replacement is allowed.",
                  file=sys.stderr)
        return 2
    finally:
        if harness is not None:
            harness.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prepare and collect one P5 synthetic Input Token Count workflow")
    parser.add_argument("--case", default=DEFAULT_CASE,
                        help=f"Pinned P5 case ID (default: {DEFAULT_CASE})")
    parser.add_argument("--windows-exchange", default=P5TokenCountOrchestrator.WINDOWS_EXCHANGE_DEFAULT,
                        help="Absolute Windows exchange directory shown in the handoff")
    parser.add_argument("--poll-seconds", type=float, default=3.0,
                        help="Container-side response polling interval")
    parser.add_argument("--wait-timeout-seconds", type=float, default=1800.0,
                        help="Stop as UNKNOWN if no host result arrives before this timeout")
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--status", action="store_true",
                         help="Show persisted workflow state without creating a Run")
    actions.add_argument("--inspect-reconciliation", metavar="REQUEST_UUID",
                         help="Read and validate original failed HTTP 400 evidence")
    actions.add_argument("--confirm-failed", "--reconcile-failed",
                         dest="reconcile_failed", metavar="REQUEST_UUID",
                         help="Operator-confirm close-out of validated failure evidence")
    parser.add_argument("--request-sha256", help="Expected original request package SHA-256")
    parser.add_argument("--response-sha256", help="Expected original response package SHA-256")
    parser.add_argument("--reason", help="Required owner close-out reason")
    args = parser.parse_args(argv)
    try:
        workflow = P5TokenCountOrchestrator()
        if args.status:
            return _print_status(workflow)
        if args.inspect_reconciliation:
            return _print_reconciliation_evidence(workflow, args.inspect_reconciliation)
        if args.reconcile_failed:
            return _reconcile_confirmed_failure(workflow, args)
        if not 0.2 <= args.poll_seconds <= 60 or not 5 <= args.wait_timeout_seconds <= 86400:
            raise TokenCountWorkflowBlocked("Polling interval or timeout is outside the safe range")
        return run_workflow(args.case, args.windows_exchange,
                            poll_seconds=args.poll_seconds,
                            wait_timeout_seconds=args.wait_timeout_seconds)
    except (TokenCountWorkflowBlocked, RunnerExchangeBlocked) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
