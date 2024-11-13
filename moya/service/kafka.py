import asyncio
import logging
import typing as t
from contextlib import asynccontextmanager

import aiokafka
from aiokafka.helpers import create_ssl_context

from moya.util.background import run_in_background
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

    kafka_producer_linger_ms: int = 200  # 200ms batches to improve send performance (producer-only)

    def as_kafka(self) -> dict[str, t.Any]:
        "Return settings as a dict suitable for passing to aiokafka"

        return {
            "bootstrap_servers": self.kafka_brokers,
            "linger_ms": self.kafka_producer_linger_ms,
            # AWS requires SASL auth via the below
            "sasl_mechanism": self.kafka_sasl_mechanism,
            "security_protocol": self.kafka_security_protocol,
            "sasl_plain_username": self.kafka_username,
            "sasl_plain_password": self.kafka_password,
            "ssl_context": create_ssl_context(),
        }


class KafkaBase:
    def __init__(self, settings: KafkaSettings, startup_timeout: int = 20) -> None:
        self.startup_timeout = startup_timeout
        self.settings = settings
        self.started: asyncio.Future[bool] | None = None
        self.kafka: t.Any = None  # aiokafka.AIOKafkaConsumer | aiokafka.AIOKafkaProducer | None = None

    async def start(self) -> None:
        self.started = asyncio.get_running_loop().create_future()

        # Wait for kafka to start up and connect to it
        for i in range(self.startup_timeout):
            try:
                await self.kafka.start()
                self.started.set_result(True)
                return
            except aiokafka.errors.KafkaConnectionError as e:
                logger.exception("Could not connect to kafka", exc_info=e)

            await asyncio.sleep(1)

        raise Exception("Timeout connecting to Kafka")

    async def stop(self) -> None:
        if self.started and self.started.done():
            await self.kafka.stop()
            self.started = None
            self.kafka = None

    @asynccontextmanager
    async def run(self, **kwargs: t.Any) -> t.AsyncIterator[None]:
        """
        Context manager to easily run the kafka producer in the background and handle shutdown correctly.
        """
        await run_in_background(self.start(**kwargs))
        try:
            yield
        finally:
            await self.stop()
