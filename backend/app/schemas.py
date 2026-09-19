from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models import MembershipRole, TaskStatus


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class RegisterRequest(ApiModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    workspace_name: str = Field(min_length=1, max_length=120)


class LoginRequest(ApiModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class AccessTokenResponse(ApiModel):
    access_token: str
    token_type: str = "bearer"


class WorkspaceResponse(ApiModel):
    id: UUID
    name: str
    role: MembershipRole


class RegisterResponse(ApiModel):
    user_id: UUID
    workspace: WorkspaceResponse


class ProjectCreate(ApiModel):
    name: str = Field(min_length=1, max_length=160)


class ProjectResponse(ApiModel):
    id: UUID
    workspace_id: UUID
    name: str
    created_at: datetime


class TaskCreate(ApiModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10_000)
    status: TaskStatus = TaskStatus.TODO


class TaskUpdate(ApiModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10_000)
    status: TaskStatus | None = None
    version: int = Field(ge=1)

    @model_validator(mode="after")
    def require_change(self) -> TaskUpdate:
        changes = self.model_dump(exclude={"version"}, exclude_unset=True)
        if not changes:
            raise ValueError("At least one task field must be provided")
        if "title" in changes and self.title is None:
            raise ValueError("Title cannot be null")
        if "status" in changes and self.status is None:
            raise ValueError("Status cannot be null")
        return self

    def changes(self) -> dict[str, object]:
        return self.model_dump(exclude={"version"}, exclude_unset=True)


class TaskResponse(ApiModel):
    id: UUID
    project_id: UUID
    created_by_id: UUID
    title: str
    description: str | None
    status: TaskStatus
    version: int
    created_at: datetime
    updated_at: datetime


class VersionConflictResponse(ApiModel):
    code: str = "task_version_conflict"
    message: str
    current_version: int
