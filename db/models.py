"""
db/models.py
SQLAlchemy model for athlete_profile and DB initialisation.
"""
import os
from sqlalchemy import (
    create_engine, Column, String, Integer, Float, Date, Text,
    ARRAY, TIMESTAMP, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class AthleteProfile(Base):
    __tablename__ = "athlete_profile"

    telegram_id = Column(String, primary_key=True)
    name = Column(String)
    age = Column(Integer)
    sports = Column(ARRAY(Text))
    primary_sport = Column(String)
    available_days = Column(ARRAY(Text))
    hours_per_week = Column(Float)
    goal_event = Column(String)
    goal_date = Column(Date)
    goal_type = Column(String)             # finish | time | podium
    goal_time_target = Column(String)      # '3:45:00'
    current_injuries = Column(ARRAY(Text))
    limiters = Column(ARRAY(Text))
    preferred_long_day = Column(String)
    preferred_intensity = Column(String)   # polarised | threshold | mixed
    experience_level = Column(String)      # beginner | intermediate | advanced
    equipment = Column(JSONB)
    email = Column(String)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


def init_db():
    """Create tables if they don't exist."""
    Base.metadata.create_all(bind=engine)
