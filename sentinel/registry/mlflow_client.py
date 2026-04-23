from __future__ import annotations
import io
import pickle
from typing import Any

import mlflow
import mlflow.sklearn
import mlflow.xgboost
from mlflow.tracking import MlflowClient

from sentinel.config import get_settings

settings = get_settings()


class SentinelMLflowClient:
    def __init__(self) -> None:
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        self.client = MlflowClient(tracking_uri=settings.mlflow_tracking_uri)

    def register_model(
        self,
        model_name: str,
        run_id: str,
        artifact_path: str = "model",
        tags: dict[str, str] | None = None,
    ) -> str:
        model_uri = f"runs:/{run_id}/{artifact_path}"
        result = mlflow.register_model(model_uri, model_name)
        if tags:
            for k, v in tags.items():
                self.client.set_model_version_tag(model_name, result.version, k, v)
        return result.version

    def get_model_versions(self, model_name: str) -> list[dict[str, Any]]:
        versions = self.client.search_model_versions(f"name='{model_name}'")
        return [
            {
                "name": v.name,
                "version": v.version,
                "run_id": v.run_id,
                "status": v.status,
                "tags": v.tags,
            }
            for v in versions
        ]

    def load_model_for_sandbox(self, model_name: str, version: str) -> Any:
        """Load a model copy for sandboxed red-team testing."""
        model_uri = f"models:/{model_name}/{version}"
        try:
            return mlflow.sklearn.load_model(model_uri)
        except Exception:
            try:
                return mlflow.xgboost.load_model(model_uri)
            except Exception:
                return mlflow.pyfunc.load_model(model_uri)

    def log_fairness_artifact(
        self, run_id: str, model_id: str, metrics: dict[str, Any]
    ) -> None:
        with mlflow.start_run(run_id=run_id):
            for k, v in metrics.items():
                if isinstance(v, (int, float)):
                    mlflow.log_metric(f"fairness_{k}", v)

    def log_shap_artifact(
        self, run_id: str, feature_importance: dict[str, float]
    ) -> None:
        with mlflow.start_run(run_id=run_id):
            for feature, importance in feature_importance.items():
                mlflow.log_metric(f"shap_{feature}", importance)

    def create_experiment(self, name: str, tags: dict[str, str] | None = None) -> str:
        experiment = self.client.get_experiment_by_name(name)
        if experiment:
            return experiment.experiment_id
        return self.client.create_experiment(name, tags=tags or {})

    def start_run(
        self,
        experiment_name: str,
        run_name: str,
        tags: dict[str, str] | None = None,
    ) -> mlflow.ActiveRun:
        exp_id = self.create_experiment(experiment_name)
        return mlflow.start_run(experiment_id=exp_id, run_name=run_name, tags=tags or {})

    def list_registered_models(self) -> list[dict[str, Any]]:
        models = self.client.search_registered_models()
        return [
            {
                "name": m.name,
                "tags": m.tags,
                "latest_versions": [
                    {"version": v.version, "run_id": v.run_id, "status": v.status}
                    for v in m.latest_versions
                ],
            }
            for m in models
        ]
