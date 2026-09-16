"""
Database models for OPEN STORE.

Mirrors the workflow rules from the OPEN STORE policy:
  DISCOVERED -> CONTACTED -> VERIFIED -> AUTHORIZED

binary_hosted can only become True once stage == AUTHORIZED — enforced in
crud.py, not just here, so there's a single choke point for that rule.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey, Text, Enum as SAEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


def gen_uuid():
    return str(uuid.uuid4())


class Stage(str, enum.Enum):
    DISCOVERED = "DISCOVERED"
    CONTACTED = "CONTACTED"
    VERIFIED = "VERIFIED"
    AUTHORIZED = "AUTHORIZED"


class ContactStatus(str, enum.Enum):
    CONTACT_NOT_AVAILABLE = "Contact Not Available"
    MESSAGE_SENT = "Message Sent"
    MESSAGE_UNDELIVERABLE = "Message Undeliverable"
    AWAITING_RESPONSE = "Awaiting Response"
    DEVELOPER_CONTACTED = "Developer Contacted"
    RIGHTS_VERIFIED = "Rights Verified"
    AUTHORIZED_FOR_DISTRIBUTION = "Authorized for Distribution"
    NOT_AUTHORIZED = "Not Authorized"
    UNDER_REVIEW = "Under Review"


class AppRecord(Base):
    __tablename__ = "app_records"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    app_name = Column(String, nullable=False, index=True)
    developer_name = Column(String, nullable=True)
    developer_contact_email = Column(String, nullable=True)

    # Public metadata only — store listing description, icon URL, etc.
    description = Column(Text, nullable=True)
    icon_url = Column(String, nullable=True)

    stage = Column(SAEnum(Stage), nullable=False, default=Stage.DISCOVERED)
    contact_status = Column(
        SAEnum(ContactStatus), nullable=False, default=ContactStatus.UNDER_REVIEW
    )
    binary_hosted = Column(Boolean, nullable=False, default=False)
    binary_url = Column(String, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    audit_entries = relationship(
        "AuditEntry", back_populates="app_record", cascade="all, delete-orphan"
    )


class AuditEntry(Base):
    __tablename__ = "audit_entries"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    app_record_id = Column(UUID(as_uuid=False), ForeignKey("app_records.id"))
    action = Column(String, nullable=False)
    detail = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    app_record = relationship("AppRecord", back_populates="audit_entries")
