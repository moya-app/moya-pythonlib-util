import asyncio
import json
import typing as t

from aiokafka import AIOKafkaConsumer

from .kafka import KafkaBase, KafkaSettings

# Hack for lack of typing
ConsumerRecord = t.Any
TopicPartition = t.Any


class KafkaConsumer(KafkaBase):
    """
    Basic Kafka Consumer - we don't use it in many places so not as sophisticated as the producer code.

    Usage:

    import asyncio
    from moya.service.kafka_consumer import KafkaConsumer, KafkaSettings

    KAFKA_CONSUMER_GROUP = "cg"
    async def main():
        consumer = KafkaConsumer(
            KafkaSettings(),
            KAFKA_CONSUMER_GROUP,
            ["topic1", "topic2"],
        )
        async with consumer.run():
            record = await consumer.getone()

    asyncio.run(main())
    """

    def __init__(
        self,
        settings: KafkaSettings,
        group: str,
        topics: list[str],
        startup_timeout: float = 20,
        value_deserializer: t.Callable[[str], t.Any] | None = lambda msg: json.loads(msg),
        **kwargs: t.Any,
    ) -> None:
        super().__init__(settings, startup_timeout)
        self.group = group
        self.topics = topics
        self.value_deserializer = value_deserializer
        self.kafka_extra_kwargs = kwargs

    async def _initialize(self) -> None:
        self.kafka = AIOKafkaConsumer(
            *self.topics,
            **self.settings.as_kafka(),
            **self.kafka_extra_kwargs,
            group_id=self.group,
            value_deserializer=self.value_deserializer,
        )
        await super()._initialize()

    async def _check_started(self) -> None:
        if not self.started:
            raise Exception("Kafka consumer not started")
        if not self.started.done():
            try:
                await asyncio.wait_for(self.started, timeout=self.startup_timeout)
            except asyncio.TimeoutError:
                raise Exception("Kafka consumer not started")

    async def getone(self) -> ConsumerRecord:
        await self._check_started()
        return await self.kafka.getone()

    async def getmany(self, *partitions: str, timeout_ms: int = 0, max_records: int | None = None) -> dict[TopicPartition, list[ConsumerRecord]]:
        await self._check_started()
        return t.cast(dict[TopicPartition, list[ConsumerRecord]], await self.kafka.getmany(*partitions, timeout_ms=timeout_ms, max_records=max_records))

    def __aiter__(self) -> t.AsyncIterator[ConsumerRecord]:
        return t.cast(t.AsyncIterator[ConsumerRecord], self.kafka.__aiter__())

    async def __anext__(self) -> ConsumerRecord:
        return await self.kafka.__anext__()
