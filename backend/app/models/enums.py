"""Domain enumerations for the AppR inventory system."""

from __future__ import annotations

import enum


class EntityStatus(str, enum.Enum):
    """Lifecycle status of an inventory entity."""

    active = "active"
    planned = "planned"
    maintenance = "maintenance"
    deprecated = "deprecated"


class OperationalStatus(str, enum.Enum):
    """Real-time operational health of a service or component."""

    operational = "operational"
    degraded = "degraded"
    outage = "outage"


class ServiceType(str, enum.Enum):
    """Category of a service within the application inventory."""

    api = "api"
    web_application = "web_application"
    database = "database"
    message_queue = "message_queue"
    cache = "cache"
    infrastructure = "infrastructure"


class ComponentType(str, enum.Enum):
    """Category of a software component."""

    library = "library"
    microservice = "microservice"
    sdk = "sdk"
    agent = "agent"
    ui_component = "ui_component"


class ResourceType(str, enum.Enum):
    """Cloud or infrastructure resource type."""

    ec2 = "ec2"
    virtual_machine = "virtual_machine"
    logic_app = "logic_app"
    storage_account = "storage_account"
    container_instance = "container_instance"
    kubernetes = "kubernetes"
    function_app = "function_app"
    load_balancer = "load_balancer"
    api_gateway = "api_gateway"
    cdn = "cdn"


class RepositoryProvider(str, enum.Enum):
    """Source control provider hosting a repository."""

    github = "github"
    gitlab = "gitlab"
    azure_devops = "azure_devops"
    bitbucket = "bitbucket"


class IncidentSeverity(str, enum.Enum):
    """Severity classification of an operational incident."""

    critical = "critical"
    major = "major"
    minor = "minor"


class IncidentStatus(str, enum.Enum):
    """Current resolution status of an incident."""

    investigating = "investigating"
    identified = "identified"
    monitoring = "monitoring"
    resolved = "resolved"


class ImpactType(str, enum.Enum):
    """Type of service impact during an incident."""

    outage = "outage"
    degraded = "degraded"


class UserRole(str, enum.Enum):
    """Permission role assigned to a user within a tenant."""

    admin = "admin"
    editor = "editor"
    viewer = "viewer"
    incident_commander = "incident_commander"


class AuthProvider(str, enum.Enum):
    """Authentication provider used to authenticate a user."""

    local = "local"
    okta = "okta"
    saml = "saml"
    oidc = "oidc"


__all__ = [
    "AuthProvider",
    "ComponentType",
    "EntityStatus",
    "ImpactType",
    "IncidentSeverity",
    "IncidentStatus",
    "OperationalStatus",
    "RepositoryProvider",
    "ResourceType",
    "ServiceType",
    "UserRole",
]
