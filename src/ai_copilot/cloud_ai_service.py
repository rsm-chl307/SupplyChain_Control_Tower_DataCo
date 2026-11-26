"""Backend-only safety gate for the existing Streamlit Cloud AI path.

All counters are process-local and deliberately conservative. This module does
not provide a durable global quota, provider-side spend cap, or real dispatch.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from decimal import Decimal, InvalidOperation
from threading import Lock
import hashlib
import logging
import time
from typing import Callable, Mapping

from src.ai_brief.validation import ValidatedBrief
from src.ai_copilot.cloud_access import ai_access_authorized
from src.ai_copilot.cloud_question import (
    CloudQuestionRequest, _issue_service_ticket, cloud_response_arguments, prepare_cloud_question,
)
from src.ai_copilot.cloud_question import CloudProviderFailure
from src.ai_brief.contract import canonical_bytes
from src.ai_copilot.provider_base import ProviderBlocked, ProviderResult
from src.ai_copilot.response_contract import ResponseOutcome, classify_response


_LOG = logging.getLogger(__name__)


MAX_INPUT_BYTES = 30_000  # Full request byte proxy; not an exact provider token count.
MAX_OUTPUT_TOKENS = 500
MAX_OUTPUT_BYTES = 16_000
SESSION_REQUEST_LIMIT = 8
SESSION_INPUT_BYTES_LIMIT = 240_000
PROCESS_DAILY_REQUEST_LIMIT = 30
MIN_REQUEST_INTERVAL_SECONDS = 1.0
WINDOW_SECONDS = 60.0
WINDOW_REQUEST_LIMIT = 3


class CloudAIRejected(RuntimeError):
    """Safe reason code; never includes question, response, password or key."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class PricePolicy:
    model: str
    input_usd_per_million: Decimal
    output_usd_per_million: Decimal
    session_estimated_usd_limit: Decimal

    @classmethod
    def from_settings(cls, settings: Mapping[str, object]) -> "PricePolicy | None":
        names = ("AI_PRICE_MODEL_ID", "AI_PRICE_INPUT_USD_PER_MILLION",
                 "AI_PRICE_OUTPUT_USD_PER_MILLION", "AI_SESSION_ESTIMATED_USD_LIMIT")
        try:
            values = [settings.get(name) for name in names]
        except Exception:
            raise CloudAIRejected("CONFIGURATION_UNAVAILABLE") from None
        if all(value is None for value in values):
            return None
        try:
            if (any(value is None for value in values) or not isinstance(values[0], str)
                    or not values[0] or len(values[0]) > 120):
                raise ValueError
            prices = tuple(Decimal(str(value)) for value in values[1:])
            if any(not value.is_finite() or value <= 0 for value in prices):
                raise ValueError
            return cls(values[0], *prices)
        except (InvalidOperation, ValueError, TypeError):
            raise CloudAIRejected("CONFIGURATION_UNAVAILABLE") from None

    def reserved_cost(self, input_bytes: int, output_tokens: int) -> Decimal:
        return ((self.input_usd_per_million * input_bytes
                 + self.output_usd_per_million * output_tokens) / Decimal(1_000_000))


@dataclass
class _SessionUse:
    timestamps: list[float] = field(default_factory=list)
    digests: set[str] = field(default_factory=set)
    input_bytes: int = 0
    output_reserved: int = 0
    estimated_usd_reserved: Decimal = Decimal(0)


@dataclass(frozen=True)
class CloudAIAnswer:
    outcome: ResponseOutcome
    request_digest: str
    input_bytes: int
    output_token_cap: int
    provider_usage: dict | None
    estimated_usd_reserved: Decimal | None
    model_id: str
    provider_request_id: str | None


class CloudAIService:
    """One backend contract for Fake/Mock now and a separately authorized provider later."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._sessions: dict[str, _SessionUse] = {}
        self._daily_day: int | None = None
        self._daily_requests = 0

    def ask(self, session: Mapping[str, object], settings: Mapping[str, object],
            review: ValidatedBrief, question: str,
            execute: Callable[[CloudQuestionRequest], ProviderResult], *,
            prior_turns: tuple[tuple[str, str], ...] = (),
            now: float | None = None) -> CloudAIAnswer:
        """Authenticate, reserve conservative limits, dispatch once, validate.

        The callable is invoked at most once. A timeout or uncertain result
        consumes the reservation and is never retried here.
        """
        timestamp = time.time() if now is None else now
        if not ai_access_authorized(session, settings, now=timestamp):
            raise CloudAIRejected("ACCESS_DENIED")
        nonce = session.get("_ai_access_nonce")
        if not isinstance(nonce, str):
            raise CloudAIRejected("ACCESS_DENIED")
        if not callable(execute):
            raise CloudAIRejected("PROVIDER_UNAVAILABLE")
        try:
            enabled = settings.get("AI_REAL_PROVIDER_ENABLED", False)
            model = settings.get("AI_MODEL_ID", "offline-fixture-only")
        except Exception:
            raise CloudAIRejected("CONFIGURATION_UNAVAILABLE") from None
        if type(enabled) is not bool or not isinstance(model, str) or not model:
            raise CloudAIRejected("CONFIGURATION_UNAVAILABLE")
        if enabled and model == "offline-fixture-only":
            raise CloudAIRejected("CONFIGURATION_UNAVAILABLE")
        try:
            bound = prepare_cloud_question(review, question, prior_turns=prior_turns,
                                           model_snapshot=model)
            arguments = cloud_response_arguments(bound)
        except (ProviderBlocked, ValueError, TypeError, KeyError, OSError, UnicodeError):
            raise CloudAIRejected("CONTEXT_INVALID") from None
        # Include instructions, output schema and metadata as well as Brief.
        try:
            wire_body = canonical_bytes(arguments)
            input_bytes = len(wire_body)
        except (TypeError, ValueError, UnicodeError):
            raise CloudAIRejected("CONTEXT_INVALID") from None
        if input_bytes > MAX_INPUT_BYTES or bound.provider_request.max_output_tokens > MAX_OUTPUT_TOKENS:
            raise CloudAIRejected("INPUT_LIMIT_EXCEEDED")
        price = PricePolicy.from_settings(settings)
        if enabled and price is None:
            raise CloudAIRejected("CONFIGURATION_UNAVAILABLE")
        if price is not None and price.model != arguments["model"]:
            raise CloudAIRejected("CONFIGURATION_UNAVAILABLE")
        reserve = price.reserved_cost(input_bytes, MAX_OUTPUT_TOKENS) if price else None
        bound = replace(bound, wire_body=wire_body,
                        wire_digest=hashlib.sha256(wire_body).hexdigest())

        with self._lock:
            day = int(timestamp // 86_400)
            if self._daily_day != day:
                self._daily_day, self._daily_requests = day, 0
                self._sessions = {key: value for key, value in self._sessions.items()
                                  if value.timestamps and timestamp - value.timestamps[-1] < 1800}
            if self._daily_requests >= PROCESS_DAILY_REQUEST_LIMIT:
                raise CloudAIRejected("RATE_LIMIT_EXCEEDED")
            usage = self._sessions.setdefault(nonce, _SessionUse())
            recent = [when for when in usage.timestamps if timestamp - when < WINDOW_SECONDS]
            if (bound.request_digest in usage.digests
                    or (usage.timestamps and timestamp - usage.timestamps[-1] < MIN_REQUEST_INTERVAL_SECONDS)):
                raise CloudAIRejected("DUPLICATE_OR_TOO_FAST")
            if len(recent) >= WINDOW_REQUEST_LIMIT or len(usage.timestamps) >= SESSION_REQUEST_LIMIT:
                raise CloudAIRejected("RATE_LIMIT_EXCEEDED")
            if (usage.input_bytes + input_bytes > SESSION_INPUT_BYTES_LIMIT
                    or usage.output_reserved + MAX_OUTPUT_TOKENS > SESSION_REQUEST_LIMIT * MAX_OUTPUT_TOKENS):
                raise CloudAIRejected("USAGE_BUDGET_EXCEEDED")
            if (price is not None and usage.estimated_usd_reserved + reserve
                    > price.session_estimated_usd_limit):
                raise CloudAIRejected("USAGE_BUDGET_EXCEEDED")
            # Reserve before external code. Never refund uncertain executions.
            usage.timestamps.append(timestamp)
            usage.digests.add(bound.request_digest)
            usage.input_bytes += input_bytes
            usage.output_reserved += MAX_OUTPUT_TOKENS
            if reserve is not None:
                usage.estimated_usd_reserved += reserve
            self._daily_requests += 1

        try:
            if enabled:
                bound = replace(bound, service_ticket=_issue_service_ticket(
                    bound.request_digest, bound.wire_digest))
            result = execute(bound)
        except CloudProviderFailure as exc:
            _LOG.warning("Cloud AI provider failure category=%s", exc.code)
            raise CloudAIRejected(exc.code) from None
        except (TimeoutError, ConnectionError):
            _LOG.warning("Cloud AI provider outcome uncertain")
            raise CloudAIRejected("PROVIDER_OUTCOME_UNKNOWN") from None
        except Exception:
            _LOG.warning("Cloud AI provider execution failed")
            raise CloudAIRejected("PROVIDER_ERROR") from None
        if type(result) is not ProviderResult:
            raise CloudAIRejected("INVALID_RESPONSE")
        if result.status == "INCOMPLETE":
            raise CloudAIRejected("OUTPUT_LIMIT_EXCEEDED")
        if result.status == "UNKNOWN_OUTCOME":
            raise CloudAIRejected("PROVIDER_OUTCOME_UNKNOWN")
        if result.status in {"DEFINITIVE_ERROR", "REFUSED"}:
            raise CloudAIRejected("PROVIDER_ERROR")
        if result.status != "SUCCEEDED" or not isinstance(result.raw_response, bytes):
            raise CloudAIRejected("INVALID_RESPONSE")
        if len(result.raw_response) > MAX_OUTPUT_BYTES:
            raise CloudAIRejected("OUTPUT_LIMIT_EXCEEDED")
        provider_usage = result.usage
        if provider_usage is not None:
            if (not isinstance(provider_usage, dict)
                    or type(provider_usage.get("input_tokens")) is not int
                    or type(provider_usage.get("output_tokens")) is not int
                    or provider_usage["input_tokens"] < 0 or provider_usage["output_tokens"] < 0):
                raise CloudAIRejected("INVALID_RESPONSE")
            if (provider_usage["input_tokens"] > MAX_INPUT_BYTES
                    or provider_usage["output_tokens"] > MAX_OUTPUT_TOKENS):
                raise CloudAIRejected("USAGE_BUDGET_EXCEEDED")
            provider_usage = {key: provider_usage[key] for key in ("input_tokens", "output_tokens")}
        try:
            outcome = classify_response(result.raw_response, review, provider_status=result.status)
        except Exception:
            _LOG.warning("Cloud AI response validation failed")
            raise CloudAIRejected("INVALID_RESPONSE") from None
        if outcome.status != "VALIDATED":
            raise CloudAIRejected("INVALID_RESPONSE")
        return CloudAIAnswer(outcome, bound.request_digest, input_bytes,
                             MAX_OUTPUT_TOKENS, provider_usage, reserve,
                             bound.provider_request.model_snapshot, result.provider_request_id)
