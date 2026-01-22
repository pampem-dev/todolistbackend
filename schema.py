from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

# User Schemas
class UserBase(BaseModel):
    email: EmailStr  # Validates email format
    password: str
    name: str

class UserCreate(UserBase):
    pass

class UserResponse(BaseModel):
    id: str
    email: str
    password: str
    name: str
    is_logged_in: bool

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: str
    password: str

# Task Schemas
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    completed: bool = False
    category: str = 'Personal'
    userId: str
    status: str = 'todo'

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    completed: bool = False
    category: str = 'Personal'
    status: str = 'todo'
    userId: Optional[str] = None  # Will be set by backend from logged-in user
    created_at: Optional[datetime] = None  # Will be set by backend

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    completed: Optional[bool] = None
    category: Optional[str] = None
    status: Optional[str] = None

class TaskResponse(TaskBase):
    id: str
    userId: str
    created_at: datetime

    class Config:
        from_attributes = True

# History Schemas
class HistoryBase(BaseModel):
    userId: str
    action: str  # added | completed | deleted
    title: str
    time: datetime

class HistoryCreate(HistoryBase):
    id: str

class HistoryResponse(HistoryBase):
    id: str

    class Config:
        from_attributes = True

# Category Schemas
class CategoryBase(BaseModel):
    userId: str
    name: str

class CategoryCreate(CategoryBase):
    id: str

class CategoryResponse(CategoryBase):
    id: str

    class Config:
        from_attributes = True
