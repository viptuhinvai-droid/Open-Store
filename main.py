"""
OPEN STORE backend API.

This is the ONE API that both the website and (later) the mobile app will
call — so all workflow logic lives here once, not duplicated per client.

Run locally:
    uvicorn app.main:app --reload
Then open http://127.0.0.1:8000/docs for an interactive test page.
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import models, schemas, crud
from .database import engine, get_db, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="OPEN STORE API", version="0.1.0")

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
    """Sends (or attempts to send) the single developer message.
    NOTE: actual email delivery isn't wired up yet — see the TODO below."""
    record = crud.get_app(db, app_id)
    if not record:
        raise HTTPException(404, "App not found")

    # TODO: replace this with a real email-sending call, then pass the
    # actual delivered=True/False result in below instead of this stand-in.
    delivered = None if record.developer_contact_email is None else True

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
def verify_rights(app_id: str, data: schemas.VerifyIn, db: Session = Depends(get_db)):
    """Admin-only in the real app — add authentication before going live."""
    record = crud.get_app(db, app_id)
    if not record:
        raise HTTPException(404, "App not found")
    return crud.mark_rights_verified(db, record, data.verified_by, data.evidence)


@app.post("/apps/{app_id}/not-authorized", response_model=schemas.AppRecordOut)
def not_authorized(app_id: str, data: schemas.NotAuthorizedIn, db: Session = Depends(get_db)):
    record = crud.get_app(db, app_id)
    if not record:
        raise HTTPException(404, "App not found")
    return crud.mark_not_authorized(db, record, data.reason)


@app.post("/apps/{app_id}/authorize", response_model=schemas.AppRecordOut)
def authorize(app_id: str, data: schemas.AuthorizeIn, db: Session = Depends(get_db)):
    """Admin-only in the real app — add authentication before going live."""
    record = crud.get_app(db, app_id)
    if not record:
        raise HTTPException(404, "App not found")
    try:
        return crud.authorize_for_distribution(db, record, data.authorized_by)
    except PermissionError as e:
        raise HTTPException(400, str(e))


@app.post("/apps/{app_id}/host-binary", response_model=schemas.AppRecordOut)
def host_binary(app_id: str, binary_url: str, db: Session = Depends(get_db)):
    """Admin-only in the real app — add authentication before going live."""
    record = crud.get_app(db, app_id)
    if not record:
        raise HTTPException(404, "App not found")
    try:
        return crud.host_binary(db, record, binary_url)
    except PermissionError as e:
        raise HTTPException(400, str(e))
