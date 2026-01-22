from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import uuid
from pydantic import BaseModel

from database import SessionLocal, engine
import models
import schema

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="TodoList API", description="Backend API for TodoList Flutter App")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Root endpoint
@app.get("/")
def read_root():
    return {"message": "TodoList API is running"}

# ================= USERS / AUTH =================

@app.get("/users", response_model=List[schema.UserResponse])
def get_all_users(db: Session = Depends(get_db)):
    """
    Get all registered users.
    """
    users = db.query(models.User).all()
    return users
    
@app.post("/users/register", response_model=schema.UserResponse)
def register_user(user: schema.UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    # Create new user
    new_user = models.User(
        id=str(uuid.uuid4()),
        email=user.email,
        password=user.password,  # In production, hash this password
        name=user.name,
        is_logged_in=0
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/users/login", response_model=schema.UserResponse)
def login_user(user_login: schema.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(
        models.User.email == user_login.email,
        models.User.password == user_login.password  # In production, compare hashed passwords
    ).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Update login status
    user.is_logged_in = 1
    db.commit()
    db.refresh(user)
    return user

@app.post("/users/logout")
def logout_user(db: Session = Depends(get_db)):
    # Logout all users
    db.query(models.User).update({"is_logged_in": 0})
    db.commit()
    return {"message": "All users logged out"}

@app.get("/users/current", response_model=schema.UserResponse)
def get_current_user(db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.is_logged_in == 1).first()
    if not user:
        raise HTTPException(status_code=401, detail="No user is currently logged in")
    return user

# DELETE a single user by ID
@app.delete("/users/{user_id}")
def delete_user(user_id: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User with id {user_id} not found")
    
    # Optionally, delete related tasks, history, categories
    db.query(models.Task).filter(models.Task.userId == user_id).delete()
    db.query(models.History).filter(models.History.userId == user_id).delete()
    db.query(models.Category).filter(models.Category.userId == user_id).delete()
    
    db.delete(user)
    db.commit()
    
    return {"message": f"User '{user.email}' and all related data deleted"}


# DELETE all users
@app.delete("/users")
def delete_all_users(db: Session = Depends(get_db)):
    # Delete all related data first
    db.query(models.Task).delete()
    db.query(models.History).delete()
    db.query(models.Category).delete()
    
    deleted_count = db.query(models.User).delete()
    db.commit()
    
    return {"message": f"Deleted {deleted_count} users and all related data"}

# ================= TASKS =================

@app.get("/tasks", response_model=List[schema.TaskResponse])
def get_tasks(user_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.Task)
    
    if user_id:
        query = query.filter(models.Task.userId == user_id)
    else:
        # If no user_id specified, get tasks for logged in user
        current_user = db.query(models.User).filter(models.User.is_logged_in == 1).first()
        if current_user:
            query = query.filter(models.Task.userId == current_user.id)
        else:
            return []
    
    return query.all()

@app.post("/tasks", response_model=schema.TaskResponse)
def create_task(task: schema.TaskCreate, db: Session = Depends(get_db)):
    # Validate that user is logged in before creating task
    current_user = db.query(models.User).filter(models.User.is_logged_in == 1).first()
    if not current_user:
        raise HTTPException(status_code=401, detail="User must be logged in to create tasks")
    
    new_task = models.Task(
        id=str(uuid.uuid4()),
        userId=current_user.id,  # Use logged-in user's ID
        title=task.title,
        description=task.description,
        due_date=task.due_date,
        completed=task.completed,
        category=task.category,
        status=task.status,
        created_at=task.created_at or datetime.utcnow()  # Use provided timestamp or current time
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    # Create history entry
    history_entry = models.History(
        id=str(uuid.uuid4()),
        userId=current_user.id,  # Use logged-in user's ID
        action="added",
        title=task.title,
        time=datetime.utcnow()
    )
    db.add(history_entry)
    db.commit()
    
    return new_task

@app.put("/tasks/{task_id}", response_model=schema.TaskResponse)
def update_task(task_id: str, task_update: schema.TaskUpdate, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task with id {task_id} not found")

    old_completed = task.completed
    old_status = task.status
    
    # Update fields if provided
    update_data = task_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
    
    db.commit()
    db.refresh(task)

    history_actions: List[str] = []

    if task_update.completed is not None and task_update.completed != old_completed:
        if task_update.completed:
            history_actions.append("completed")
        else:
            history_actions.append("marked as incomplete")

    if task_update.status is not None and task_update.status != old_status:
        if task_update.status == "completed":
            history_actions.append("moved to completed")
        elif task_update.status == "inprogress":
            history_actions.append("moved to in progress")
        elif task_update.status == "todo":
            history_actions.append("moved to to do")

    for action in history_actions:
        history_entry = models.History(
            id=str(uuid.uuid4()),
            userId=task.userId,
            action=action,
            title=task.title,
            time=datetime.utcnow()
        )
        db.add(history_entry)

    if history_actions:
        db.commit()
    
    return task

@app.delete("/tasks/{task_id}")
def delete_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task with id {task_id} not found")
    
    # Create history entry before deletion
    history_entry = models.History(
        id=str(uuid.uuid4()),
        userId=task.userId,
        action="deleted",
        title=task.title,
        time=datetime.utcnow()
    )
    db.add(history_entry)
    
    # Delete task
    db.delete(task)
    db.commit()
    
    return {"message": f"Task with id {task_id} deleted"}

# ================= HISTORY =================

@app.get("/history", response_model=List[schema.HistoryResponse])
def get_history(user_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.History)
    
    if user_id:
        query = query.filter(models.History.userId == user_id)
    else:
        # If no user_id specified, get history for logged in user
        current_user = db.query(models.User).filter(models.User.is_logged_in == 1).first()
        if current_user:
            query = query.filter(models.History.userId == current_user.id)
        else:
            return []
    
    # Sort by time DESC (newest first)
    return query.order_by(models.History.time.desc()).all()

@app.delete("/history")
def clear_history(user_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.History)
    
    if user_id:
        query = query.filter(models.History.userId == user_id)
    else:
        # Clear history for logged in user
        current_user = db.query(models.User).filter(models.User.is_logged_in == 1).first()
        if current_user:
            query = query.filter(models.History.userId == current_user.id)
        else:
            return {"message": "No user logged in"}
    
    deleted_count = query.count()
    query.delete()
    db.commit()
    
    return {"message": f"Cleared {deleted_count} history entries"}

class HistoryBatchDelete(BaseModel):
    history_ids: List[str]
    user_id: Optional[str] = None

@app.delete("/history/batch")
def delete_history_batch(request: HistoryBatchDelete, db: Session = Depends(get_db)):
    query = db.query(models.History).filter(models.History.id.in_(request.history_ids))
    
    if request.user_id:
        query = query.filter(models.History.userId == request.user_id)
    else:
        # Delete for logged in user
        current_user = db.query(models.User).filter(models.User.is_logged_in == 1).first()
        if current_user:
            query = query.filter(models.History.userId == current_user.id)
        else:
            raise HTTPException(status_code=401, detail="No user logged in")
    
    deleted_count = query.count()
    query.delete(synchronize_session=False)
    db.commit()
    
    return {"message": f"Deleted {deleted_count} history items"}

@app.delete("/history/{history_id}")
def delete_history_item(history_id: str, user_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.History).filter(models.History.id == history_id)
    
    if user_id:
        query = query.filter(models.History.userId == user_id)
    else:
        # Delete for logged in user
        current_user = db.query(models.User).filter(models.User.is_logged_in == 1).first()
        if current_user:
            query = query.filter(models.History.userId == current_user.id)
        else:
            raise HTTPException(status_code=401, detail="No user logged in")
    
    history_item = query.first()
    if not history_item:
        raise HTTPException(status_code=404, detail=f"History item with id {history_id} not found")
    
    db.delete(history_item)
    db.commit()
    
    return {"message": f"History item with id {history_id} deleted"}

# ================= CATEGORIES =================

@app.get("/categories", response_model=List[str])
def get_categories(user_id: Optional[str] = None, db: Session = Depends(get_db)):
    core_categories = ['Work', 'Personal', 'School', 'Others', 'General']
    
    query = db.query(models.Category)
    
    if user_id:
        query = query.filter(models.Category.userId == user_id)
    else:
        # If no user_id specified, get categories for logged in user
        current_user = db.query(models.User).filter(models.User.is_logged_in == 1).first()
        if current_user:
            query = query.filter(models.Category.userId == current_user.id)
        else:
            return core_categories
    
    user_categories = [cat.name for cat in query.all()]
    
    # Combine core and user categories, remove duplicates
    all_categories = list(set(core_categories + user_categories))
    return all_categories

@app.post("/categories", response_model=schema.CategoryResponse)
def create_category(category: schema.CategoryCreate, db: Session = Depends(get_db)):
    # Check if category already exists for this user
    existing = db.query(models.Category).filter(
        models.Category.userId == category.userId,
        models.Category.name == category.name
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists for this user")
    
    new_category = models.Category(
        id=category.id,
        userId=category.userId,
        name=category.name
    )
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    
    return new_category

@app.delete("/categories/{category_name}")
def delete_category(category_name: str, user_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.Category).filter(models.Category.name == category_name)
    
    if user_id:
        query = query.filter(models.Category.userId == user_id)
    else:
        # Delete category for logged in user
        current_user = db.query(models.User).filter(models.User.is_logged_in == 1).first()
        if current_user:
            query = query.filter(models.Category.userId == current_user.id)
        else:
            raise HTTPException(status_code=401, detail="No user logged in")
    
    category = query.first()
    if not category:
        raise HTTPException(status_code=404, detail=f"Category '{category_name}' not found")
    
    db.delete(category)
    db.commit()
    
    return {"message": f"Category '{category_name}' deleted"}
