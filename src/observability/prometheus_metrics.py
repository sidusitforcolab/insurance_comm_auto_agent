"""Prometheus metrics instrumentation for FastAPI."""
import logging

from prometheus_client import Counter, Histogram
from prometheus_fastapi_instrumentator import Instrumentator

logger = logging.getLogger(__name__)

UNDERWRITING_REQUESTS = Counter(
    "underwriting_requests_total",
    "Total number of underwriting requests",
    ["decision"]
)
PREMIUM_CALCULATION_DURATION = Histogram(
    "premium_calculation_duration_seconds",
    "Time spent calculating premium"
)
DOCUMENT_INGESTION_DURATION = Histogram(
    "document_ingestion_duration_seconds",
    "Time spent ingesting and processing documents"
)
API_ERRORS = Counter(
    "api_errors_total",
    "Total API errors",
    ["endpoint", "status_code"]
)


def setup_metrics(app):
    """Instrument FastAPI app with Prometheus metrics."""
    instrumentator = Instrumentator(
        should_group_status_codes=False,
        should_ignore_untemplated=True
    ).instrument(app).expose(app)
    logger.info("Prometheus instrumentation enabled")
    return instrumentator
