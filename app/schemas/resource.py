from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.schemas.policy import PolicySummary

ResourceName = Annotated[str, StringConstraints(min_length=1, max_length=255)]
ResourceType = Annotated[str, StringConstraints(min_length=1, max_length=255)]
ResourceStatus = Annotated[str, StringConstraints(min_length=1, max_length=255)]
ResourceDescription = Annotated[str, StringConstraints(max_length=5000)]


class ResourceCreateRequest(BaseModel):
    name: ResourceName
    type: ResourceType
    description: ResourceDescription | None = None
    status: ResourceStatus


class ResourceUpdateRequest(BaseModel):
    name: ResourceName | None = None
    type: ResourceType | None = None
    description: ResourceDescription | None = None
    status: ResourceStatus | None = None


class ResourceSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    type: str
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class ResourceCreateData(BaseModel):
    resource: ResourceSummary


class ResourceListData(BaseModel):
    resources: list[ResourceSummary]


class ResourceDetailsData(BaseModel):
    resource: ResourceSummary
    policies: list[PolicySummary]


class ResourceUpdateData(BaseModel):
    resource: ResourceSummary


class ResourceDeleteData(BaseModel):
    resource_id: uuid.UUID
