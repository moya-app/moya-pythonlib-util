import abc
import asyncio
import logging
from datetime import datetime
from typing import Generic, TypeVar

from opentelemetry import propagate, trace
from opentelemetry.instrumentation.aiokafka.utils import _aiokafka_getter
from opentelemetry.trace import Status, StatusCode

from moya.service.kafka_consumer import ConsumerRecord, KafkaConsumer, KafkaSettings
from moya.util.asyncpool import asyncpool_queue

# OTEL other instrumentation is set up automatically by opentelemetry-instrument -a as we won't be forking
tracer = trace.get_tracer(__name__)

logger = logging.getLogger(__name__)


T = TypeVar("T")


class KafkaRunner(abc.ABC, Generic[T]):
    """
    Base class for running a Kafka consumer and processing the messages via pydantic with appropriate logging and error
    handling.

    Simply implement the various abstract methods below and then do something like:

    import asyncio
    from moya.util.logging import setup_logging
    from moya.util.sentry import init as setup_sentry

    class KafkaUserDetailUpdater(KafkaRunner[pydantic class]):
        ...

    async def main() -> None:
        setup_logging()
        setup_sentry()
        await KafkaUserDetailUpdater(process_batch_size=5).run()

    if __name__ == "__main__":
        asyncio.run(main())

    If you are inserting records into a database, because of the network latency you likely want to run with
    `process_batch_size=5` or so to ensure that the process_item() tasks run in parallel so that full CPU can be used.
    """

    def __init__(
        self,
        consumer_group: str,
        topics: list[str],
        kafka_batch_size: int = 100,
        process_batch_size: int = 1,
    ) -> None:
        """
        :param consumer_group: The consumer group name to use
        :param topics: The list of topics to consume from
        :param kafka_batch_size: The number of records to fetch from Kafka at a time. The commit only happens after all
            of these records have been processed so any bugs or process exit will cause this whole batch to be retried
            by the next process meaning you may get duplicates but you should never loose records.
        :param process_batch_size: The number of parallel instances of process_item() to run at a time
        """
        self.consumer_group = consumer_group
        self.topics = topics
        self.kafka_batch_size = kafka_batch_size
        self.process_batch_size = process_batch_size
        self.consumer = KafkaConsumer(
            KafkaSettings(),
            consumer_group,
            topics,
            value_deserializer=None,
            # TODO: Figure out auto-commit and enable it. Currently has lots of errors when consumer-group
            # rebalances
            # enable_auto_commit=False,
            enable_auto_commit=True,
            auto_offset_reset="latest",
        )
        self.counter = 0

    @abc.abstractmethod
    def parse_record(self, topic: str, value: bytes) -> tuple[T, str] | None:
        """
        Return the raw Kafka item into a (pydantic) item and a string which is used for logging. Return None to skip
        processing.
        """
        ...

    @abc.abstractmethod
    async def process_item(self, item: T, timestamp: datetime) -> None:
        "Process the item - insert into a database or similar"
        ...

    async def _process_record(self, record: ConsumerRecord) -> None:
        """
        Process the given record from Kafka.
        """
        # Pull the propagated trace from the consumer message so it ties back to the original request
        # TODO: Move this into a pythonlib util helper function.
        context = propagate.extract(record.headers, getter=_aiokafka_getter)
        with tracer.start_as_current_span("process-record", context=context) as span:
            try:
                result = self.parse_record(record.topic, record.value)
                if result is None:
                    return
                item, logging_key = result
            except Exception as e:
                logger.exception(f"Received invalid JSON input for {record.value} (topic: {record.topic})", exc_info=e)
                span.set_status(Status(StatusCode.ERROR))
                span.set_attribute("error.message", str(e))
                span.set_attribute("error.input", record.value)
                # await run_in_background(self.consumer.kafka.commit())  # commit after logging the error
                return

            timestamp = datetime.fromtimestamp(record.timestamp / 1000)

            try:
                await self.process_item(item, timestamp)
                self.counter += 1
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR))
                span.set_attribute("error.message", str(e))
                span.set_attribute("error.input", record.value)

                logger.exception(f"Error processing {logging_key} {record.value}", exc_info=e)
                # Don't commit because we want to retry probably???
            else:
                # Doesn't matter if this fails for some reason, we can always re-process the record but we
                # don't want to loose any records
                # await run_in_background(self.consumer.kafka.commit())

                logger.debug(f"Processed for {logging_key} lag {datetime.now() - timestamp}")
                if self.counter % 1000 == 0:
                    # TODO: Alert sentry if lag > 30 min or something? But only once... Look at avg
                    # lag of the last few records.
                    logger.info(f"Processed {self.counter} items, last lag for partition {record.partition} was {datetime.now() - timestamp}")

    async def run(self) -> None:
        async with (
            self.consumer.run(),
            asyncpool_queue(self._process_record, worker_count=self.process_batch_size, maxsize=self.process_batch_size * 3) as queue,
        ):
            while True:
                try:
                    records = await self.consumer.getmany(max_records=self.kafka_batch_size)
                except Exception as e:
                    logger.exception("Unknown Kafka exception", exc_info=e)
                    await asyncio.sleep(0.1)
                    continue

                for topic, record_list in records.items():
                    for record in record_list:
                        await queue.put(record)

                # Wait for all the tasks to complete so that we know all items have been fully processed. If one is
                # particularly slow then this could cause some unnecessary waiting but it's a bit more robust than
                # keeping unprocessed items in the queue from the previous kafka batch.
                await queue.join()
