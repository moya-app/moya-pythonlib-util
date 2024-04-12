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

    @asynccontextmanager
    async def fastapi_lifespan(app: FastAPI) -> t.AsyncGenerator[None, None]:
        asyncio.ensure_future(kafka_producer().start())

        yield

        await kafka_producer().stop()

    app = FastAPI(..., lifespan=fastapi_lifespan)


    Then when you want to produce something:

    await kafka_producer().send("topic", {"key": "value"})
    """

    async def start(self) -> None:
        self.kafka = aiokafka.AIOKafkaProducer(
            **self.settings.as_kafka(),
            # Producer optimizations
            linger_ms=200,  # 200ms batches to improve send performance
            compression_type="lz4",
        )
        await super().start()

    async def send_nowait(
        self, topic: str, payload: dict, timestamp_ms: int = None, encoder: t.Type[json.JSONEncoder] | None = None
    ) -> asyncio.Future:  # [aiokafka.RecordMetadata]:
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
        return t.cast(asyncio.Future, fut)

    async def send(
        self, topic: str, payload: dict, timestamp_ms: int = None, encoder: t.Type[json.JSONEncoder] | None = None
    ) -> t.Any:  # aiokafka.RecordMetadata:
        """
        Send a message to kafka and wait for it to successfully complete. This
        may block for a few seconds, so you should run it in the background to
        allow batching, for example using moya.util.background.run_in_background()

        A custom encoder may also be specified to encode the payload.
        """
        return await self.send_nowait(topic, payload, timestamp_ms, encoder)


@cache
def kafka_producer(settings: KafkaSettings = None) -> KafkaProducer:
    if settings is None:
        settings = KafkaSettings()
    return KafkaProducer(settings)
