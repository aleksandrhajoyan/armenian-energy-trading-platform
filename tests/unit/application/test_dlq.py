"""Dead Letter Queue application-port contract."""

from energy_trading.application.ports import DeadLetterQueuePort
from tests.unit.application.fakes import InMemoryDeadLetterQueue, as_dlq_port
from tests.unit.domain._factories import dlq


async def test_in_memory_dlq_accepts_canonical_record() -> None:
    memory = InMemoryDeadLetterQueue()
    port: DeadLetterQueuePort = as_dlq_port(memory)
    record = dlq()

    await port.enqueue(record)

    assert memory.records == (record,)
    assert memory.records[0].payload_reference == "blob://ingestion/dlq-1"
    assert not hasattr(record, "payload")
    assert "payload" not in record.model_dump()
