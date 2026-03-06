"""OpenTelemetry configuration for distributed tracing and metrics."""

from __future__ import annotations

import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.semconv.resource import ResourceAttributes

from app.core.config import settings

logger = structlog.get_logger(__name__)

_tracer_provider: TracerProvider | None = None


def configure_telemetry(app: object, engine: object | None = None) -> None:  # noqa: ANN401
    """Bootstrap OpenTelemetry instrumentation.

    Instruments:
    - FastAPI (HTTP server spans)
    - SQLAlchemy (database query spans)
    - Redis (cache operation spans)
    - Celery (task spans)

    Exports traces to the configured OTLP endpoint (New Relic by default).
    Falls back to a console exporter when the endpoint is not configured.

    Args:
        app: The FastAPI application instance.
        engine: Optional SQLAlchemy async engine for SQLAlchemy instrumentation.
    """
    global _tracer_provider  # noqa: PLW0603

    resource = Resource.create(
        {
            ResourceAttributes.SERVICE_NAME: settings.OTEL_SERVICE_NAME,
            ResourceAttributes.SERVICE_VERSION: settings.APP_VERSION,
            ResourceAttributes.DEPLOYMENT_ENVIRONMENT: settings.ENVIRONMENT,
        }
    )

    provider = TracerProvider(resource=resource)

    if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        headers: dict[str, str] = {}
        if settings.NEW_RELIC_LICENSE_KEY:
            headers["api-key"] = settings.NEW_RELIC_LICENSE_KEY

        otlp_exporter = OTLPSpanExporter(
            endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
            headers=headers,
            insecure=not settings.is_production,
        )
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        logger.info(
            "otel otlp exporter configured",
            endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
        )
    else:
        # Development fallback: print spans to stdout
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        logger.info("otel console exporter configured (no OTLP endpoint set)")

    trace.set_tracer_provider(provider)
    _tracer_provider = provider

    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(
        app,  # type: ignore[arg-type]
        tracer_provider=provider,
        excluded_urls="health,ready",
    )

    # Instrument SQLAlchemy (bind to engine if provided)
    if engine is not None:
        SQLAlchemyInstrumentor().instrument(
            engine=engine.sync_engine,  # type: ignore[union-attr]
            tracer_provider=provider,
        )
    else:
        SQLAlchemyInstrumentor().instrument(tracer_provider=provider)

    # Instrument Redis
    RedisInstrumentor().instrument(tracer_provider=provider)

    # Instrument Celery
    CeleryInstrumentor().instrument(tracer_provider=provider)

    logger.info("opentelemetry instrumentation configured")


def get_tracer(name: str = __name__) -> trace.Tracer:
    """Return a tracer from the configured provider."""
    provider = _tracer_provider or trace.get_tracer_provider()
    return provider.get_tracer(name)


def shutdown_telemetry() -> None:
    """Flush and shut down the tracer provider on application exit."""
    if _tracer_provider is not None:
        _tracer_provider.shutdown()
        logger.info("opentelemetry shut down")


__all__ = ["configure_telemetry", "get_tracer", "shutdown_telemetry"]
