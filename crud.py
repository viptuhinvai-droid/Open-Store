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

import models, schemas

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
        category=data.category,
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


def list_apps(db: Session, skip: int = 0, limit: int = 50, category: str | None = None):
    q = db.query(models.AppRecord)
    if category:
        q = q.filter(models.AppRecord.category == category)
    return q.offset(skip).limit(limit).all()


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


# ---- Account system ----

def get_user_by_email(db: Session, email: str) -> models.User | None:
    return db.query(models.User).filter(models.User.email == email).first()


def get_user(db: Session, user_id: str) -> models.User | None:
    return db.query(models.User).filter(models.User.id == user_id).first()


def create_user(db: Session, email: str, password_hash: str, name: str | None) -> models.User:
    user = models.User(email=email, password_hash=password_hash, name=name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ---- Reviews & ratings ----

def upsert_review(
    db: Session, app_id: str, user_id: str, rating: int, comment: str | None
) -> models.Review:
    """One review per user per app — a second submission updates the first."""
    existing = (
        db.query(models.Review)
        .filter(models.Review.app_id == app_id, models.Review.user_id == user_id)
        .first()
    )
    if existing:
        existing.rating = rating
        existing.comment = comment
        db.commit()
        db.refresh(existing)
        return existing

    review = models.Review(app_id=app_id, user_id=user_id, rating=rating, comment=comment)
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def get_reviews_for_app(db: Session, app_id: str, skip: int = 0, limit: int = 50):
    return (
        db.query(models.Review)
        .filter(models.Review.app_id == app_id)
        .order_by(models.Review.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_rating_summary(db: Session, app_id: str) -> tuple[float, int]:
    from sqlalchemy import func
    result = (
        db.query(func.avg(models.Review.rating), func.count(models.Review.id))
        .filter(models.Review.app_id == app_id)
        .first()
    )
    avg, count = result
    return (round(float(avg), 2) if avg else 0.0, count or 0)


# ---- "For you" recommendations ----

def get_recommendations(db: Session, user_id: str | None, limit: int = 20):
    """
    If the user has rated apps 4+ in a category before, prioritize
    top-rated AUTHORIZED apps in that category they haven't reviewed yet.
    Falls back to overall top-rated AUTHORIZED apps for everyone else.
    """
    from sqlalchemy import func

    base = (
        db.query(
            models.AppRecord,
            func.coalesce(func.avg(models.Review.rating), 0).label("avg_rating"),
        )
        .outerjoin(models.Review, models.Review.app_id == models.AppRecord.id)
        .filter(
            models.AppRecord.stage == models.Stage.AUTHORIZED,
            models.AppRecord.binary_hosted == True,  # noqa: E712
        )
        .group_by(models.AppRecord.id)
    )

    preferred_categories = []
    reviewed_app_ids = set()
    if user_id:
        liked = (
            db.query(models.AppRecord.category)
            .join(models.Review, models.Review.app_id == models.AppRecord.id)
            .filter(models.Review.user_id == user_id, models.Review.rating >= 4)
            .distinct()
            .all()
        )
        preferred_categories = [c[0] for c in liked]
        reviewed_app_ids = {
            r.app_id for r in db.query(models.Review).filter(models.Review.user_id == user_id)
        }

    rows = base.order_by(func.coalesce(func.avg(models.Review.rating), 0).desc()).all()

    if preferred_categories:
        preferred = [
            r for r in rows
            if r[0].category in preferred_categories and r[0].id not in reviewed_app_ids
        ]
        rest = [r for r in rows if r not in preferred]
        rows = preferred + rest

    return [r[0] for r in rows[:limit]]
