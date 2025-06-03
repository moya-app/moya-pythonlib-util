import abc
import asyncio
import logging
from datetime import datetime
from typing import Generic, TypeVar

from opentelemetry import propagate, trace
from opentelemetry.instrumentation.aiokafka.utils import _aiokafka_getter
from opentelemetry.trace import Status, StatusCode

from moya.service.kafka_consumer import KafkaConsumer, KafkaSettings

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
        await KafkaUserDetailUpdater().run()

    if __name__ == "__main__":
        asyncio.run(main())
    """

    def __init__(self, consumer_group: str, topics: list[str]) -> None:
        self.consumer_group = consumer_group
        self.topics = topics
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

    async def run(self) -> None:
        # TODO: Batch into a single txn for a number of updates in order to reduce database load?
        async with self.consumer.run():
            counter = 0
            while True:
                try:
                    record = await self.consumer.getone()
                except Exception as e:
                    logger.exception("Unknown Kafka exception", exc_info=e)
                    await asyncio.sleep(0.1)
                    continue

                # Pull the propagated trace from the consumer message so it ties back to the original request
                # TODO: Move this into a pythonlib util helper function.
                context = propagate.extract(record.headers, getter=_aiokafka_getter)
                with tracer.start_as_current_span("process-record", context=context) as span:
                    try:
                        result = self.parse_record(record.topic, record.value)
                        if result is None:
                            continue
                        item, logging_key = result
                    except Exception as e:
                        logger.exception(f"Received invalid JSON input for {record.value} (topic: {record.topic})", exc_info=e)
                        span.set_status(Status(StatusCode.ERROR))
                        span.set_attribute("error.message", str(e))
                        span.set_attribute("error.input", record.value)
                        # await run_in_background(self.consumer.kafka.commit())  # commit after logging the error
                        continue

                    timestamp = datetime.fromtimestamp(record.timestamp / 1000)

                    try:
                        await self.process_item(item, timestamp)
                        counter += 1
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
                        if counter % 1000 == 0:
                            # TODO: Alert sentry if lag > 30 min or something? But only once... Look at avg
                            # lag of the last few records.
                            logger.info(f"Processed {counter} items, last lag for partition {record.partition} was {datetime.now() - timestamp}")
