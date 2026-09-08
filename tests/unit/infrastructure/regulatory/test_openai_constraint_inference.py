"""Offline unit tests for the OpenAI regulatory-constraint inference adapter.

No live OpenAI network call, API key, or real ``AsyncOpenAI`` client is used.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from datetime import date
from types import SimpleNamespace
from typing import Any, cast

import pytest
from openai import APIConnectionError, OpenAIError

from energy_trading.application.errors import DependencyUnavailableError
from energy_trading.application.ports.document_extraction import ExtractedDocumentChunk
from energy_trading.application.ports.regulatory_constraint_inference import (
    RegulatoryConstraintInferencePort,
)
from energy_trading.domain.models.regulatory import RegulatoryConstraint
from energy_trading.infrastructure.regulatory.openai_constraint_inference import (
    _INFERENCE_INSTRUCTIONS,
    OpenAIRegulatoryConstraintInferenceAdapter,
    _ProviderConstraintCandidate,
    _ProviderInferenceEnvelope,
)

_MODEL = "gpt-4.1-mini"
_UNAVAILABLE_MESSAGE = "Regulatory constraint inference is unavailable."
_PROVIDER_LEAK = "sk-test-leak Confidential synthetic license clause."
_CHUNK_TEXT_SENTINEL = "Synthetic licensed upper bound SENTINEL_CHUNK_BODY remains verbatim."
_CHUNK_ID = "chunk-alpha"
_DOCUMENT_ID = "doc-synthetic-1"


@dataclass
class _FakeResponses:
    """Test-only Responses resource. Not a production OpenAI client."""

    parse_calls: list[dict[str, object]] = field(default_factory=list)
    error: BaseException | None = None
    response: object | None = None

    async def parse(self, **kwargs: object) -> object:
        self.parse_calls.append(kwargs)
        if self.error is not None:
            raise self.error
        assert self.response is not None
        return self.response


@dataclass
class _RecordingEndpoint:
    create_calls: list[dict[str, object]] = field(default_factory=list)
    parse_calls: list[dict[str, object]] = field(default_factory=list)

    async def create(self, **kwargs: object) -> object:
        self.create_calls.append(kwargs)
        raise AssertionError("non-responses OpenAI resource must not be called")

    async def parse(self, **kwargs: object) -> object:
        self.parse_calls.append(kwargs)
        raise AssertionError("non-responses OpenAI resource must not be called")


@dataclass
class _FakeOpenAIClient:
    """Structural fake for the injected ``AsyncOpenAI`` Responses surface."""

    responses: _FakeResponses = field(default_factory=_FakeResponses)
    embeddings: _RecordingEndpoint = field(default_factory=_RecordingEndpoint)
    chat: _RecordingEndpoint = field(default_factory=_RecordingEndpoint)
    completions: _RecordingEndpoint = field(default_factory=_RecordingEndpoint)


def _chunk(**overrides: object) -> ExtractedDocumentChunk:
    values: dict[str, object] = {
        "document_id": _DOCUMENT_ID,
        "chunk_id": _CHUNK_ID,
        "ordinal": 0,
        "text": _CHUNK_TEXT_SENTINEL,
        "page_number": 1,
    }
    values.update(overrides)
    return ExtractedDocumentChunk(**values)  # type: ignore[arg-type]


def _candidate(**overrides: object) -> _ProviderConstraintCandidate:
    values: dict[str, object] = {
        "constraint_id": "synthetic-limit-1",
        "constraint_type": "capacity_limit",
        "description": "Synthetic licensed upper bound from supplied chunk.",
        "effective_from": date(2026, 6, 1),
        "evidence_chunk_ids": (_CHUNK_ID,),
        "maximum_value": 12.5,
        "unit": "MW",
        "source_document_id": _DOCUMENT_ID,
    }
    values.update(overrides)
    return _ProviderConstraintCandidate.model_validate(values)


def _envelope(
    constraints: tuple[_ProviderConstraintCandidate, ...] = (),
) -> _ProviderInferenceEnvelope:
    return _ProviderInferenceEnvelope(constraints=constraints)


def _parsed_response(
    envelope: _ProviderInferenceEnvelope,
    *,
    output: object | None = None,
) -> object:
    namespace = SimpleNamespace(output_parsed=envelope)
    if output is not None:
        namespace.output = output
    return namespace


def _adapter(
    client: _FakeOpenAIClient,
    *,
    model: str = _MODEL,
) -> OpenAIRegulatoryConstraintInferenceAdapter:
    return OpenAIRegulatoryConstraintInferenceAdapter(
        client=cast(Any, client),
        model=model,
    )


def test_adapter_does_not_inherit_the_application_port() -> None:
    assert (
        RegulatoryConstraintInferencePort not in OpenAIRegulatoryConstraintInferenceAdapter.__mro__
    )


def test_adapter_structurally_satisfies_inference_port() -> None:
    adapter = _adapter(_FakeOpenAIClient())
    port: RegulatoryConstraintInferencePort = adapter
    assert inspect.iscoroutinefunction(port.infer)
    signature = inspect.signature(OpenAIRegulatoryConstraintInferenceAdapter.infer)
    assert list(signature.parameters) == ["self", "chunks"]
    assert signature.parameters["chunks"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.return_annotation in {
        tuple[RegulatoryConstraint, ...],
        "tuple[RegulatoryConstraint, ...]",
    }


def test_constructor_is_keyword_only_client_and_model() -> None:
    signature = inspect.signature(OpenAIRegulatoryConstraintInferenceAdapter.__init__)
    assert tuple(signature.parameters) == ("self", "client", "model")
    assert signature.parameters["client"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["model"].kind is inspect.Parameter.KEYWORD_ONLY


def test_constructor_does_not_require_an_api_key() -> None:
    client = _FakeOpenAIClient()
    adapter = _adapter(client)
    assert adapter._client is client
    assert adapter._model is _MODEL
    assert not hasattr(adapter, "api_key")


async def test_empty_chunks_return_empty_tuple_without_provider_call() -> None:
    client = _FakeOpenAIClient()
    client.responses.response = _parsed_response(_envelope((_candidate(),)))
    adapter = _adapter(client)

    result = await adapter.infer(chunks=())

    assert result == ()
    assert client.responses.parse_calls == []
    assert client.embeddings.parse_calls == []
    assert client.embeddings.create_calls == []
    assert client.chat.create_calls == []
    assert client.completions.create_calls == []


async def test_non_empty_input_invokes_structured_output_once() -> None:
    client = _FakeOpenAIClient()
    client.responses.response = _parsed_response(_envelope((_candidate(),)))
    adapter = _adapter(client)
    chunks = (_chunk(),)

    result = await adapter.infer(chunks=chunks)

    assert len(client.responses.parse_calls) == 1
    call = client.responses.parse_calls[0]
    assert call["model"] is _MODEL
    assert call["instructions"] is _INFERENCE_INSTRUCTIONS
    assert call["text_format"] is _ProviderInferenceEnvelope
    assert call["input"] == (
        f"chunk_id: {_CHUNK_ID}\n"
        f"document_id: {_DOCUMENT_ID}\n"
        f"ordinal: 0\n"
        f"text:\n{_CHUNK_TEXT_SENTINEL}"
    )
    assert _CHUNK_TEXT_SENTINEL in str(call["input"])
    assert client.embeddings.parse_calls == []
    assert client.embeddings.create_calls == []
    assert client.chat.create_calls == []
    assert client.completions.create_calls == []
    assert isinstance(result, tuple)
    assert len(result) == 1
    assert type(result[0]) is RegulatoryConstraint
    assert type(result[0]).__module__ == RegulatoryConstraint.__module__


async def test_model_string_is_forwarded_unchanged() -> None:
    client = _FakeOpenAIClient()
    client.responses.response = _parsed_response(_envelope((_candidate(),)))
    model = "  custom-inference-model  "
    adapter = _adapter(client, model=model)

    await adapter.infer(chunks=(_chunk(),))

    assert client.responses.parse_calls[0]["model"] is model


async def test_chunk_text_and_identities_are_deterministic_and_unmutated() -> None:
    client = _FakeOpenAIClient()
    first = _chunk()
    second = _chunk(chunk_id="chunk-beta", ordinal=1, text="Second synthetic clause body.")
    client.responses.response = _parsed_response(
        _envelope(
            (
                _candidate(),
                _candidate(
                    constraint_id="synthetic-limit-2",
                    evidence_chunk_ids=("chunk-beta",),
                ),
            )
        )
    )
    adapter = _adapter(client)

    await adapter.infer(chunks=(first, second))

    provider_input = client.responses.parse_calls[0]["input"]
    assert isinstance(provider_input, str)
    assert provider_input.index(_CHUNK_ID) < provider_input.index("chunk-beta")
    assert first.text in provider_input
    assert second.text in provider_input
    assert provider_input.count(first.text) == 1
    rebuilt_first = (
        f"chunk_id: {first.chunk_id}\n"
        f"document_id: {first.document_id}\n"
        f"ordinal: {first.ordinal}\n"
        f"text:\n{first.text}"
    )
    rebuilt_second = (
        f"chunk_id: {second.chunk_id}\n"
        f"document_id: {second.document_id}\n"
        f"ordinal: {second.ordinal}\n"
        f"text:\n{second.text}"
    )
    assert provider_input == f"{rebuilt_first}\n\n{rebuilt_second}"
    assert first.text in rebuilt_first
    assert second.text in rebuilt_second


async def test_one_valid_candidate_becomes_one_canonical_constraint() -> None:
    client = _FakeOpenAIClient()
    candidate = _candidate()
    client.responses.response = _parsed_response(_envelope((candidate,)))
    adapter = _adapter(client)

    result = await adapter.infer(chunks=(_chunk(),))

    assert len(result) == 1
    constraint = result[0]
    assert isinstance(constraint, RegulatoryConstraint)
    assert constraint.constraint_id == "synthetic-limit-1"
    assert constraint.constraint_type == "capacity_limit"
    assert constraint.description == "Synthetic licensed upper bound from supplied chunk."
    assert constraint.effective_from == date(2026, 6, 1)
    assert constraint.effective_to is None
    assert constraint.minimum_value is None
    assert constraint.maximum_value == 12.5
    assert constraint.unit == "MW"
    assert constraint.currency is None
    assert constraint.source_document_id == _DOCUMENT_ID
    assert not hasattr(constraint, "evidence_chunk_ids")


async def test_multiple_valid_candidates_preserve_order() -> None:
    client = _FakeOpenAIClient()
    first = _candidate(constraint_id="synthetic-limit-1")
    second = _candidate(
        constraint_id="synthetic-limit-2",
        constraint_type="license_window",
        description="Synthetic effective window from supplied chunk.",
        maximum_value=None,
        unit=None,
    )
    client.responses.response = _parsed_response(_envelope((first, second)))
    adapter = _adapter(client)

    result = await adapter.infer(chunks=(_chunk(),))

    assert [item.constraint_id for item in result] == [
        "synthetic-limit-1",
        "synthetic-limit-2",
    ]
    assert all(isinstance(item, RegulatoryConstraint) for item in result)


async def test_empty_provider_constraint_collection_returns_empty_tuple() -> None:
    client = _FakeOpenAIClient()
    client.responses.response = _parsed_response(_envelope())
    adapter = _adapter(client)

    result = await adapter.infer(chunks=(_chunk(),))

    assert result == ()
    assert client.responses.parse_calls


async def test_evidence_references_to_supplied_chunks_succeed() -> None:
    client = _FakeOpenAIClient()
    chunks = (
        _chunk(),
        _chunk(chunk_id="chunk-beta", ordinal=1, text="Second synthetic clause body."),
    )
    client.responses.response = _parsed_response(
        _envelope((_candidate(evidence_chunk_ids=(_CHUNK_ID, "chunk-beta")),))
    )
    adapter = _adapter(client)

    result = await adapter.infer(chunks=chunks)

    assert len(result) == 1
    assert result[0].constraint_id == "synthetic-limit-1"


async def test_unknown_evidence_chunk_id_fails_closed() -> None:
    client = _FakeOpenAIClient()
    client.responses.response = _parsed_response(
        _envelope((_candidate(evidence_chunk_ids=("chunk-unknown",)),))
    )
    adapter = _adapter(client)

    with pytest.raises(DependencyUnavailableError, match=_UNAVAILABLE_MESSAGE) as caught:
        await adapter.infer(chunks=(_chunk(),))

    assert caught.value.message == _UNAVAILABLE_MESSAGE
    assert "chunk-unknown" not in caught.value.message
    assert _CHUNK_ID not in caught.value.message
    assert _CHUNK_TEXT_SENTINEL not in caught.value.message


async def test_invalid_canonical_field_values_fail_closed() -> None:
    client = _FakeOpenAIClient()
    client.responses.response = _parsed_response(_envelope((_candidate(currency="usd"),)))
    adapter = _adapter(client)

    with pytest.raises(DependencyUnavailableError, match=_UNAVAILABLE_MESSAGE) as caught:
        await adapter.infer(chunks=(_chunk(),))

    assert caught.value.message == _UNAVAILABLE_MESSAGE
    assert "usd" not in caught.value.message
    assert _CHUNK_TEXT_SENTINEL not in caught.value.message


async def test_invalid_canonical_window_fails_closed() -> None:
    client = _FakeOpenAIClient()
    client.responses.response = _parsed_response(
        _envelope(
            (
                _candidate(
                    effective_from=date(2026, 6, 1),
                    effective_to=date(2026, 5, 1),
                ),
            )
        )
    )
    adapter = _adapter(client)

    with pytest.raises(DependencyUnavailableError, match=_UNAVAILABLE_MESSAGE) as caught:
        await adapter.infer(chunks=(_chunk(),))

    assert caught.value.message == _UNAVAILABLE_MESSAGE
    assert "2026" not in caught.value.message


async def test_missing_parsed_output_fails_closed() -> None:
    client = _FakeOpenAIClient()
    client.responses.response = SimpleNamespace()
    adapter = _adapter(client)

    with pytest.raises(DependencyUnavailableError, match=_UNAVAILABLE_MESSAGE) as caught:
        await adapter.infer(chunks=(_chunk(),))

    assert caught.value.message == _UNAVAILABLE_MESSAGE
    assert _CHUNK_TEXT_SENTINEL not in caught.value.message
    assert client.responses.parse_calls


async def test_unusable_parsed_output_fails_closed() -> None:
    client = _FakeOpenAIClient()
    client.responses.response = SimpleNamespace(output_parsed="not-an-envelope")
    adapter = _adapter(client)

    with pytest.raises(DependencyUnavailableError, match=_UNAVAILABLE_MESSAGE) as caught:
        await adapter.infer(chunks=(_chunk(),))

    assert caught.value.message == _UNAVAILABLE_MESSAGE
    assert "not-an-envelope" not in caught.value.message
    assert _CHUNK_TEXT_SENTINEL not in caught.value.message


async def test_provider_refusal_fails_closed() -> None:
    client = _FakeOpenAIClient()
    client.responses.response = SimpleNamespace(
        output_parsed=None,
        output=[
            SimpleNamespace(
                type="message",
                content=[SimpleNamespace(type="refusal", refusal=_PROVIDER_LEAK)],
            )
        ],
    )
    adapter = _adapter(client)

    with pytest.raises(DependencyUnavailableError, match=_UNAVAILABLE_MESSAGE) as caught:
        await adapter.infer(chunks=(_chunk(),))

    assert caught.value.message == _UNAVAILABLE_MESSAGE
    assert _PROVIDER_LEAK not in caught.value.message
    assert "sk-test-leak" not in caught.value.message
    assert _CHUNK_TEXT_SENTINEL not in caught.value.message


async def test_openai_sdk_failure_becomes_sanitized_dependency_unavailable() -> None:
    client = _FakeOpenAIClient()
    client.responses.error = OpenAIError(_PROVIDER_LEAK)
    adapter = _adapter(client)

    with pytest.raises(DependencyUnavailableError, match=_UNAVAILABLE_MESSAGE) as caught:
        await adapter.infer(chunks=(_chunk(),))

    assert type(caught.value) is DependencyUnavailableError
    assert not isinstance(caught.value, OpenAIError)
    assert caught.value.message == _UNAVAILABLE_MESSAGE
    assert _CHUNK_TEXT_SENTINEL not in caught.value.message
    assert "SENTINEL_CHUNK_BODY" not in caught.value.message
    assert "sk-test-leak" not in caught.value.message
    assert _PROVIDER_LEAK not in caught.value.message
    assert isinstance(caught.value.__cause__, OpenAIError)
    assert client.responses.parse_calls[0]["model"] is _MODEL


async def test_openai_connection_error_is_translated() -> None:
    client = _FakeOpenAIClient()
    client.responses.error = APIConnectionError(request=None)  # type: ignore[arg-type]
    adapter = _adapter(client)

    with pytest.raises(DependencyUnavailableError, match=_UNAVAILABLE_MESSAGE) as caught:
        await adapter.infer(chunks=(_chunk(),))

    assert caught.value.message == _UNAVAILABLE_MESSAGE
    assert _CHUNK_TEXT_SENTINEL not in caught.value.message
    assert isinstance(caught.value.__cause__, APIConnectionError)
    assert not isinstance(caught.value, APIConnectionError)


async def test_returned_values_are_not_provider_objects() -> None:
    client = _FakeOpenAIClient()
    envelope = _envelope((_candidate(),))
    client.responses.response = _parsed_response(envelope)
    adapter = _adapter(client)

    result = await adapter.infer(chunks=(_chunk(),))

    assert result != (envelope,)
    assert result[0] is not envelope
    assert type(result[0]) is RegulatoryConstraint
    assert type(result[0]) is not _ProviderConstraintCandidate
    assert type(result[0]) is not _ProviderInferenceEnvelope
    assert not isinstance(result[0], SimpleNamespace)
