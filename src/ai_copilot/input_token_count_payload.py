"""Endpoint-specific canonical payload for Responses input-token counting.

The shared ProviderRequest remains the trusted source of the complete planned
Generation request. This serializer validates that request through the existing
Generation adapter, then explicitly projects only fields supported by the
Responses ``/input_tokens`` endpoint.
"""
from __future__ import annotations

import hashlib

from src.ai_copilot.provider import OpenAIResponsesAdapter, ProviderRequest
from tools.windows_api_runner.api_runner import canonical_json_bytes


# Matches the current OpenAI InputTokenCountParams / endpoint request schema.
# ``text`` includes its supported nested ``format`` and ``verbosity`` fields.
INPUT_TOKEN_COUNT_FIELDS = frozenset({
    "conversation",
    "input",
    "instructions",
    "model",
    "parallel_tool_calls",
    "personality",
    "previous_response_id",
    "reasoning",
    "text",
    "tool_choice",
    "tools",
    "truncation",
})

# Keep the established P5 projection definition stable. It is a named subset
# of the endpoint payload and is independently digest-bound in every package.
COUNT_FIELDS = (
    "model", "input", "instructions", "text", "reasoning",
    "truncation", "tools", "tool_choice",
)


def input_token_count_payload(request: ProviderRequest) -> dict:
    """Validate and serialize the exact endpoint-supported count payload."""
    generation_arguments = OpenAIResponsesAdapter.call_arguments(request)
    payload = {key: generation_arguments[key]
               for key in INPUT_TOKEN_COUNT_FIELDS if key in generation_arguments}
    missing = {"model", "input"} - payload.keys()
    if missing:
        raise ValueError("Input Token Count payload is missing required fields")
    return payload


def input_token_count_wire(request: ProviderRequest) -> tuple[bytes, str, str]:
    """Return canonical payload bytes, full digest, and established projection digest."""
    payload = input_token_count_payload(request)
    missing_projection_fields = set(COUNT_FIELDS) - payload.keys()
    if missing_projection_fields:
        raise ValueError("Input Token Count payload cannot satisfy the P5 count projection")
    full_wire = canonical_json_bytes(payload)
    projection_wire = canonical_json_bytes({field: payload[field] for field in COUNT_FIELDS})
    return (full_wire, hashlib.sha256(full_wire).hexdigest(),
            hashlib.sha256(projection_wire).hexdigest())
