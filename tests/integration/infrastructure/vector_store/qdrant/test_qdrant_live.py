"""Live Qdrant server and document-vector adapter tests.

These tests require the Compose ``qdrant`` profile and
``ENERGY_RUN_QDRANT_INTEGRATION=1``. They never embed query text and do not
select a production distance metric.
"""

from __future__ import annotations

from dataclasses import fields

import pytest
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse

from energy_trading.application.errors import ConflictError
from energy_trading.application.ports import (
    DocumentChunkEmbedding,
    DocumentVectorIndexEntry,
    DocumentVectorSearchQuery,
    ExtractedDocumentChunk,
)
from energy_trading.infrastructure.vector_store.qdrant.document_vector import (
    QdrantDocumentVectorConfig,
    QdrantDocumentVectorIndex,
    QdrantDocumentVectorSearch,
)
from energy_trading.shared.config.qdrant import QdrantSettings
from tests.integration.infrastructure.vector_store.qdrant.conftest import (
    qdrant_integration_enabled,
)

pytestmark = [
    pytest.mark.qdrant_integration,
    pytest.mark.skipif(
        not qdrant_integration_enabled(),
        reason="ENERGY_RUN_QDRANT_INTEGRATION=1 is required",
    ),
]

CHUNK_FIELD_NAMES = frozenset(item.name for item in fields(ExtractedDocumentChunk))


def _entry(
    *,
    document_id: str,
    chunk_id: str,
    text: str,
    vector: tuple[float, ...],
    ordinal: int = 0,
    page_number: int | None = 1,
) -> DocumentVectorIndexEntry:
    chunk = ExtractedDocumentChunk(
        document_id=document_id,
        chunk_id=chunk_id,
        ordinal=ordinal,
        text=text,
        page_number=page_number,
    )
    embedding = DocumentChunkEmbedding(
        document_id=document_id,
        chunk_id=chunk_id,
        vector=vector,
    )
    return DocumentVectorIndexEntry(chunk=chunk, embedding=embedding)


def _index(
    client: AsyncQdrantClient,
    config: QdrantDocumentVectorConfig,
) -> QdrantDocumentVectorIndex:
    return QdrantDocumentVectorIndex(client, config)


def _search(
    client: AsyncQdrantClient,
    config: QdrantDocumentVectorConfig,
) -> QdrantDocumentVectorSearch:
    return QdrantDocumentVectorSearch(client, config)


async def _exact_count(client: AsyncQdrantClient, collection_name: str) -> int:
    result = await client.count(collection_name=collection_name, exact=True)
    return int(result.count)


def _assert_chunk_without_score(chunk: ExtractedDocumentChunk) -> None:
    assert isinstance(chunk, ExtractedDocumentChunk)
    assert "score" not in CHUNK_FIELD_NAMES
    assert not hasattr(chunk, "score")
    assert not hasattr(chunk, "similarity")
    assert not hasattr(chunk, "distance")


async def test_authenticated_get_collections_succeeds(qdrant_client: AsyncQdrantClient) -> None:
    collections = await qdrant_client.get_collections()
    assert collections is not None
    assert hasattr(collections, "collections")


async def test_unauthenticated_get_collections_is_rejected(
    qdrant_settings: QdrantSettings,
) -> None:
    unauthenticated = AsyncQdrantClient(
        host=qdrant_settings.host,
        port=qdrant_settings.port,
        https=False,
        api_key=None,
        timeout=qdrant_settings.timeout_seconds,
        prefer_grpc=False,
        cloud_inference=False,
        check_compatibility=False,
    )
    try:
        with pytest.raises(UnexpectedResponse) as captured:
            await unauthenticated.get_collections()
        status = captured.value.status_code
        assert status in {401, 403}
        message = str(captured.value)
        secret = qdrant_settings.api_key
        assert secret is not None
        assert secret.get_secret_value() not in message
    finally:
        await unauthenticated.close()


async def test_index_new_entry_is_searchable(
    qdrant_client: AsyncQdrantClient,
    qdrant_config: QdrantDocumentVectorConfig,
) -> None:
    entry = _entry(
        document_id="doc-index",
        chunk_id="chunk-1",
        text="live indexed chunk",
        vector=(1.0, 0.0, 0.0),
    )
    await _index(qdrant_client, qdrant_config).index((entry,))
    assert await _exact_count(qdrant_client, qdrant_config.collection_name) == 1
    results = await _search(qdrant_client, qdrant_config).search(
        DocumentVectorSearchQuery(vector=(1.0, 0.0, 0.0), limit=1)
    )
    assert results == (entry.chunk,)


async def test_index_multiple_identities_in_one_call(
    qdrant_client: AsyncQdrantClient,
    qdrant_config: QdrantDocumentVectorConfig,
) -> None:
    first = _entry(
        document_id="doc-multi",
        chunk_id="chunk-a",
        text="first live chunk",
        vector=(1.0, 0.0, 0.0),
    )
    second = _entry(
        document_id="doc-multi",
        chunk_id="chunk-b",
        text="second live chunk",
        vector=(0.0, 1.0, 0.0),
    )
    await _index(qdrant_client, qdrant_config).index((first, second))
    assert await _exact_count(qdrant_client, qdrant_config.collection_name) == 2
    results = await _search(qdrant_client, qdrant_config).search(
        DocumentVectorSearchQuery(vector=(1.0, 0.0, 0.0), limit=2)
    )
    identities = {(item.document_id, item.chunk_id) for item in results}
    assert identities == {
        (first.chunk.document_id, first.chunk.chunk_id),
        (second.chunk.document_id, second.chunk.chunk_id),
    }


async def test_exact_retry_indexes_one_point(
    qdrant_client: AsyncQdrantClient,
    qdrant_config: QdrantDocumentVectorConfig,
) -> None:
    entry = _entry(
        document_id="doc-retry",
        chunk_id="chunk-1",
        text="exact retry chunk",
        vector=(0.0, 1.0, 0.0),
    )
    adapter = _index(qdrant_client, qdrant_config)
    await adapter.index((entry,))
    await adapter.index((entry,))
    assert await _exact_count(qdrant_client, qdrant_config.collection_name) == 1
    results = await _search(qdrant_client, qdrant_config).search(
        DocumentVectorSearchQuery(vector=(0.0, 1.0, 0.0), limit=5)
    )
    assert results == (entry.chunk,)


async def test_same_identity_conflict_does_not_overwrite(
    qdrant_client: AsyncQdrantClient,
    qdrant_config: QdrantDocumentVectorConfig,
) -> None:
    original = _entry(
        document_id="doc-conflict",
        chunk_id="chunk-1",
        text="original live text",
        vector=(1.0, 0.0, 0.0),
    )
    changed = _entry(
        document_id="doc-conflict",
        chunk_id="chunk-1",
        text="changed live text",
        vector=(0.0, 1.0, 0.0),
    )
    adapter = _index(qdrant_client, qdrant_config)
    await adapter.index((original,))
    with pytest.raises(ConflictError, match="already indexed"):
        await adapter.index((changed,))
    assert await _exact_count(qdrant_client, qdrant_config.collection_name) == 1
    results = await _search(qdrant_client, qdrant_config).search(
        DocumentVectorSearchQuery(vector=(1.0, 0.0, 0.0), limit=1)
    )
    assert results == (original.chunk,)
    assert results[0].text == "original live text"


async def test_search_returns_ranked_extracted_chunks(
    qdrant_client: AsyncQdrantClient,
    qdrant_config: QdrantDocumentVectorConfig,
) -> None:
    most = _entry(
        document_id="doc-rank",
        chunk_id="most",
        text="most relevant live chunk",
        vector=(1.0, 0.0, 0.0),
    )
    mid = _entry(
        document_id="doc-rank",
        chunk_id="mid",
        text="mid relevant live chunk",
        vector=(0.5, 0.0, 0.0),
    )
    least = _entry(
        document_id="doc-rank",
        chunk_id="least",
        text="least relevant live chunk",
        vector=(0.0, 1.0, 0.0),
    )
    await _index(qdrant_client, qdrant_config).index((least, most, mid))
    results = await _search(qdrant_client, qdrant_config).search(
        DocumentVectorSearchQuery(vector=(1.0, 0.0, 0.0), limit=3)
    )
    assert results == (most.chunk, mid.chunk, least.chunk)
    for chunk in results:
        _assert_chunk_without_score(chunk)


async def test_search_respects_limit(
    qdrant_client: AsyncQdrantClient,
    qdrant_config: QdrantDocumentVectorConfig,
) -> None:
    most = _entry(
        document_id="doc-limit",
        chunk_id="most",
        text="limit most relevant",
        vector=(1.0, 0.0, 0.0),
    )
    mid = _entry(
        document_id="doc-limit",
        chunk_id="mid",
        text="limit mid relevant",
        vector=(0.5, 0.0, 0.0),
    )
    least = _entry(
        document_id="doc-limit",
        chunk_id="least",
        text="limit least relevant",
        vector=(0.0, 1.0, 0.0),
    )
    await _index(qdrant_client, qdrant_config).index((most, mid, least))
    results = await _search(qdrant_client, qdrant_config).search(
        DocumentVectorSearchQuery(vector=(1.0, 0.0, 0.0), limit=2)
    )
    assert results == (most.chunk, mid.chunk)
    assert len(results) == 2


async def test_search_on_empty_collection_returns_empty_tuple(
    qdrant_client: AsyncQdrantClient,
    qdrant_config: QdrantDocumentVectorConfig,
) -> None:
    results = await _search(qdrant_client, qdrant_config).search(
        DocumentVectorSearchQuery(vector=(1.0, 0.0, 0.0), limit=5)
    )
    assert results == ()


async def test_search_does_not_expose_scores(
    qdrant_client: AsyncQdrantClient,
    qdrant_config: QdrantDocumentVectorConfig,
) -> None:
    entry = _entry(
        document_id="doc-score",
        chunk_id="chunk-1",
        text="score-free live chunk",
        vector=(1.0, 0.0, 0.0),
    )
    await _index(qdrant_client, qdrant_config).index((entry,))
    results = await _search(qdrant_client, qdrant_config).search(
        DocumentVectorSearchQuery(vector=(1.0, 0.0, 0.0), limit=1)
    )
    assert len(results) == 1
    _assert_chunk_without_score(results[0])
    assert results[0] == entry.chunk
