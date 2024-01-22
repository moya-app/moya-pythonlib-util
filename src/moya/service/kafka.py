import asyncio
import logging
import typing as t

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

    def as_kafka(self) -> dict:
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


class KafkaBase:
    def __init__(self, settings: KafkaSettings, startup_timeout: int = 20) -> None:
        self.startup_timeout = startup_timeout
        self.settings = settings
        self.started: asyncio.Future[bool] = None
        self.kafka: t.Any = None  # should be AIOKafkaProducer or AIOKafkaConsumer

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
