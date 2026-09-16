from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from models import Stage, ContactStatus


class AppDiscoverIn(BaseModel):
    app_name: str
    developer_name: Optional[str] = None
    developer_contact_email: Optional[str] = None
    description: Optional[str] = None
    icon_url: Optional[str] = None


class VerifyIn(BaseModel):
    verified_by: str
    evidence: str


class AuthorizeIn(BaseModel):
    authorized_by: str


class NotAuthorizedIn(BaseModel):
    reason: str


class AuditEntryOut(BaseModel):
    action: str
    detail: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class AppRecordOut(BaseModel):
    id: str
    app_name: str
    developer_name: Optional[str] = None
    developer_contact_email: Optional[str] = None
    description: Optional[str] = None
    icon_url: Optional[str] = None
    stage: Stage
    contact_status: ContactStatus
    binary_hosted: bool
    binary_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
