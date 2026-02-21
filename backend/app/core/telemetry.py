"""OpenTelemetry configuration for distributed tracing and metrics."""

from __future__ import annotations

from typing import TYPE_CHECKING

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from app.core.config import settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    from fastapi import FastAPI
    from sqlalchemy.ext.asyncio import AsyncEngine

logger = get_logger(__name__)


def configure_telemetry(app: "FastAPI", engine: "AsyncEngine | None" = None) -> None:
    """Instrument the application with OpenTelemetry.

    Args:
        app: The FastAPI application instance to instrument.
        engine: Optional async SQLAlchemy engine for DB tracing.
    """
    if not settings.OTEL_ENABLED:
        logger.info("OpenTelemetry disabled via OTEL_ENABLED=false")
        return

    resource = Resource.create(
        {
            "service.name": settings.OTEL_SERVICE_NAME,
            "service.version": settings.APP_VERSION,
            "deployment.environment": settings.ENVIRONMENT,
        }
    )

    provider = TracerProvider(resource=resource)

    # Choose exporter based on environment
    if settings.is_production and settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        headers: dict[str, str] = {}
        if settings.NEW_RELIC_LICENSE_KEY:
            headers["api-key"] = settings.NEW_RELIC_LICENSE_KEY

        span_exporter: OTLPSpanExporter | ConsoleSpanExporter = OTLPSpanExporter(
            endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
            headers=headers,
        )
        logger.info(
            "OTLP trace exporter configured",
            endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
        )
    else:
        span_exporter = ConsoleSpanExporter()
        logger.info("Console trace exporter configured (non-production)")

    provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(provider)

    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=provider,
        excluded_urls="/health,/ready,/metrics",
    )

    # Instrument SQLAlchemy
    if engine is not None:
        SQLAlchemyInstrumentor().instrument(
            engine=engine.sync_engine,
            tracer_provider=provider,
        )

    # Instrument Redis
    RedisInstrumentor().instrument(tracer_provider=provider)

    # Instrument Celery
    CeleryInstrumentor().instrument(tracer_provider=provider)

    logger.info(
        "OpenTelemetry configured",
        service=settings.OTEL_SERVICE_NAME,
        environment=settings.ENVIRONMENT,
    )
