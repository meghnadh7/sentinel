from __future__ import annotations
"""OpenTelemetry setup — instruments FastAPI, SQLAlchemy, Redis."""

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from sentinel.config import get_settings

settings = get_settings()

_tracer: trace.Tracer | None = None


def setup_tracing(app=None) -> None:
    resource = Resource.create({
        "service.name": "sentinel-api",
        "service.version": "1.0.0",
        "deployment.environment": settings.environment,
    })

    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    if app:
        FastAPIInstrumentor.instrument_app(app)

    SQLAlchemyInstrumentor().instrument()
    RedisInstrumentor().instrument()

    global _tracer
    _tracer = trace.get_tracer("sentinel")


def get_tracer() -> trace.Tracer:
    if _tracer is None:
        return trace.get_tracer("sentinel")
    return _tracer


def create_agent_span(
    agent_name: str,
    task_name: str,
    model_id: str | None = None,
    model_version: str | None = None,
    risk_tier: str | None = None,
    trigger: str = "on_demand",
):
    tracer = get_tracer()
    span_name = f"sentinel.{agent_name}.{task_name}"
    span = tracer.start_span(span_name)
    span.set_attribute("agent.name", agent_name)
    span.set_attribute("agent.task", task_name)
    span.set_attribute("audit.trigger", trigger)
    if model_id:
        span.set_attribute("model.id", model_id)
    if model_version:
        span.set_attribute("model.version", model_version)
    if risk_tier:
        span.set_attribute("model.risk_tier", risk_tier)
    return span
