# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker, declarative_base

# SQLALCHEMY_DATABASE_URL = "sqlite:///./todolist.db"

# engine = create_engine(
#     SQLALCHEMY_DATABASE_URL,
#     connect_args={"check_same_thread": False},  # required for SQLite
# )

# SessionLocal = sessionmaker(
#     autocommit=False,
#     autoflush=False,
#     bind=engine
# )

# Base = declarative_base()


import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Get DATABASE_URL from environment variables (Railway sets this for you)
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# Create the engine for Postgres
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,  # no connect_args needed for Postgres
    pool_pre_ping=True  # optional, keeps connections alive
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()
