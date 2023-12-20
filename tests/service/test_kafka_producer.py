from unittest.mock import patch

import pytest

import moya.service.kafka_producer as kafka_producer


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


@pytest.mark.asyncio
@patch("asyncio.sleep")  # disable actually sleeping
async def test_kafka_bad_connection(mock_sleep):
    k = kafka_producer.KafkaProducer(get_test_settings())
    with pytest.raises(Exception, match="Kafka producer not started"):
        await k.send("test", {"test": "test"})

    with pytest.raises(Exception, match="Could not connect to Kafka"):
        await k.start()

    assert mock_sleep.call_count == 20, "Should have tried a number of times to connect"
    assert not k.started.done(), "Should have created the future but not completed it"

    k.startup_timeout = 0.1
    with pytest.raises(Exception, match="Kafka producer not started"):
        await k.send("test", {"test": "test"})

    # Should be a no-op
    await k.stop()


@pytest.mark.asyncio
async def test_kafka_producer_library():
    k = kafka_producer.KafkaProducer(get_test_settings())

    with patch("aiokafka.AIOKafkaProducer.start") as mock_start:
        await k.start()
        mock_start.assert_called_once()

    with patch("aiokafka.AIOKafkaProducer.send_and_wait") as mock_send:
        await k.send("test", {"test": "test"})
        mock_send.assert_called_once_with("test", b'{"test": "test"}')

    with patch("aiokafka.AIOKafkaProducer.stop"):
        await k.stop()
        mock_start.assert_called_once()


@pytest.mark.asyncio
async def test_kafka_producer_fn():
    k = kafka_producer.kafka_producer(get_test_settings())
    assert k.settings.kafka_brokers == "localhost:9092"
    k = kafka_producer.kafka_producer(get_test_settings(kafka_brokers="localhost:9093"))
    assert k.settings.kafka_brokers == "localhost:9093"
