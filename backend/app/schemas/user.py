"""Pydantic schemas for user management endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import AuthProvider, UserRole


class UserCreate(BaseModel):
    """Payload for creating a new local user (Admin only)."""

    email: EmailStr
    display_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, description="Plain-text password; stored as bcrypt hash")
    role: UserRole = UserRole.viewer
    is_active: bool = True

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "jane.doe@example.com",
                    "display_name": "Jane Doe",
                    "password": "securepassword1",
                    "role": "viewer",
                }
            ]
        }
    }


class UserUpdate(BaseModel):
    """Payload for updating an existing user (Admin only). All fields optional."""

    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    role: UserRole | None = None
    is_active: bool | None = None


class UserListItem(BaseModel):
    """Abbreviated user representation for list responses."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    display_name: str
    role: UserRole
    auth_provider: AuthProvider
    is_active: bool
    last_login_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserRead(BaseModel):
    """Full user representation including timestamps."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    display_name: str
    role: UserRole
    auth_provider: AuthProvider
    external_id: str | None = None
    is_active: bool
    last_login_at: datetime | None = None
    person_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


__all__ = ["UserCreate", "UserListItem", "UserRead", "UserUpdate"]
