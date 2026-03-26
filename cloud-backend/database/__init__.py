"""
Cloud Backend Database Module

Provides Supabase client and database utilities for cloud services.
"""
from .supabase_client import get_supabase_client, reset_client
from .models import Base, User, Company
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import os

# Database URL from environment (for SQLAlchemy if needed)
DATABASE_URL = os.getenv("DATABASE_URL")

# Create SQLAlchemy engine and session if DATABASE_URL is set
engine = None
SessionLocal = None

if DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=3600,
        connect_args={
            "sslmode": "require"
        }
    )
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )

def get_db():
    """
    Dependency for FastAPI routes that need SQLAlchemy database access.
    Yields a database session and ensures it's closed after use.
    """
    if not SessionLocal:
        raise RuntimeError("DATABASE_URL not configured. Cannot create database session.")

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

__all__ = ["get_supabase_client", "reset_client", "get_db",
           "User", "Company", "Base"]
