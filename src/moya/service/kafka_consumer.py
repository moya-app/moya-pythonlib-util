import json
import typing as t

from aiokafka import AIOKafkaConsumer

from .kafka import KafkaBase, KafkaSettings


class KafkaConsumer(KafkaBase):
    """
    Basic Kafka Consumer - we don't use it in many places so not as sophisticated as the producer code.
    """

    def __init__(self, settings: KafkaSettings, group: str, topics: list[str], startup_timeout: int = 20) -> None:
        super().__init__(settings, startup_timeout)
        self.group = group
        self.topics = topics

    async def start(self, **kwargs: dict) -> None:
        self.kafka = AIOKafkaConsumer(
            *self.topics,
            **self.settings.as_kafka(),
            **kwargs,
            group_id=self.group,
            value_deserializer=lambda msg: json.loads(msg),
        )
        await super().start()

    async def getone(self) -> t.Any:  # ConsumerRecord:
        return await self.kafka.getone()

    async def __anext__(self) -> t.Any:  # ConsumerRecord:
        return await self.kafka.__anext__()
