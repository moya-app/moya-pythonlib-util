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
        self.kafka = AIOKafkaConsumer(
            *topics,
            **self.settings.as_kafka(),
            **kwargs,
            group_id=group,
            value_deserializer=lambda msg: json.loads(msg),
        )

    async def getone(self) -> t.Any:  # ConsumerRecord:
        return await self.kafka.getone()

    async def __anext__(self) -> t.Any:  # ConsumerRecord:
        return await self.kafka.__anext__()
