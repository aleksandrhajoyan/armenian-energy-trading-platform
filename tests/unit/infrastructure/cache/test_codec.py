"""Infrastructure-local cache codec contract."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from energy_trading.domain.models import ConsumptionRecord
from energy_trading.infrastructure.cache.codec import CacheCodec, CacheCodecError
from tests.unit.domain._factories import consumption


class _ConsumptionRecordCodec:
    """Test-only deterministic codec. Not a production serializer."""

    def encode(self, value: ConsumptionRecord) -> bytes:
        return value.model_dump_json().encode("utf-8")

    def decode(self, payload: bytes) -> ConsumptionRecord:
        try:
            return ConsumptionRecord.model_validate_json(payload)
        except ValidationError as exc:
            raise CacheCodecError("unable to decode consumption record") from exc


def _as_codec(codec: _ConsumptionRecordCodec) -> CacheCodec[ConsumptionRecord]:
    return codec


def test_codec_structurally_satisfies_protocol() -> None:
    codec = _as_codec(_ConsumptionRecordCodec())
    assert callable(codec.encode)
    assert callable(codec.decode)


def test_codec_round_trips_typed_consumption_record() -> None:
    codec = _as_codec(_ConsumptionRecordCodec())
    record = consumption()
    payload = codec.encode(record)
    assert isinstance(payload, bytes)
    loaded = codec.decode(payload)
    assert loaded == record
    assert isinstance(loaded, ConsumptionRecord)


def test_codec_decode_failure_is_cache_codec_error() -> None:
    codec = _as_codec(_ConsumptionRecordCodec())
    with pytest.raises(CacheCodecError):
        codec.decode(b"not-a-consumption-record")
