"""LangSmith integration helper for tracing agent execution."""
import logging
from typing import Optional

try:
    from langsmith import LangSmith
except ImportError:
    LangSmith = None

logger = logging.getLogger(__name__)


class LangSmithTracer:
    """Simple wrapper for LangSmith tracing."""

    def __init__(self, api_key: Optional[str] = None, project: str = "insurance-agent"):
        self.api_key = api_key
        self.project = project
        self.client = None

        if LangSmith is None:
            logger.warning("langsmith package not installed; LangSmith tracing disabled")
            return

        if self.api_key:
            self.client = LangSmith(api_key=self.api_key, project=self.project)
            logger.info("LangSmith tracer initialized")
        else:
            logger.warning("LANGSMITH_API_KEY not configured; LangSmith tracing disabled")

    def log_event(self, name: str, metadata: dict):
        if not self.client:
            return
        try:
            self.client.log_event(name=name, metadata=metadata)
        except Exception as exc:
            logger.error(f"LangSmith log event failed: {exc}")
