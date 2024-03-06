"""
Unfortunately, the opentelemetry-instrument command does not work with gunicorn
as documented in
https://opentelemetry-python.readthedocs.io/en/latest/examples/fork-process-model/README.html .
The below file is intended to be a trivial replacement that can be dropped in
to the gunicorn.conf.py file via:

    from moya.util.opentelemetry import post_fork
"""
import logging
import os

from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (  # ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor  # , ConsoleSpanExporter


# When running with gunicorn we can only set up opentelemetry after a process
# has been forked. This means that the opentelemetry-instrument command is not
# possible.
def post_fork(server, worker):  # type:ignore
    if "OTEL_SERVICE_NAME" in os.environ:
        resource = Resource.create(
            attributes={
                # Add some extra parameters in to help us track details in more depth
                "worker": worker.pid,
                "environment": os.environ["APP_ENVIRONMENT"],
            }
        )

        # The Exporters automatically pick up config from env vars which is quite nice
        trace.set_tracer_provider(TracerProvider(resource=resource))
        if "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT" in os.environ:
            span_processor = BatchSpanProcessor(OTLPSpanExporter())
            trace.get_tracer_provider().add_span_processor(span_processor)
        # else:
        #    span_processor = BatchSpanProcessor(ConsoleSpanExporter())

        if "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT" in os.environ:
            reader = PeriodicExportingMetricReader(OTLPMetricExporter())
            metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[reader]))
        # else:
        #    reader = PeriodicExportingMetricReader(ConsoleMetricExporter())

        if "OTEL_EXPORTER_OTLP_LOGS_ENDPOINT" in os.environ:
            logger_provider = LoggerProvider(resource=resource)
            set_logger_provider(logger_provider)
            logger_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
            logging.getLogger().addHandler(LoggingHandler(logger_provider=logger_provider))
            LoggingInstrumentor().instrument()
