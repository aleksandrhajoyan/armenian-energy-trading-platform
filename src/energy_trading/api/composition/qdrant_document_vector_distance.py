"""Map configured document-vector distance to Qdrant SDK Distance.

This module translates an already-validated provider-neutral distance into the
Qdrant ``Distance`` enum. It does not load settings, inspect the environment,
construct clients, or invoke collection primitives.
"""

from typing import Final

from qdrant_client.http.models import Distance

from energy_trading.shared.config.qdrant import QdrantDocumentVectorDistance

_QDRANT_DISTANCE_BY_CONFIG: Final[dict[QdrantDocumentVectorDistance, Distance]] = {
    QdrantDocumentVectorDistance.COSINE: Distance.COSINE,
    QdrantDocumentVectorDistance.DOT: Distance.DOT,
    QdrantDocumentVectorDistance.EUCLID: Distance.EUCLID,
    QdrantDocumentVectorDistance.MANHATTAN: Distance.MANHATTAN,
}


def map_qdrant_document_vector_distance(
    *,
    distance: QdrantDocumentVectorDistance,
) -> Distance:
    """Return the Qdrant SDK distance for a configured document-vector metric.

    The mapping is total over ``QdrantDocumentVectorDistance``. Unknown values
    fail closed rather than selecting a metric.
    """

    try:
        return _QDRANT_DISTANCE_BY_CONFIG[distance]
    except KeyError as exc:
        raise ValueError("Unsupported document vector distance.") from exc
