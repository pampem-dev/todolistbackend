from sqlalchemy import Column, String, DateTime, Integer, Boolean
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    name = Column(String, nullable=False)
    is_logged_in = Column(Integer, default=0)  # 0 for False, 1 for True

class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, index=True)
    userId = Column('user_id', String, nullable=False, index=True)  # Explicitly map to user_id column
    title = Column(String, nullable=False, index=True)
    description = Column(String, nullable=True)
    due_date = Column(DateTime, nullable=True)
    completed = Column(Boolean, default=False)
    category = Column(String, default='Personal')
    status = Column(String, default='todo')  # todo | inProgress | done
    created_at = Column(DateTime, nullable=False)

class History(Base):
    __tablename__ = "history"

    id = Column(String, primary_key=True, index=True)
    userId = Column('user_id', String, nullable=False, index=True)  # Explicitly map to user_id column
    action = Column(String, nullable=False)  # added | completed | deleted
    title = Column(String, nullable=False)
    time = Column(DateTime, nullable=False)

class Category(Base):
    __tablename__ = "categories"

    id = Column(String, primary_key=True, index=True)
    userId = Column('user_id', String, nullable=False, index=True)  # Explicitly map to user_id column
    name = Column(String, nullable=False)
