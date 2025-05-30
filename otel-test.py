# Use this file to test OTEL configuration. Use like:
#
#   OTEL_SERVICE_NAME=test OTEL_TRACES_EXPORTER=console OTEL_PYTHON_LOG_CORRELATION=true OTEL_LOGS_EXPORTER=console OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED=true OTEL_PYTHON_LOG_LEVEL=info uvicorn --workers=2 otel-test:app --reload # noqa
#
#   curl http://127.0.0.1:8000/version
#   curl http://127.0.0.1:8000/log
#
# And an OTEL dump of JSON should appear on the console after a few seconds.
import logging

from moya.util.fastapi import setup_fastapi
from moya.util.logging import setup_logging

logger = logging.getLogger(__name__)

setup_logging()
app = setup_fastapi()


@app.get("/log")
async def log() -> str:
    rootlogger = logging.getLogger()
    print(rootlogger)
    for h in rootlogger.handlers:
        print(type(h))
        print(h)

    logger.debug("debug")
    logger.info("info")
    logger.warning("warning")
    logger.error("error")
    return "OK"
