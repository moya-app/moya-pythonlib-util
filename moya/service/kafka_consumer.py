import json
import typing as t

from aiokafka import AIOKafkaConsumer

from .kafka import KafkaBase, KafkaSettings


class KafkaConsumer(KafkaBase):
    """
    Basic Kafka Consumer - we don't use it in many places so not as sophisticated as the producer code.
    """

    def __init__(
        self,
        settings: KafkaSettings,
        group: str,
        topics: list[str],
        startup_timeout: int = 20,
        value_deserializer: t.Callable[[str], t.Any] = lambda msg: json.loads(msg),
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
        return await self.kafka.getone()

    async def __anext__(self) -> t.Any:  # ConsumerRecord:
        return await self.kafka.__anext__()
