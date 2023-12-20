import asyncio
import json
import logging
from functools import cache

import aiokafka
from aiokafka.helpers import create_ssl_context

from moya.util.config import MoyaSettings

logger = logging.getLogger("kafka")


class KafkaSettings(MoyaSettings):
    """
    Pull settings from standardized kafka settings in environment variables
    """

    kafka_sasl_mechanism: str
    kafka_security_protocol: str = "SASL_SSL"
    kafka_username: str
    kafka_password: str
    kafka_brokers: str


class KafkaProducer:
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

    def __init__(self, settings: KafkaSettings) -> None:
        self.startup_timeout = 20
        self.settings = settings
        self.started: asyncio.Future[bool] = None

    async def start(self) -> None:
        self.started = asyncio.get_running_loop().create_future()
        self.producer = aiokafka.AIOKafkaProducer(
            bootstrap_servers=self.settings.kafka_brokers,
            security_protocol=self.settings.kafka_security_protocol,
            ssl_context=create_ssl_context(),
            # compression_type='lz4',
            sasl_mechanism=self.settings.kafka_sasl_mechanism,
            # TODO: Does this work on AWS?
            sasl_plain_username=self.settings.kafka_username,
            sasl_plain_password=self.settings.kafka_password,
        )

        # Wait for kafka to start up and connect to it
        for i in range(self.startup_timeout):
            try:
                await self.producer.start()
                self.started.set_result(True)
                return
            except aiokafka.errors.KafkaConnectionError as e:
                logger.exception("Could not connect to kafka", exc_info=e)

            await asyncio.sleep(1)

        raise Exception("Could not connect to Kafka")

    async def stop(self) -> None:
        if self.started and self.started.done():
            await self.producer.stop()

    async def send(self, topic: str, payload: dict) -> None:
        if not self.started:
            raise Exception("Kafka producer not started")
        if not self.started.done():
            try:
                await asyncio.wait_for(self.started, timeout=self.startup_timeout)
            except asyncio.TimeoutError:
                raise Exception("Kafka producer not started")

        # TODO: Just .send() ?
        await self.producer.send_and_wait(topic, json.dumps(payload).encode("utf-8"))


@cache
def kafka_producer(settings: KafkaSettings = None) -> KafkaProducer:
    if settings is None:
        settings = KafkaSettings()
    return KafkaProducer(settings)
