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
from auth_utils import hash_password, verify_password, create_token, decode_token

Base.metadata.create_all(bind=engine)

app = FastAPI(title="OPEN STORE API", version="0.1.0")

ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY")


def require_admin(x_admin_key: str = Header(default=None)):
    """Checks the X-Admin-Key header against ADMIN_API_KEY (set on Render).
    Blocks verify/authorize/host-binary so only you can approve apps."""
    if not ADMIN_API_KEY or x_admin_key != ADMIN_API_KEY:
        raise HTTPException(401, "Invalid or missing admin key")


def get_current_user(
    x_auth_token: str = Header(default=None), db: Session = Depends(get_db)
):
    """Requires a valid 'X-Auth-Token' header containing the login token."""
    if not x_auth_token:
        raise HTTPException(401, "Missing X-Auth-Token header")
    user_id = decode_token(x_auth_token)
    if not user_id:
        raise HTTPException(401, "Invalid or expired token")
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(401, "User not found")
    return user


def get_optional_user(
    x_auth_token: str = Header(default=None), db: Session = Depends(get_db)
):
    """Like get_current_user, but returns None instead of raising when
    there's no token — for endpoints that work for guests too."""
    if not x_auth_token:
        return None
    user_id = decode_token(x_auth_token)
    if not user_id:
        return None
    return crud.get_user(db, user_id)


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
def list_apps(
    skip: int = 0, limit: int = 50, category: str | None = None,
    db: Session = Depends(get_db),
):
    return crud.list_apps(db, skip, limit, category)


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


# ---- Account system ----

@app.post("/auth/signup", response_model=schemas.TokenOut)
def signup(data: schemas.SignupIn, db: Session = Depends(get_db)):
    if crud.get_user_by_email(db, data.email):
        raise HTTPException(400, "An account with this email already exists")
    user = crud.create_user(db, data.email, hash_password(data.password), data.name)
    token = create_token(user.id)
    return {"access_token": token, "user": user}


@app.post("/auth/login", response_model=schemas.TokenOut)
def login(data: schemas.LoginIn, db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, data.email)
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password")
    token = create_token(user.id)
    return {"access_token": token, "user": user}


@app.get("/auth/me", response_model=schemas.UserOut)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user


# ---- Reviews & ratings ----

@app.post("/apps/{app_id}/reviews", response_model=schemas.ReviewOut)
def submit_review(
    app_id: str,
    data: schemas.ReviewIn,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    record = crud.get_app(db, app_id)
    if not record:
        raise HTTPException(404, "App not found")
    review = crud.upsert_review(db, app_id, current_user.id, data.rating, data.comment)
    return schemas.ReviewOut(
        id=review.id, app_id=review.app_id, user_id=review.user_id,
        user_name=current_user.name or current_user.email,
        rating=review.rating, comment=review.comment, created_at=review.created_at,
    )


@app.get("/apps/{app_id}/reviews", response_model=list[schemas.ReviewOut])
def list_reviews(app_id: str, skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    reviews = crud.get_reviews_for_app(db, app_id, skip, limit)
    return [
        schemas.ReviewOut(
            id=r.id, app_id=r.app_id, user_id=r.user_id,
            user_name=(r.user.name or r.user.email) if r.user else None,
            rating=r.rating, comment=r.comment, created_at=r.created_at,
        )
        for r in reviews
    ]


@app.get("/apps/{app_id}/rating", response_model=schemas.RatingSummaryOut)
def get_rating(app_id: str, db: Session = Depends(get_db)):
    average, count = crud.get_rating_summary(db, app_id)
    return {"average": average, "count": count}


# ---- For you ----

@app.get("/recommendations", response_model=list[schemas.AppRecordOut])
def recommendations(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: models.User | None = Depends(get_optional_user),
):
    user_id = current_user.id if current_user else None
    return crud.get_recommendations(db, user_id, limit)
