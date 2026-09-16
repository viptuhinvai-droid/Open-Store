"""
Database connection setup.

On Render, set the environment variable DATABASE_URL to the connection
string of your Render PostgreSQL instance (Render shows this on the
database's page as the "Internal Database URL").

Locally, if DATABASE_URL isn't set, this falls back to a SQLite file so
you can run and test everything on your own machine first.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./appnova.db")

# Render's Postgres URL sometimes starts with "postgres://" — SQLAlchemy
# needs "postgresql://". Fix it automatically so you don't have to.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
