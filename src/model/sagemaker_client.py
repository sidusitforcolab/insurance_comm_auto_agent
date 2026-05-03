"""AWS SageMaker client for model hosting and inference."""
import logging
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)


class SageMakerClient:
    """Client helper for AWS SageMaker endpoint invocation."""

    def __init__(self, region_name: str = "us-east-1"):
        self.client = boto3.client("sagemaker-runtime", region_name=region_name)

    def invoke_text_model(self, endpoint_name: str, payload: str, content_type: str = "application/json") -> Optional[str]:
        """Invoke a SageMaker text inference endpoint."""
        try:
            response = self.client.invoke_endpoint(
                EndpointName=endpoint_name,
                ContentType=content_type,
                Body=payload.encode("utf-8")
            )
            result = response.get("Body")
            if not result:
                return None
            text = result.read().decode("utf-8")
            return text
        except (BotoCoreError, ClientError) as exc:
            logger.error(f"SageMaker endpoint invocation failed: {exc}")
            return None
