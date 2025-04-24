import asyncio
import json
import typing as t

from aiokafka import AIOKafkaConsumer

from .kafka import KafkaBase, KafkaSettings


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
        startup_timeout: int = 20,
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

    async def getone(self) -> t.Any:  # ConsumerRecord:
        if not self.started:
            raise Exception("Kafka consumer not started")
        if not self.started.done():
            try:
                await asyncio.wait_for(self.started, timeout=self.startup_timeout)
            except asyncio.TimeoutError:
                raise Exception("Kafka consumer not started")

        # TODO: This may get stuck in a loop if value deserializer is JSON and json.loads raises an exception as it
        # doesn't progress to the next record so keeps looping here. How do we fix this?
        return await self.kafka.getone()

    def __aiter__(self) -> t.Any:  # ConsumerRecord:
        return self.kafka.__aiter__()

    async def __anext__(self) -> t.Any:  # ConsumerRecord:
        return await self.kafka.__anext__()
