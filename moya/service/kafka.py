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
            # AWS requires SASL auth via the below
            "sasl_mechanism": self.kafka_sasl_mechanism,
            "security_protocol": self.kafka_security_protocol,
            "sasl_plain_username": self.kafka_username,
            "sasl_plain_password": self.kafka_password,
            "ssl_context": create_ssl_context(),
        }

    def as_kafka_producer(self) -> dict[str, t.Any]:
        return {
            **self.as_kafka(),
            "linger_ms": self.kafka_producer_linger_ms,
        }


class KafkaBase:
    kafka: t.Any  # aiokafka.AIOKafkaConsumer | aiokafka.AIOKafkaProducer

    def __init__(self, settings: KafkaSettings, startup_timeout: int = 20) -> None:
        self.startup_timeout = startup_timeout
        self.settings = settings
        self.started: asyncio.Future[bool] | None = None
        self.kafka = None

    async def _initialize(self) -> None:
        """
        Initialize the variables that require the current asyncio loop in order to work. Initializing aiokafka
        secretly records the currently running async loop internally. If not in an async context it will blow
        up, and when using pytest-asyncio it will break if used seveal times in different tests because a new
        loop is created in various parts of the test suite.
        """
        self.started = asyncio.get_running_loop().create_future()

    async def _start(self) -> None:
        """
        Start the kafka consumer/producer. This may block while connecting so can be run in the (async)
        background.
        """
        assert self.started is not None

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

    async def start(self) -> None:
        await self._initialize()
        await self._start()

    async def stop(self) -> None:
        if self.started and self.started.done():
            await self.kafka.stop()
            self.started = None

    @asynccontextmanager
    async def run(self) -> t.AsyncIterator[None]:
        """
        Context manager to easily run the kafka producer, starting up in the background and shutting down
        correctly.
        """
        await self._initialize()
        await run_in_background(self._start())
        try:
            yield
        finally:
            await self.stop()
