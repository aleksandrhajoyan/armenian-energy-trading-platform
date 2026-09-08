"""Regulatory Intelligence HTTP transport DTOs stay aligned with canonical contracts."""

from __future__ import annotations

import inspect
from datetime import date
from math import inf, nan

import pytest
from pydantic import ValidationError

from energy_trading.api.schemas.regulatory_intelligence import (
    RegulatoryConstraintResponse,
    RegulatoryIntelligenceQueryRequest,
    RegulatoryIntelligenceQueryResponse,
)
from energy_trading.application.agents.regulatory_intelligence import (
    RegulatoryIntelligenceResult,
)
from energy_trading.application.orchestration.regulatory_intelligence_query_execution import (
    RegulatoryIntelligenceQueryExecutionService,
)
from energy_trading.domain.models.regulatory import RegulatoryConstraint

_PROVIDER_FIELD_NAMES = frozenset(
    {
        "openai",
        "qdrant",
        "api_key",
        "model",
        "collection",
        "vector",
        "embedding",
        "url",
        "retry",
        "client",
    }
)


def _constraint_payload(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "constraint_id": "constraint-1",
        "constraint_type": "capacity_limit",
        "description": "Generic numeric bound",
        "effective_from": date(2026, 1, 1),
        "effective_to": date(2026, 12, 31),
        "minimum_value": 1.5,
        "maximum_value": 10.25,
        "unit": "MW",
        "currency": "AMD",
        "source_document_id": "doc-1",
    }
    values.update(overrides)
    return values


def test_request_happy_path_preserves_typed_field_values() -> None:
    query_text = "  surrounding spaces are preserved  "
    request = RegulatoryIntelligenceQueryRequest(query_text=query_text, limit=7)
    assert request.query_text == query_text
    assert request.query_text != query_text.strip()
    assert request.limit == 7


def test_request_requires_query_text_and_limit() -> None:
    with pytest.raises(ValidationError) as missing_query:
        RegulatoryIntelligenceQueryRequest.model_validate({"limit": 3})
    assert "query_text" in str(missing_query.value)
    with pytest.raises(ValidationError) as missing_limit:
        RegulatoryIntelligenceQueryRequest.model_validate({"query_text": "rules query"})
    assert "limit" in str(missing_limit.value)


def test_request_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        RegulatoryIntelligenceQueryRequest.model_validate(
            {
                "query_text": "rules query",
                "limit": 3,
                "collection": "regulatory-docs",
            }
        )


def test_request_rejects_non_positive_limit() -> None:
    with pytest.raises(ValidationError):
        RegulatoryIntelligenceQueryRequest(query_text="rules query", limit=0)
    with pytest.raises(ValidationError):
        RegulatoryIntelligenceQueryRequest(query_text="rules query", limit=-1)


def test_request_accepts_any_string_query_text_without_stripping() -> None:
    blank = RegulatoryIntelligenceQueryRequest(query_text="", limit=1)
    assert blank.query_text == ""
    whitespace = RegulatoryIntelligenceQueryRequest(query_text="   ", limit=1)
    assert whitespace.query_text == "   "


def test_response_happy_path_retains_nested_values() -> None:
    constraint = RegulatoryConstraintResponse.model_validate(_constraint_payload())
    response = RegulatoryIntelligenceQueryResponse(constraints=(constraint,))
    assert response.constraints == (constraint,)
    stored = response.constraints[0]
    assert stored.constraint_id == "constraint-1"
    assert stored.constraint_type == "capacity_limit"
    assert stored.description == "Generic numeric bound"
    assert stored.effective_from == date(2026, 1, 1)
    assert stored.effective_to == date(2026, 12, 31)
    assert stored.minimum_value == 1.5
    assert stored.maximum_value == 10.25
    assert stored.unit == "MW"
    assert stored.currency == "AMD"
    assert stored.source_document_id == "doc-1"


def test_response_accepts_empty_constraints() -> None:
    response = RegulatoryIntelligenceQueryResponse(constraints=())
    assert response.constraints == ()


def test_nested_constraint_rejects_unknown_fields() -> None:
    payload = _constraint_payload(score=0.99)
    with pytest.raises(ValidationError):
        RegulatoryConstraintResponse.model_validate(payload)


def test_nested_constraint_rejects_empty_required_text() -> None:
    with pytest.raises(ValidationError):
        RegulatoryConstraintResponse.model_validate(_constraint_payload(constraint_id=""))
    with pytest.raises(ValidationError):
        RegulatoryConstraintResponse.model_validate(_constraint_payload(unit=""))


def test_nested_constraint_rejects_invalid_currency_and_non_finite_values() -> None:
    with pytest.raises(ValidationError):
        RegulatoryConstraintResponse.model_validate(_constraint_payload(currency="amd"))
    with pytest.raises(ValidationError):
        RegulatoryConstraintResponse.model_validate(_constraint_payload(minimum_value=inf))
    with pytest.raises(ValidationError):
        RegulatoryConstraintResponse.model_validate(_constraint_payload(maximum_value=nan))


def test_response_json_serialization_uses_iso_dates_and_array_constraints() -> None:
    constraint = RegulatoryConstraintResponse.model_validate(_constraint_payload())
    response = RegulatoryIntelligenceQueryResponse(constraints=(constraint,))
    payload = response.model_dump(mode="json")
    assert payload == {
        "constraints": [
            {
                "constraint_id": "constraint-1",
                "constraint_type": "capacity_limit",
                "description": "Generic numeric bound",
                "effective_from": "2026-01-01",
                "effective_to": "2026-12-31",
                "minimum_value": 1.5,
                "maximum_value": 10.25,
                "unit": "MW",
                "currency": "AMD",
                "source_document_id": "doc-1",
            }
        ]
    }


def test_request_and_response_align_with_canonical_application_contracts() -> None:
    execute_params = inspect.signature(
        RegulatoryIntelligenceQueryExecutionService.execute
    ).parameters
    assert tuple(name for name in execute_params if name != "self") == ("query_text", "limit")
    assert execute_params["query_text"].annotation is str
    assert execute_params["limit"].annotation is int
    assert execute_params["query_text"].default is inspect.Parameter.empty
    assert execute_params["limit"].default is inspect.Parameter.empty
    assert tuple(RegulatoryIntelligenceQueryRequest.model_fields) == ("query_text", "limit")
    assert RegulatoryIntelligenceQueryRequest.model_fields["query_text"].is_required()
    assert RegulatoryIntelligenceQueryRequest.model_fields["limit"].is_required()
    assert tuple(RegulatoryIntelligenceResult.__dataclass_fields__) == ("constraints",)
    assert tuple(RegulatoryIntelligenceQueryResponse.model_fields) == ("constraints",)
    assert tuple(RegulatoryConstraint.model_fields) == tuple(
        RegulatoryConstraintResponse.model_fields
    )


def test_transport_models_do_not_expose_provider_fields() -> None:
    field_names = {
        *RegulatoryIntelligenceQueryRequest.model_fields,
        *RegulatoryIntelligenceQueryResponse.model_fields,
        *RegulatoryConstraintResponse.model_fields,
    }
    leaked = sorted(name for name in field_names if name in _PROVIDER_FIELD_NAMES)
    assert leaked == []


def test_schema_module_does_not_invoke_query_execution() -> None:
    assert not hasattr(RegulatoryIntelligenceQueryRequest, "execute")
    assert not hasattr(RegulatoryIntelligenceQueryResponse, "execute")
    assert "execute" not in RegulatoryIntelligenceQueryRequest.model_fields
    assert "execute" not in RegulatoryIntelligenceQueryResponse.model_fields
