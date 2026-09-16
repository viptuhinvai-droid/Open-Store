"""
All state-changing rules for the OPEN STORE developer-contact & distribution
workflow live here — this is the one place that enforces them, so no API
route or future caller can bypass a gate by writing directly to the DB.

Rules enforced:
  - A record can't be hosted (binary_hosted=True) unless stage == AUTHORIZED.
  - A record can't move to AUTHORIZED unless stage == VERIFIED.
  - VERIFIED and AUTHORIZED can only be set through their dedicated
    functions (mark_rights_verified / authorize_for_distribution), each
    requiring a named human actor — never inferred from contact failure,
    silence, or timeouts.
"""

from sqlalchemy.orm import Session

from . import models, schemas

UNVERIFIED_NOTICE = "Developer distribution authorization has not been verified."


def _log(db: Session, record: models.AppRecord, action: str, detail: str = ""):
    entry = models.AuditEntry(app_record_id=record.id, action=action, detail=detail)
    db.add(entry)


def discover_app(db: Session, data: schemas.AppDiscoverIn) -> models.AppRecord:
    record = models.AppRecord(
        app_name=data.app_name,
        developer_name=data.developer_name,
        developer_contact_email=data.developer_contact_email,
        description=data.description,
        icon_url=data.icon_url,
        stage=models.Stage.DISCOVERED,
        contact_status=models.ContactStatus.UNDER_REVIEW,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    _log(db, record, "DISCOVERED", f"Public metadata recorded for {record.app_name}")
    db.commit()
    return record


def get_app(db: Session, app_id: str) -> models.AppRecord | None:
    return db.query(models.AppRecord).filter(models.AppRecord.id == app_id).first()


def list_apps(db: Session, skip: int = 0, limit: int = 50):
    return db.query(models.AppRecord).offset(skip).limit(limit).all()


def already_contacted(record: models.AppRecord) -> bool:
    return any(
        e.action == "CONTACT_ATTEMPT" and e.detail and "sent" in e.detail.lower()
        for e in record.audit_entries
    )


def record_contact_attempt(
    db: Session, record: models.AppRecord, delivered: bool | None
) -> models.AppRecord:
    """delivered=True -> message sent; False -> undeliverable;
    None -> no contact channel was available at all."""
    if record.developer_contact_email is None or delivered is None:
        record.contact_status = models.ContactStatus.CONTACT_NOT_AVAILABLE
        _log(db, record, "CONTACT_ATTEMPT", "No contact channel available")
    elif already_contacted(record):
        _log(db, record, "CONTACT_ATTEMPT", "Skipped — already contacted")
    elif delivered:
        record.contact_status = models.ContactStatus.MESSAGE_SENT
        record.stage = models.Stage.CONTACTED
        _log(db, record, "CONTACT_ATTEMPT", "Message sent")
    else:
        record.contact_status = models.ContactStatus.MESSAGE_UNDELIVERABLE
        _log(db, record, "CONTACT_ATTEMPT", "Message undeliverable")

    db.commit()
    db.refresh(record)
    return record


def mark_awaiting_response(db: Session, record: models.AppRecord) -> models.AppRecord:
    record.contact_status = models.ContactStatus.AWAITING_RESPONSE
    _log(db, record, "STATUS_CHANGE", "Awaiting developer response")
    db.commit()
    db.refresh(record)
    return record


def mark_developer_contacted(db: Session, record: models.AppRecord) -> models.AppRecord:
    record.contact_status = models.ContactStatus.DEVELOPER_CONTACTED
    _log(db, record, "STATUS_CHANGE", "Developer responded / contact confirmed")
    db.commit()
    db.refresh(record)
    return record


def mark_rights_verified(
    db: Session, record: models.AppRecord, verified_by: str, evidence: str
) -> models.AppRecord:
    record.stage = models.Stage.VERIFIED
    record.contact_status = models.ContactStatus.RIGHTS_VERIFIED
    _log(db, record, "RIGHTS_VERIFIED", f"By {verified_by}: {evidence}")
    db.commit()
    db.refresh(record)
    return record


def mark_not_authorized(db: Session, record: models.AppRecord, reason: str) -> models.AppRecord:
    record.contact_status = models.ContactStatus.NOT_AUTHORIZED
    _log(db, record, "NOT_AUTHORIZED", reason)
    db.commit()
    db.refresh(record)
    return record


def authorize_for_distribution(
    db: Session, record: models.AppRecord, authorized_by: str
) -> models.AppRecord:
    if record.stage != models.Stage.VERIFIED:
        raise PermissionError("Cannot authorize distribution before rights are VERIFIED.")
    record.stage = models.Stage.AUTHORIZED
    record.contact_status = models.ContactStatus.AUTHORIZED_FOR_DISTRIBUTION
    _log(db, record, "AUTHORIZED", f"By {authorized_by}")
    db.commit()
    db.refresh(record)
    return record


def host_binary(db: Session, record: models.AppRecord, binary_url: str) -> models.AppRecord:
    if record.stage != models.Stage.AUTHORIZED:
        raise PermissionError("Cannot host binary — application is not AUTHORIZED.")
    record.binary_hosted = True
    record.binary_url = binary_url
    _log(db, record, "BINARY_HOSTED", "APK/AAB made available on OPEN STORE")
    db.commit()
    db.refresh(record)
    return record


def distribution_notice(record: models.AppRecord) -> str:
    if record.stage == models.Stage.AUTHORIZED and record.binary_hosted:
        return "Available for download on OPEN STORE."
    return UNVERIFIED_NOTICE
