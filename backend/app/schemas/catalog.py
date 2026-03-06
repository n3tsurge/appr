"""Pydantic schemas for all catalog entity types."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import (
    ComponentType,
    EntityStatus,
    ImpactType,
    IncidentSeverity,
    IncidentStatus,
    OperationalStatus,
    RepositoryProvider,
    ResourceType,
    ServiceType,
)


# ---------------------------------------------------------------------------
# Service schemas
# ---------------------------------------------------------------------------


class ServiceCreate(BaseModel):
    """Payload for creating a new service."""

    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=100)
    description: str | None = None
    service_type: ServiceType = ServiceType.api
    status: EntityStatus = EntityStatus.active
    operational_status: OperationalStatus = OperationalStatus.operational
    owner_team_id: uuid.UUID | None = None
    owner_person_id: uuid.UUID | None = None
    tier: int | None = None
    pagerduty_service_id: str | None = None
    datadog_service_name: str | None = None
    runbook_url: str | None = None
    dashboard_url: str | None = None
    slo_target: float | None = None
    attributes: dict = Field(default_factory=dict)
    tags: list = Field(default_factory=list)
    external_id: str | None = None


class ServiceUpdate(BaseModel):
    """Payload for updating an existing service. All fields optional."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    service_type: ServiceType | None = None
    status: EntityStatus | None = None
    operational_status: OperationalStatus | None = None
    owner_team_id: uuid.UUID | None = None
    owner_person_id: uuid.UUID | None = None
    tier: int | None = None
    pagerduty_service_id: str | None = None
    datadog_service_name: str | None = None
    runbook_url: str | None = None
    dashboard_url: str | None = None
    slo_target: float | None = None
    attributes: dict | None = None
    tags: list | None = None
    external_id: str | None = None


class ServiceRead(BaseModel):
    """Full service representation with all fields and timestamps."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    slug: str
    description: str | None = None
    service_type: ServiceType
    status: EntityStatus
    operational_status: OperationalStatus
    owner_team_id: uuid.UUID | None = None
    owner_person_id: uuid.UUID | None = None
    tier: int | None = None
    pagerduty_service_id: str | None = None
    datadog_service_name: str | None = None
    runbook_url: str | None = None
    dashboard_url: str | None = None
    slo_target: float | None = None
    attributes: dict
    tags: list
    external_id: str | None = None
    created_at: datetime
    updated_at: datetime
    created_by: uuid.UUID | None = None
    updated_by: uuid.UUID | None = None

    model_config = {"from_attributes": True}


class ServiceListItem(BaseModel):
    """Abbreviated service representation for list responses."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    slug: str
    service_type: ServiceType
    status: EntityStatus
    operational_status: OperationalStatus
    owner_team_id: uuid.UUID | None = None
    tier: int | None = None
    tags: list
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Component schemas
# ---------------------------------------------------------------------------


class ComponentCreate(BaseModel):
    """Payload for creating a new component."""

    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=100)
    description: str | None = None
    component_type: ComponentType = ComponentType.library
    status: EntityStatus = EntityStatus.active
    owner_team_id: uuid.UUID | None = None
    owner_person_id: uuid.UUID | None = None
    language: str | None = None
    version: str | None = None
    package_name: str | None = None
    attributes: dict = Field(default_factory=dict)
    tags: list = Field(default_factory=list)
    external_id: str | None = None


class ComponentUpdate(BaseModel):
    """Payload for updating an existing component. All fields optional."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    component_type: ComponentType | None = None
    status: EntityStatus | None = None
    owner_team_id: uuid.UUID | None = None
    owner_person_id: uuid.UUID | None = None
    language: str | None = None
    version: str | None = None
    package_name: str | None = None
    attributes: dict | None = None
    tags: list | None = None
    external_id: str | None = None


class ComponentRead(BaseModel):
    """Full component representation with all fields and timestamps."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    slug: str
    description: str | None = None
    component_type: ComponentType
    status: EntityStatus
    owner_team_id: uuid.UUID | None = None
    owner_person_id: uuid.UUID | None = None
    language: str | None = None
    version: str | None = None
    package_name: str | None = None
    attributes: dict
    tags: list
    external_id: str | None = None
    created_at: datetime
    updated_at: datetime
    created_by: uuid.UUID | None = None
    updated_by: uuid.UUID | None = None

    model_config = {"from_attributes": True}


class ComponentListItem(BaseModel):
    """Abbreviated component representation for list responses."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    slug: str
    component_type: ComponentType
    status: EntityStatus
    owner_team_id: uuid.UUID | None = None
    language: str | None = None
    tags: list
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Product schemas
# ---------------------------------------------------------------------------


class ProductCreate(BaseModel):
    """Payload for creating a new product."""

    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=100)
    description: str | None = None
    status: EntityStatus = EntityStatus.active
    owner_team_id: uuid.UUID | None = None
    owner_person_id: uuid.UUID | None = None
    tier: int | None = None
    tags: list = Field(default_factory=list)
    external_id: str | None = None


class ProductUpdate(BaseModel):
    """Payload for updating an existing product. All fields optional."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    status: EntityStatus | None = None
    owner_team_id: uuid.UUID | None = None
    owner_person_id: uuid.UUID | None = None
    tier: int | None = None
    tags: list | None = None
    external_id: str | None = None


class ProductRead(BaseModel):
    """Full product representation with all fields and timestamps."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    slug: str
    description: str | None = None
    status: EntityStatus
    owner_team_id: uuid.UUID | None = None
    owner_person_id: uuid.UUID | None = None
    tier: int | None = None
    tags: list
    external_id: str | None = None
    created_at: datetime
    updated_at: datetime
    created_by: uuid.UUID | None = None
    updated_by: uuid.UUID | None = None

    model_config = {"from_attributes": True}


class ProductListItem(BaseModel):
    """Abbreviated product representation for list responses."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    slug: str
    status: EntityStatus
    owner_team_id: uuid.UUID | None = None
    tier: int | None = None
    tags: list
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Team schemas
# ---------------------------------------------------------------------------


class TeamCreate(BaseModel):
    """Payload for creating a new team."""

    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=100)
    description: str | None = None
    email: str | None = None
    slack_channel: str | None = None
    parent_team_id: uuid.UUID | None = None


class TeamUpdate(BaseModel):
    """Payload for updating an existing team. All fields optional."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    email: str | None = None
    slack_channel: str | None = None
    parent_team_id: uuid.UUID | None = None


class TeamRead(BaseModel):
    """Full team representation with all fields and timestamps."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    slug: str
    description: str | None = None
    email: str | None = None
    slack_channel: str | None = None
    parent_team_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
    created_by: uuid.UUID | None = None
    updated_by: uuid.UUID | None = None

    model_config = {"from_attributes": True}


class TeamListItem(BaseModel):
    """Abbreviated team representation for list responses."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    slug: str
    email: str | None = None
    slack_channel: str | None = None
    parent_team_id: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Person schemas
# ---------------------------------------------------------------------------


class PersonCreate(BaseModel):
    """Payload for creating a new person directory record."""

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    display_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    title: str | None = None
    department: str | None = None
    location: str | None = None
    manager_id: uuid.UUID | None = None
    team_id: uuid.UUID | None = None
    slack_user_id: str | None = None
    github_username: str | None = None
    external_hr_id: str | None = None
    is_active: bool = True


class PersonUpdate(BaseModel):
    """Payload for updating an existing person. All fields optional."""

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    title: str | None = None
    department: str | None = None
    location: str | None = None
    manager_id: uuid.UUID | None = None
    team_id: uuid.UUID | None = None
    slack_user_id: str | None = None
    github_username: str | None = None
    external_hr_id: str | None = None
    is_active: bool | None = None


class PersonRead(BaseModel):
    """Full person representation with all fields and timestamps."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    first_name: str
    last_name: str
    display_name: str
    email: str
    title: str | None = None
    department: str | None = None
    location: str | None = None
    manager_id: uuid.UUID | None = None
    team_id: uuid.UUID | None = None
    slack_user_id: str | None = None
    github_username: str | None = None
    external_hr_id: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: uuid.UUID | None = None
    updated_by: uuid.UUID | None = None

    model_config = {"from_attributes": True}


class PersonListItem(BaseModel):
    """Abbreviated person representation for list responses."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    first_name: str
    last_name: str
    display_name: str
    email: str
    title: str | None = None
    department: str | None = None
    team_id: uuid.UUID | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Repository schemas
# ---------------------------------------------------------------------------


class RepositoryCreate(BaseModel):
    """Payload for creating a new repository record."""

    name: str = Field(min_length=1, max_length=255)
    full_name: str = Field(min_length=1, max_length=512)
    description: str | None = None
    provider: RepositoryProvider
    clone_url: str | None = None
    html_url: str | None = None
    default_branch: str = "main"
    is_private: bool = True
    is_archived: bool = False
    language: str | None = None
    external_id: str | None = None


class RepositoryUpdate(BaseModel):
    """Payload for updating an existing repository. All fields optional."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    full_name: str | None = Field(default=None, min_length=1, max_length=512)
    description: str | None = None
    provider: RepositoryProvider | None = None
    clone_url: str | None = None
    html_url: str | None = None
    default_branch: str | None = None
    is_private: bool | None = None
    is_archived: bool | None = None
    language: str | None = None
    external_id: str | None = None


class RepositoryRead(BaseModel):
    """Full repository representation with all fields and timestamps."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    full_name: str
    description: str | None = None
    provider: RepositoryProvider
    clone_url: str | None = None
    html_url: str | None = None
    default_branch: str
    is_private: bool
    is_archived: bool
    language: str | None = None
    external_id: str | None = None
    created_at: datetime
    updated_at: datetime
    created_by: uuid.UUID | None = None
    updated_by: uuid.UUID | None = None

    model_config = {"from_attributes": True}


class RepositoryListItem(BaseModel):
    """Abbreviated repository representation for list responses."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    full_name: str
    provider: RepositoryProvider
    default_branch: str
    is_private: bool
    is_archived: bool
    language: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Resource schemas
# ---------------------------------------------------------------------------


class ResourceCreate(BaseModel):
    """Payload for creating a new cloud/infrastructure resource."""

    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=100)
    description: str | None = None
    resource_type: ResourceType
    status: EntityStatus = EntityStatus.active
    cloud_provider: str | None = None
    region: str | None = None
    account_id: str | None = None
    resource_id: str | None = None
    owner_team_id: uuid.UUID | None = None
    attributes: dict = Field(default_factory=dict)
    tags: list = Field(default_factory=list)
    external_id: str | None = None


class ResourceUpdate(BaseModel):
    """Payload for updating an existing resource. All fields optional."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    resource_type: ResourceType | None = None
    status: EntityStatus | None = None
    cloud_provider: str | None = None
    region: str | None = None
    account_id: str | None = None
    resource_id: str | None = None
    owner_team_id: uuid.UUID | None = None
    attributes: dict | None = None
    tags: list | None = None
    external_id: str | None = None


class ResourceRead(BaseModel):
    """Full resource representation with all fields and timestamps."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    slug: str
    description: str | None = None
    resource_type: ResourceType
    status: EntityStatus
    cloud_provider: str | None = None
    region: str | None = None
    account_id: str | None = None
    resource_id: str | None = None
    owner_team_id: uuid.UUID | None = None
    attributes: dict
    tags: list
    external_id: str | None = None
    created_at: datetime
    updated_at: datetime
    created_by: uuid.UUID | None = None
    updated_by: uuid.UUID | None = None

    model_config = {"from_attributes": True}


class ResourceListItem(BaseModel):
    """Abbreviated resource representation for list responses."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    slug: str
    resource_type: ResourceType
    status: EntityStatus
    cloud_provider: str | None = None
    region: str | None = None
    owner_team_id: uuid.UUID | None = None
    tags: list
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Incident schemas
# ---------------------------------------------------------------------------


class IncidentCreate(BaseModel):
    """Payload for creating a new incident."""

    title: str = Field(min_length=1, max_length=512)
    description: str | None = None
    severity: IncidentSeverity
    status: IncidentStatus = IncidentStatus.investigating
    incident_commander_id: uuid.UUID | None = None
    detected_at: datetime | None = None
    acknowledged_at: datetime | None = None
    slack_channel: str | None = None
    pagerduty_incident_id: str | None = None
    postmortem_url: str | None = None
    attributes: dict = Field(default_factory=dict)


class IncidentUpdate(BaseModel):
    """Payload for updating an existing incident. All fields optional."""

    title: str | None = Field(default=None, min_length=1, max_length=512)
    description: str | None = None
    severity: IncidentSeverity | None = None
    status: IncidentStatus | None = None
    incident_commander_id: uuid.UUID | None = None
    detected_at: datetime | None = None
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    slack_channel: str | None = None
    pagerduty_incident_id: str | None = None
    postmortem_url: str | None = None
    attributes: dict | None = None


class IncidentRead(BaseModel):
    """Full incident representation with all fields and timestamps."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    title: str
    description: str | None = None
    severity: IncidentSeverity
    status: IncidentStatus
    incident_commander_id: uuid.UUID | None = None
    detected_at: datetime | None = None
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    slack_channel: str | None = None
    pagerduty_incident_id: str | None = None
    postmortem_url: str | None = None
    attributes: dict
    created_at: datetime
    updated_at: datetime
    created_by: uuid.UUID | None = None
    updated_by: uuid.UUID | None = None

    model_config = {"from_attributes": True}


class IncidentListItem(BaseModel):
    """Abbreviated incident representation for list responses."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    title: str
    severity: IncidentSeverity
    status: IncidentStatus
    incident_commander_id: uuid.UUID | None = None
    detected_at: datetime | None = None
    resolved_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class IncidentTimelineEntryCreate(BaseModel):
    """Payload for adding a timeline entry to an incident."""

    occurred_at: datetime
    entry_type: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1)
    author_id: uuid.UUID | None = None


class IncidentTimelineEntryRead(BaseModel):
    """Timeline entry representation."""

    id: uuid.UUID
    incident_id: uuid.UUID
    occurred_at: datetime
    entry_type: str
    message: str
    author_id: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class IncidentResolveRequest(BaseModel):
    """Payload for resolving an incident."""

    resolved_at: datetime | None = None
    postmortem_url: str | None = None
    resolution_note: str | None = None


# ---------------------------------------------------------------------------
# Scorecard schemas
# ---------------------------------------------------------------------------


class ScorecardCriterionCreate(BaseModel):
    """Payload for creating a scorecard criterion."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    weight: int = Field(default=1, ge=1)
    rule_type: str = Field(min_length=1, max_length=100)
    rule_config: dict = Field(default_factory=dict)
    sort_order: int = 0
    is_active: bool = True


class ScorecardCriterionRead(BaseModel):
    """Scorecard criterion representation."""

    id: uuid.UUID
    scorecard_id: uuid.UUID
    name: str
    description: str | None = None
    weight: int
    rule_type: str
    rule_config: dict
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScorecardCreate(BaseModel):
    """Payload for creating a new scorecard."""

    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=100)
    description: str | None = None
    entity_type: str = Field(min_length=1, max_length=50)
    is_active: bool = True
    passing_threshold: int = Field(default=70, ge=0, le=100)
    criteria: list[ScorecardCriterionCreate] = Field(default_factory=list)


class ScorecardUpdate(BaseModel):
    """Payload for updating an existing scorecard. All fields optional."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    entity_type: str | None = Field(default=None, min_length=1, max_length=50)
    is_active: bool | None = None
    passing_threshold: int | None = Field(default=None, ge=0, le=100)


class ScorecardRead(BaseModel):
    """Full scorecard representation with criteria and timestamps."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    slug: str
    description: str | None = None
    entity_type: str
    is_active: bool
    passing_threshold: int
    created_at: datetime
    updated_at: datetime
    created_by: uuid.UUID | None = None
    updated_by: uuid.UUID | None = None

    model_config = {"from_attributes": True}


class ScorecardListItem(BaseModel):
    """Abbreviated scorecard representation for list responses."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    slug: str
    entity_type: str
    is_active: bool
    passing_threshold: int
    created_at: datetime

    model_config = {"from_attributes": True}


__all__ = [
    # Service
    "ServiceCreate",
    "ServiceUpdate",
    "ServiceRead",
    "ServiceListItem",
    # Component
    "ComponentCreate",
    "ComponentUpdate",
    "ComponentRead",
    "ComponentListItem",
    # Product
    "ProductCreate",
    "ProductUpdate",
    "ProductRead",
    "ProductListItem",
    # Team
    "TeamCreate",
    "TeamUpdate",
    "TeamRead",
    "TeamListItem",
    # Person
    "PersonCreate",
    "PersonUpdate",
    "PersonRead",
    "PersonListItem",
    # Repository
    "RepositoryCreate",
    "RepositoryUpdate",
    "RepositoryRead",
    "RepositoryListItem",
    # Resource
    "ResourceCreate",
    "ResourceUpdate",
    "ResourceRead",
    "ResourceListItem",
    # Incident
    "IncidentCreate",
    "IncidentUpdate",
    "IncidentRead",
    "IncidentListItem",
    "IncidentTimelineEntryCreate",
    "IncidentTimelineEntryRead",
    "IncidentResolveRequest",
    # Scorecard
    "ScorecardCreate",
    "ScorecardUpdate",
    "ScorecardRead",
    "ScorecardListItem",
    "ScorecardCriterionCreate",
    "ScorecardCriterionRead",
]
