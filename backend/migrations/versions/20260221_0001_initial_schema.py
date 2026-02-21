"""initial schema

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-02-21 00:01:00.000000+00:00

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = None
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    # ---------------------------------------------------------------------------
    # tenants
    # ---------------------------------------------------------------------------
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("settings", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("slug", name="uq_tenants_slug"),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"])

    # ---------------------------------------------------------------------------
    # teams
    # ---------------------------------------------------------------------------
    op.create_table(
        "teams",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("slack_channel", sa.String(255), nullable=True),
        sa.Column("parent_team_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["parent_team_id"], ["teams.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_teams_tenant_slug"),
    )
    op.create_index("ix_teams_tenant_id", "teams", ["tenant_id"])
    op.create_index("ix_teams_slug", "teams", ["slug"])
    op.create_index("ix_teams_deleted_at", "teams", ["deleted_at"])
    op.create_index("ix_teams_parent_team_id", "teams", ["parent_team_id"])

    # ---------------------------------------------------------------------------
    # persons
    # ---------------------------------------------------------------------------
    op.create_table(
        "persons",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("department", sa.String(255), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("manager_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("slack_user_id", sa.String(50), nullable=True),
        sa.Column("github_username", sa.String(100), nullable=True),
        sa.Column("external_hr_id", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["manager_id"], ["persons.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("tenant_id", "email", name="uq_persons_tenant_email"),
    )
    op.create_index("ix_persons_tenant_id", "persons", ["tenant_id"])
    op.create_index("ix_persons_email", "persons", ["email"])
    op.create_index("ix_persons_deleted_at", "persons", ["deleted_at"])
    op.create_index("ix_persons_manager_id", "persons", ["manager_id"])
    op.create_index("ix_persons_team_id", "persons", ["team_id"])

    # ---------------------------------------------------------------------------
    # users
    # ---------------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("role", sa.String(50), nullable=False, server_default="viewer"),
        sa.Column("auth_provider", sa.String(50), nullable=False, server_default="local"),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["person_id"], ["persons.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
        sa.UniqueConstraint("tenant_id", "auth_provider", "external_id", name="uq_users_tenant_provider_external"),
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_deleted_at", "users", ["deleted_at"])
    op.create_index("ix_users_person_id", "users", ["person_id"])

    # ---------------------------------------------------------------------------
    # refresh_tokens
    # ---------------------------------------------------------------------------
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])

    # ---------------------------------------------------------------------------
    # products
    # ---------------------------------------------------------------------------
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("owner_team_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("owner_person_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tier", sa.Integer(), nullable=True),
        sa.Column("tags", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["owner_team_id"], ["teams.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_person_id"], ["persons.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_products_tenant_slug"),
    )
    op.create_index("ix_products_tenant_id", "products", ["tenant_id"])
    op.create_index("ix_products_slug", "products", ["slug"])
    op.create_index("ix_products_deleted_at", "products", ["deleted_at"])
    op.create_index("ix_products_owner_team_id", "products", ["owner_team_id"])
    op.create_index("ix_products_owner_person_id", "products", ["owner_person_id"])

    # ---------------------------------------------------------------------------
    # services
    # ---------------------------------------------------------------------------
    op.create_table(
        "services",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("service_type", sa.String(50), nullable=False, server_default="api"),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("operational_status", sa.String(50), nullable=False, server_default="operational"),
        sa.Column("owner_team_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("owner_person_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tier", sa.Integer(), nullable=True),
        sa.Column("pagerduty_service_id", sa.String(255), nullable=True),
        sa.Column("datadog_service_name", sa.String(255), nullable=True),
        sa.Column("runbook_url", sa.String(2048), nullable=True),
        sa.Column("dashboard_url", sa.String(2048), nullable=True),
        sa.Column("slo_target", sa.Float(), nullable=True),
        sa.Column("attributes", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("tags", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["owner_team_id"], ["teams.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_person_id"], ["persons.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_services_tenant_slug"),
    )
    op.create_index("ix_services_tenant_id", "services", ["tenant_id"])
    op.create_index("ix_services_slug", "services", ["slug"])
    op.create_index("ix_services_deleted_at", "services", ["deleted_at"])
    op.create_index("ix_services_owner_team_id", "services", ["owner_team_id"])
    op.create_index("ix_services_owner_person_id", "services", ["owner_person_id"])

    # ---------------------------------------------------------------------------
    # components
    # ---------------------------------------------------------------------------
    op.create_table(
        "components",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("component_type", sa.String(50), nullable=False, server_default="library"),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("owner_team_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("owner_person_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("language", sa.String(100), nullable=True),
        sa.Column("version", sa.String(100), nullable=True),
        sa.Column("package_name", sa.String(255), nullable=True),
        sa.Column("attributes", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("tags", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["owner_team_id"], ["teams.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_person_id"], ["persons.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_components_tenant_slug"),
    )
    op.create_index("ix_components_tenant_id", "components", ["tenant_id"])
    op.create_index("ix_components_slug", "components", ["slug"])
    op.create_index("ix_components_deleted_at", "components", ["deleted_at"])
    op.create_index("ix_components_owner_team_id", "components", ["owner_team_id"])
    op.create_index("ix_components_owner_person_id", "components", ["owner_person_id"])

    # ---------------------------------------------------------------------------
    # repositories
    # ---------------------------------------------------------------------------
    op.create_table(
        "repositories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("clone_url", sa.String(2048), nullable=True),
        sa.Column("html_url", sa.String(2048), nullable=True),
        sa.Column("default_branch", sa.String(255), nullable=False, server_default=sa.text("'main'")),
        sa.Column("is_private", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("language", sa.String(100), nullable=True),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "full_name", name="uq_repositories_tenant_full_name"),
    )
    op.create_index("ix_repositories_tenant_id", "repositories", ["tenant_id"])
    op.create_index("ix_repositories_deleted_at", "repositories", ["deleted_at"])

    # ---------------------------------------------------------------------------
    # resources
    # ---------------------------------------------------------------------------
    op.create_table(
        "resources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("cloud_provider", sa.String(50), nullable=True),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("account_id", sa.String(255), nullable=True),
        sa.Column("resource_id", sa.String(512), nullable=True),
        sa.Column("owner_team_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("attributes", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("tags", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["owner_team_id"], ["teams.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_resources_tenant_slug"),
    )
    op.create_index("ix_resources_tenant_id", "resources", ["tenant_id"])
    op.create_index("ix_resources_slug", "resources", ["slug"])
    op.create_index("ix_resources_deleted_at", "resources", ["deleted_at"])
    op.create_index("ix_resources_owner_team_id", "resources", ["owner_team_id"])

    # ---------------------------------------------------------------------------
    # incidents
    # ---------------------------------------------------------------------------
    op.create_table(
        "incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="investigating"),
        sa.Column("incident_commander_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("slack_channel", sa.String(255), nullable=True),
        sa.Column("pagerduty_incident_id", sa.String(255), nullable=True),
        sa.Column("postmortem_url", sa.String(2048), nullable=True),
        sa.Column("attributes", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["incident_commander_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_incidents_tenant_id", "incidents", ["tenant_id"])
    op.create_index("ix_incidents_deleted_at", "incidents", ["deleted_at"])
    op.create_index("ix_incidents_incident_commander_id", "incidents", ["incident_commander_id"])

    # ---------------------------------------------------------------------------
    # incident_timeline_entries
    # ---------------------------------------------------------------------------
    op.create_table(
        "incident_timeline_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("entry_type", sa.String(100), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_incident_timeline_entries_incident_id", "incident_timeline_entries", ["incident_id"])

    # ---------------------------------------------------------------------------
    # incident_affected_entities
    # ---------------------------------------------------------------------------
    op.create_table(
        "incident_affected_entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("impact_type", sa.String(50), nullable=False, server_default="outage"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("incident_id", "entity_type", "entity_id", name="uq_incident_affected_entity"),
    )
    op.create_index("ix_incident_affected_entities_incident_id", "incident_affected_entities", ["incident_id"])

    # ---------------------------------------------------------------------------
    # scorecards
    # ---------------------------------------------------------------------------
    op.create_table(
        "scorecards",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("passing_threshold", sa.Integer(), nullable=False, server_default=sa.text("70")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_scorecards_tenant_slug"),
    )
    op.create_index("ix_scorecards_tenant_id", "scorecards", ["tenant_id"])
    op.create_index("ix_scorecards_slug", "scorecards", ["slug"])
    op.create_index("ix_scorecards_deleted_at", "scorecards", ["deleted_at"])

    # ---------------------------------------------------------------------------
    # scorecard_criteria
    # ---------------------------------------------------------------------------
    op.create_table(
        "scorecard_criteria",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("scorecard_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("weight", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("rule_type", sa.String(100), nullable=False),
        sa.Column("rule_config", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["scorecard_id"], ["scorecards.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_scorecard_criteria_scorecard_id", "scorecard_criteria", ["scorecard_id"])

    # ---------------------------------------------------------------------------
    # audit_logs
    # ---------------------------------------------------------------------------
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(255), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_type", sa.String(50), nullable=False, server_default=sa.text("'user'")),
        sa.Column("entity_type", sa.String(100), nullable=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("before", postgresql.JSONB(), nullable=True),
        sa.Column("after", postgresql.JSONB(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("request_id", sa.String(36), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_audit_logs_tenant_occurred", "audit_logs", ["tenant_id", "occurred_at"])
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"])
    op.create_index("ix_audit_logs_actor", "audit_logs", ["actor_id"])

    # ---------------------------------------------------------------------------
    # entity_assignments
    # ---------------------------------------------------------------------------
    op.create_table(
        "entity_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assignee_type", sa.String(50), nullable=False),
        sa.Column("assignee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(100), nullable=False, server_default=sa.text("'owner'")),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("assigned_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "tenant_id", "entity_type", "entity_id", "assignee_type", "assignee_id", "role",
            name="uq_entity_assignment",
        ),
    )
    op.create_index("ix_entity_assignments_tenant_id", "entity_assignments", ["tenant_id"])

    # ---------------------------------------------------------------------------
    # Association tables (many-to-many)
    # ---------------------------------------------------------------------------
    op.create_table(
        "product_services",
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("product_id", "service_id"),
    )

    op.create_table(
        "service_components",
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("component_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["component_id"], ["components.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("service_id", "component_id"),
    )

    op.create_table(
        "service_resources",
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resource_id"], ["resources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("service_id", "resource_id"),
    )

    op.create_table(
        "service_dependencies",
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("depends_on_service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["depends_on_service_id"], ["services.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("service_id", "depends_on_service_id"),
        sa.UniqueConstraint("service_id", "depends_on_service_id", name="uq_service_dependencies"),
    )

    op.create_table(
        "component_dependencies",
        sa.Column("component_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("depends_on_component_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["component_id"], ["components.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["depends_on_component_id"], ["components.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("component_id", "depends_on_component_id"),
        sa.UniqueConstraint("component_id", "depends_on_component_id", name="uq_component_dependencies"),
    )

    op.create_table(
        "component_service_dependencies",
        sa.Column("component_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("depends_on_service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["component_id"], ["components.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["depends_on_service_id"], ["services.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("component_id", "depends_on_service_id"),
        sa.UniqueConstraint("component_id", "depends_on_service_id", name="uq_component_service_dependencies"),
    )

    op.create_table(
        "service_repositories",
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("service_id", "repository_id"),
    )

    op.create_table(
        "component_repositories",
        sa.Column("component_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("repository_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["component_id"], ["components.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("component_id", "repository_id"),
    )


def downgrade() -> None:
    # Drop association tables first
    op.drop_table("component_repositories")
    op.drop_table("service_repositories")
    op.drop_table("component_service_dependencies")
    op.drop_table("component_dependencies")
    op.drop_table("service_dependencies")
    op.drop_table("service_resources")
    op.drop_table("service_components")
    op.drop_table("product_services")

    # Drop dependent tables
    op.drop_table("entity_assignments")
    op.drop_table("audit_logs")
    op.drop_table("scorecard_criteria")
    op.drop_table("scorecards")
    op.drop_table("incident_affected_entities")
    op.drop_table("incident_timeline_entries")
    op.drop_table("incidents")
    op.drop_table("resources")
    op.drop_table("repositories")
    op.drop_table("components")
    op.drop_table("services")
    op.drop_table("products")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
    op.drop_table("persons")
    op.drop_table("teams")
    op.drop_table("tenants")
