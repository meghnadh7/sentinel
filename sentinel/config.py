from __future__ import annotations
from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    environment: Literal["development", "staging", "production"] = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    prometheus_port: int = 8001

    # LLM
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    use_local_embeddings: bool = True
    use_mock_llm: bool = False

    # LangSmith
    langchain_api_key: str = ""
    langchain_tracing_v2: bool = True
    langchain_project: str = "sentinel"

    # MySQL
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "sentinel"
    mysql_password: str = "sentinel_dev"
    mysql_database: str = "sentinel_db"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # MLflow
    mlflow_tracking_uri: str = "http://localhost:5000"

    # Slack
    slack_webhook_url: str = ""
    slack_audit_channel: str = "#sentinel-alerts"
    hitl_approval_timeout_seconds: int = 86400  # 24 hours

    # AWS
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    s3_bucket: str = "sentinel-artifacts"

    # Observability
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"

    # Audit thresholds
    fairness_demographic_parity_threshold: float = 0.80
    fairness_watch_threshold: float = 0.85
    fairness_min_subgroup_size: int = 200
    shap_stability_threshold: float = 0.85
    red_team_success_rate_threshold: float = 0.10
    doc_completeness_threshold: float = 0.90

    # Agent limits
    agent_max_tool_calls: int = 10
    agent_max_output_tokens: int = 4096
    agent_max_cost_dollars: float = 5.00
    red_team_budget_dollars: float = 500.0
    red_team_max_iterations: int = 10000

    # RAG
    rag_index_persist_dir: str = "./data/rag_index"
    rag_chunk_size: int = 512
    rag_chunk_overlap: int = 50

    @computed_field
    @property
    def mysql_async_url(self) -> str:
        return (
            f"mysql+asyncmy://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )

    @computed_field
    @property
    def mysql_sync_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )

    @computed_field
    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
