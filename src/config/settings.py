"""Configuration settings for the insurance agent."""
import os
from typing import Optional

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # AWS Configuration
    aws_region: str = Field(default="us-east-1")
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None

    # Database Configuration
    database_url: str = Field(default="postgresql://postgres:password@localhost:5432/insurance_agent")

    # LLM Configuration
    bedrock_model_id: str = Field(default="anthropic.claude-3-sonnet-20240229-v1:0")
    anthropic_api_key: Optional[str] = None

    # Bing Search API
    bing_api_key: Optional[str] = None

    # DnB API
    dnb_api_key: Optional[str] = None

    # External tool integrations
    pinecone_api_key: Optional[str] = None
    pinecone_environment: Optional[str] = None
    tawily_api_key: Optional[str] = None
    sagemaker_endpoint_name: Optional[str] = None
    sagemaker_region: Optional[str] = Field(default="us-east-1")
    arize_api_key: Optional[str] = None
    ragas_api_key: Optional[str] = None

    # Observability
    langsmith_api_key: Optional[str] = None
    langsmith_project: str = Field(default="insurance-agent")
    prometheus_enabled: bool = Field(default=True)
    prometheus_metrics_path: str = Field(default="/metrics")

    # Security
    llama_guard_model: str = Field(default="meta-llama/LlamaGuard-7b")
    aws_waf_region: str = Field(default="us-east-1")
    aws_eks_cluster_name: Optional[str] = None
    aws_eks_namespace: str = Field(default="default")

    # Application Settings
    debug: bool = Field(default=True)
    log_level: str = Field(default="INFO")
    max_file_size_mb: int = Field(default=10)
    max_concurrent_requests: int = Field(default=10)

    # Premium calculation settings
    base_premium_by_vehicle: dict = Field(default={
        "sedan": 500.0,
        "truck": 1200.0,
        "van": 800.0,
        "fleet": 5000.0
    })

    premium_adjustment_rules: dict = Field(default={
        "claim_multiplier": 0.5,  # +50% per claim
        "serious_accident_multiplier": 1.0,  # +100% per serious accident
        "violation_multiplier": 0.25,  # +25% per violation
        "new_business_multiplier": 0.4,  # +40% for businesses < 1 year
        "young_business_multiplier": 0.2,  # +20% for businesses < 3 years
        "bing_negative_flag_multiplier": 0.5,  # +50% for negative Bing results
    })

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()