"""EKS deployment helper for FastAPI services."""
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def generate_eks_manifest(service_name: str, image: str, replicas: int = 1) -> Dict[str, Any]:
    """Generate a simplified Kubernetes manifest for EKS."""
    manifest = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": service_name},
        "spec": {
            "replicas": replicas,
            "selector": {"matchLabels": {"app": service_name}},
            "template": {
                "metadata": {"labels": {"app": service_name}},
                "spec": {
                    "containers": [
                        {
                            "name": service_name,
                            "image": image,
                            "ports": [{"containerPort": 8000}],
                            "env": [
                                {"name": "DATABASE_URL", "value": "$(DATABASE_URL)"},
                                {"name": "AWS_REGION", "value": "$(AWS_REGION)"}
                            ]
                        }
                    ]
                }
            }
        }
    }
    logger.info(f"Generated EKS manifest for {service_name}")
    return manifest
