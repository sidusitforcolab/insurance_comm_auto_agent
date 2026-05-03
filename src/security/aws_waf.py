"""AWS WAF / web application firewall helper stub."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AwsWafManager:
    """Stub helper for AWS WAF configuration and rules."""

    def __init__(self, region_name: str = "us-east-1", api_key: Optional[str] = None):
        self.region_name = region_name
        self.api_key = api_key

    def get_recommendations(self) -> dict:
        """Return placeholder WAF configuration recommendations."""
        logger.info("Returning AWS WAF placeholder recommendations")
        return {
            "recommended_rules": [
                "SQL injection protection",
                "Cross-site scripting protection",
                "Rate limiting",
                "Bad bot prevention"
            ],
            "notes": "Implement AWS WAF via API Gateway or AWS console for production"
        }
