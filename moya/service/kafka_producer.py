import asyncio
import json
import typing as t
from functools import cache

import aiokafka

from .kafka import KafkaBase, KafkaSettings


class KafkaProducer(KafkaBase):
    """
    Usage:

    Set up the kafka system:

    import asyncio
    import typing as t
    from contextlib import asynccontextmanager
    from moya.service.kafka import kafka_producer
    from moya.util.background import run_in_background

    @asynccontextmanager
    async def fastapi_lifespan(app: FastAPI) -> t.AsyncGenerator[None, None]:
        async with kafka_producer().run():
            yield

    app = FastAPI(..., lifespan=fastapi_lifespan)


    Then when you want to produce something:

    await kafka_producer().send("topic", {"key": "value"})
    """

    def __init__(self, settings: KafkaSettings, startup_timeout: int = 20) -> None:
        super().__init__(settings, startup_timeout)

    async def _initialize(self) -> None:
        self.kafka = aiokafka.AIOKafkaProducer(
            **self.settings.as_kafka_producer(),
            # Producer optimizations
            compression_type="lz4",
        )
        await super()._initialize()

    async def send_nowait(
        self,
        topic: str,
        payload: dict[str, t.Any],
        timestamp_ms: int | None = None,
        encoder: t.Type[json.JSONEncoder] | None = None,
    ) -> asyncio.Future[t.Any]:  # [aiokafka.RecordMetadata]:
        """
        Send a message to kafka and return a future which will be resolved when
        the message send has been completed

        A custom encoder may also be specified to encode the payload.
        """
        if not self.started:
            raise Exception("Kafka producer not started")
        if not self.started.done():
            try:
                await asyncio.wait_for(self.started, timeout=self.startup_timeout)
            except asyncio.TimeoutError:
                raise Exception("Kafka producer not started")

        fut = await self.kafka.send(topic, json.dumps(payload, cls=encoder).encode("utf-8"), timestamp_ms=timestamp_ms)
        # return t.cast(asyncio.Future[aiokafka.RecordMetadata], fut)
        return t.cast(asyncio.Future[t.Any], fut)

    async def send(
        self,
        topic: str,
        payload: dict[str, t.Any],
        timestamp_ms: int | None = None,
        encoder: t.Type[json.JSONEncoder] | None = None,
    ) -> t.Any:  # aiokafka.RecordMetadata:
        """
        Send a message to kafka and wait for it to successfully complete. This
        may block for a few seconds, so you should run it in the background to
        allow batching, for example using moya.util.background.run_in_background()

        A custom encoder may also be specified to encode the payload.
        """
        return await self.send_nowait(topic, payload, timestamp_ms, encoder)


@cache
def kafka_producer(settings: KafkaSettings | None = None) -> KafkaProducer:
    if settings is None:
        settings = KafkaSettings()
    return KafkaProducer(settings)
