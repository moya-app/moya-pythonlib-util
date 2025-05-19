# Use this file to test OTEL configuration. Use like:
#
#   OTEL_METRICS_EXPORTER=none OTEL_TRACES_EXPORTER=console uvicorn --workers=2 otel-test:app
#   curl http://127.0.0.1:8000/version
#
# And an OTEL dump of JSON should appear on the console after a few seconds.
from moya.util.fastapi import setup_fastapi

app = setup_fastapi()
