import json
import typing as t
import uuid
from unittest.mock import patch

import pytest

import moya.service.kafka_producer as kafka_producer
from moya.util.background import never_run_in_background

never_run_in_background(True)


def get_test_settings(**kwargs) -> kafka_producer.KafkaSettings:
    return kafka_producer.KafkaSettings(
        **{
            "kafka_sasl_mechanism": "PLAIN",
            "kafka_security_protocol": "SASL_SSL",
            "kafka_username": "test",
            "kafka_password": "test",
            "kafka_brokers": "localhost:9092",
            **kwargs,
        }
    )


@patch("asyncio.sleep")  # disable actually sleeping
async def test_kafka_bad_connection(mock_sleep):
    k = kafka_producer.KafkaProducer(get_test_settings())
    with pytest.raises(Exception, match="Kafka producer not started"):
        await k.send("test", {"test": "test"})

    with pytest.raises(Exception, match="Timeout connecting to Kafka"):
        await k.start()

    assert mock_sleep.call_count == 20, "Should have tried a number of times to connect"
    assert not k.started.done(), "Should have created the future but not completed it"

    k.startup_timeout = 0.1
    with pytest.raises(Exception, match="Kafka producer not started"):
        await k.send("test", {"test": "test"})

    # Should be a no-op
    await k.stop()


async def test_kafka_producer_library():
    k = kafka_producer.KafkaProducer(get_test_settings())

    with patch("aiokafka.AIOKafkaProducer.start") as mock_start:
        await k.start()
        mock_start.assert_called_once()

    with patch("aiokafka.AIOKafkaProducer.send") as mock_send:
        await k.send("test", {"test": "test"})
        mock_send.assert_called_once_with("test", b'{"test": "test"}', timestamp_ms=None)

    with patch("aiokafka.AIOKafkaProducer.send") as mock_send:
        await k.send_nowait("test", {"test": "test"})
        mock_send.assert_called_once_with("test", b'{"test": "test"}', timestamp_ms=None)

    with patch("aiokafka.AIOKafkaProducer.stop") as mock_stop:
        await k.stop()
        mock_stop.assert_called_once()

    # Check the new context manager functionality
    with patch("aiokafka.AIOKafkaProducer.start") as mock_start, patch("aiokafka.AIOKafkaProducer.stop") as mock_stop:
        async with k.run():
            mock_start.assert_called_once()
            mock_stop.assert_not_called()

        mock_stop.assert_called_once()


async def test_kafka_producer_fn():
    k = kafka_producer.kafka_producer(get_test_settings())
    assert k.settings.kafka_brokers == "localhost:9092"
    k = kafka_producer.kafka_producer(get_test_settings(kafka_brokers="localhost:9093"))
    assert k.settings.kafka_brokers == "localhost:9093"


async def test_custom_encoder():
    k = kafka_producer.KafkaProducer(get_test_settings())

    with patch("aiokafka.AIOKafkaProducer.start") as mock_start:
        await k.start()
        mock_start.assert_called_once()

    class KafkaEncoder(json.JSONEncoder):
        """
        Custom JSON encodings for non-standard objects
        """

        def default(self, obj: t.Any) -> t.Any:
            if isinstance(obj, uuid.UUID):
                return str(obj)
            return json.JSONEncoder.default(self, obj)

    id = uuid.uuid4()
    with pytest.raises(TypeError, match=r"Object of type UUID is not JSON serializable"):
        await k.send("test", {"test": id})
    with pytest.raises(TypeError, match=r"Object of type UUID is not JSON serializable"):
        await k.send_nowait("test", {"test": id})

    with patch("aiokafka.AIOKafkaProducer.send") as mock_send:
        await k.send("test", {"test": id}, encoder=KafkaEncoder)
        mock_send.assert_called_once_with("test", f'{{"test": "{id}"}}'.encode(), timestamp_ms=None)

    with patch("aiokafka.AIOKafkaProducer.send") as mock_send:
        await k.send_nowait("test", {"test": id}, encoder=KafkaEncoder)
        mock_send.assert_called_once_with("test", f'{{"test": "{id}"}}'.encode(), timestamp_ms=None)

    with patch("aiokafka.AIOKafkaProducer.stop"):
        await k.stop()
        mock_start.assert_called_once()
