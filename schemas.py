from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field

from models import Stage, ContactStatus, Category


class AppDiscoverIn(BaseModel):
    app_name: str
    developer_name: Optional[str] = None
    developer_contact_email: Optional[str] = None
    description: Optional[str] = None
    icon_url: Optional[str] = None
    category: Category = Category.APP


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
    category: Category
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


# ---- Account system ----

class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: Optional[str] = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    name: Optional[str] = None

    class Config:
        from_attributes = True


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---- Reviews ----

class ReviewIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None


class ReviewOut(BaseModel):
    id: str
    app_id: str
    user_id: str
    user_name: Optional[str] = None
    rating: int
    comment: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class RatingSummaryOut(BaseModel):
    average: float
    count: int
