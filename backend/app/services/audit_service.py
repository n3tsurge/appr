"""AuditService – structured event logging to the audit_logs table (TPRD-012)."""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

logger = structlog.get_logger(__name__)


class AuditService:
    """Records immutable audit events to the ``audit_logs`` table.

    Per TPRD-012 requirements every create, update, and delete operation must
    be recorded with before/after snapshots. System events (scheduled jobs,
    webhooks) use ``actor_type="system"`` with a ``None`` actor_id.

    Usage::

        audit = AuditService(db)
        await audit.log(
            tenant_id=tenant_id,
            event_type="service.created",
            actor_id=current_user.id,
            entity_type="Service",
            entity_id=service.id,
            after=service_dict,
            request_id=request.state.request_id,
        )
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def log(
        self,
        *,
        tenant_id: uuid.UUID,
        event_type: str,
        actor_id: uuid.UUID | None = None,
        actor_type: str = "user",
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
    ) -> AuditLog:
        """Persist a single audit event.

        Args:
            tenant_id: Tenant scope of the event.
            event_type: Dot-notation event name (e.g. ``service.created``).
            actor_id: UUID of the user who triggered the event; None for system.
            actor_type: ``"user"`` or ``"system"`` (default ``"user"``).
            entity_type: SQLAlchemy model class name (e.g. ``"Service"``).
            entity_id: Primary key of the affected entity.
            before: JSON-serialisable snapshot before the change.
            after: JSON-serialisable snapshot after the change.
            metadata: Additional structured context (reason, diff summary, etc.).
            ip_address: Client IP address (IPv4 or IPv6).
            user_agent: HTTP User-Agent string.
            request_id: Correlation ID from ``X-Request-ID`` header.

        Returns:
            The persisted ``AuditLog`` instance (already added to the session).
        """
        entry = AuditLog(
            tenant_id=tenant_id,
            event_type=event_type,
            actor_id=actor_id,
            actor_type=actor_type,
            entity_type=entity_type,
            entity_id=entity_id,
            before=before,
            after=after,
            metadata_=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )
        self._db.add(entry)

        logger.info(
            "audit event recorded",
            event_type=event_type,
            actor_id=str(actor_id) if actor_id else None,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            request_id=request_id,
        )

        return entry

    async def log_login(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        auth_provider: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
    ) -> AuditLog:
        """Convenience helper for recording authentication events."""
        return await self.log(
            tenant_id=tenant_id,
            event_type="user.login",
            actor_id=user_id,
            entity_type="User",
            entity_id=user_id,
            metadata={"auth_provider": auth_provider},
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

    async def log_logout(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
    ) -> AuditLog:
        """Convenience helper for recording logout events."""
        return await self.log(
            tenant_id=tenant_id,
            event_type="user.logout",
            actor_id=user_id,
            entity_type="User",
            entity_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )


__all__ = ["AuditService"]
