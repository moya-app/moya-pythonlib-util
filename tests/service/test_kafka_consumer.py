from unittest.mock import patch

from moya.service.kafka_consumer import KafkaConsumer, KafkaSettings
from moya.util.background import never_run_in_background

never_run_in_background(True)


def get_test_settings(**kwargs) -> KafkaSettings:
    return KafkaSettings(
        **{
            "kafka_sasl_mechanism": "PLAIN",
            "kafka_security_protocol": "SASL_SSL",
            "kafka_username": "test",
            "kafka_password": "test",
            "kafka_brokers": "localhost:9092",
            **kwargs,
        }
    )


async def test_kafka_consumer_library():
    k = KafkaConsumer(get_test_settings(), "test-group", ["test-topic1", "test-topic2"])

    with patch("aiokafka.AIOKafkaConsumer.start") as mock_start:
        await k.start()
        mock_start.assert_called_once()

    # TODO: Try .getone() and async for

    with patch("aiokafka.AIOKafkaConsumer.stop") as mock_stop:
        await k.stop()
        mock_stop.assert_called_once()

    # Check the new context manager functionality
    with patch("aiokafka.AIOKafkaConsumer.start") as mock_start, patch("aiokafka.AIOKafkaConsumer.stop") as mock_stop:
        async with k.run():
            mock_start.assert_called_once()
            mock_stop.assert_not_called()

        mock_stop.assert_called_once()


# TODO: Turn these into proper unit tests but for the moment make sure that mypy is happy at least
async def mypy_checks() -> None:
    k = KafkaConsumer(get_test_settings(), "test-group", ["test-topic1", "test-topic2"])
    async with k.run():
        await k.getone()

        async for msg in k:
            return
