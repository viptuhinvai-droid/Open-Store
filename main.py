"""
OPEN STORE backend API.

This is the ONE API that both the website and (later) the mobile app will
call — so all workflow logic lives here once, not duplicated per client.

Run locally:
    uvicorn app.main:app --reload
Then open http://127.0.0.1:8000/docs for an interactive test page.
"""

import os

from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

import models, schemas, crud
from database import engine, get_db, Base
from email_utils import send_developer_email

Base.metadata.create_all(bind=engine)

app = FastAPI(title="OPEN STORE API", version="0.1.0")

ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY")


def require_admin(x_admin_key: str = Header(default=None)):
    """Checks the X-Admin-Key header against ADMIN_API_KEY (set on Render).
    Blocks verify/authorize/host-binary so only you can approve apps."""
    if not ADMIN_API_KEY or x_admin_key != ADMIN_API_KEY:
        raise HTTPException(401, "Invalid or missing admin key")

# Allows the website (and later the mobile app) to call this API from
# a different domain. Tighten this to your real domain once you have one.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "OPEN STORE API is running"}


@app.post("/apps", response_model=schemas.AppRecordOut)
def discover_app(data: schemas.AppDiscoverIn, db: Session = Depends(get_db)):
    return crud.discover_app(db, data)


@app.get("/apps", response_model=list[schemas.AppRecordOut])
def list_apps(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return crud.list_apps(db, skip, limit)


@app.get("/apps/{app_id}", response_model=schemas.AppRecordOut)
def get_app(app_id: str, db: Session = Depends(get_db)):
    record = crud.get_app(db, app_id)
    if not record:
        raise HTTPException(404, "App not found")
    return record


@app.get("/apps/{app_id}/notice")
def get_notice(app_id: str, db: Session = Depends(get_db)):
    record = crud.get_app(db, app_id)
    if not record:
        raise HTTPException(404, "App not found")
    return {"notice": crud.distribution_notice(record)}


@app.post("/apps/{app_id}/contact", response_model=schemas.AppRecordOut)
def attempt_contact(app_id: str, db: Session = Depends(get_db)):
    """Sends the single developer message by real email."""
    record = crud.get_app(db, app_id)
    if not record:
        raise HTTPException(404, "App not found")

    if record.developer_contact_email is None:
        delivered = None
    else:
        delivered = send_developer_email(
            record.developer_contact_email,
            record.developer_name or "Unknown Developer",
            record.app_name,
        )

    return crud.record_contact_attempt(db, record, delivered)


@app.post("/apps/{app_id}/awaiting-response", response_model=schemas.AppRecordOut)
def awaiting_response(app_id: str, db: Session = Depends(get_db)):
    record = crud.get_app(db, app_id)
    if not record:
        raise HTTPException(404, "App not found")
    return crud.mark_awaiting_response(db, record)


@app.post("/apps/{app_id}/developer-contacted", response_model=schemas.AppRecordOut)
def developer_contacted(app_id: str, db: Session = Depends(get_db)):
    record = crud.get_app(db, app_id)
    if not record:
        raise HTTPException(404, "App not found")
    return crud.mark_developer_contacted(db, record)


@app.post("/apps/{app_id}/verify", response_model=schemas.AppRecordOut)
def verify_rights(
    app_id: str,
    data: schemas.VerifyIn,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    record = crud.get_app(db, app_id)
    if not record:
        raise HTTPException(404, "App not found")
    return crud.mark_rights_verified(db, record, data.verified_by, data.evidence)


@app.post("/apps/{app_id}/not-authorized", response_model=schemas.AppRecordOut)
def not_authorized(
    app_id: str,
    data: schemas.NotAuthorizedIn,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    record = crud.get_app(db, app_id)
    if not record:
        raise HTTPException(404, "App not found")
    return crud.mark_not_authorized(db, record, data.reason)


@app.post("/apps/{app_id}/authorize", response_model=schemas.AppRecordOut)
def authorize(
    app_id: str,
    data: schemas.AuthorizeIn,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    record = crud.get_app(db, app_id)
    if not record:
        raise HTTPException(404, "App not found")
    try:
        return crud.authorize_for_distribution(db, record, data.authorized_by)
    except PermissionError as e:
        raise HTTPException(400, str(e))


@app.post("/apps/{app_id}/host-binary", response_model=schemas.AppRecordOut)
def host_binary(
    app_id: str,
    binary_url: str,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    record = crud.get_app(db, app_id)
    if not record:
        raise HTTPException(404, "App not found")
    try:
        return crud.host_binary(db, record, binary_url)
    except PermissionError as e:
        raise HTTPException(400, str(e))
