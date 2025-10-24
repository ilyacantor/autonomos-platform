from uuid import UUID
from sqlalchemy.orm import Session
from app import models, schemas
from app.security import get_password_hash

def create_tenant(db: Session, tenant: schemas.TenantCreate) -> models.Tenant:
    """Create a new tenant"""
    db_tenant = models.Tenant(name=tenant.name)
    db.add(db_tenant)
    db.commit()
    db.refresh(db_tenant)
    return db_tenant

def create_user(db: Session, user: schemas.UserCreate, tenant_id: UUID) -> models.User:
    """Create a new user for a tenant"""
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        tenant_id=tenant_id
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user_by_email(db: Session, email: str) -> models.User | None:
    """Retrieve a user by email"""
    return db.query(models.User).filter(models.User.email == email).first()

def create_task(db: Session, task: schemas.TaskCreate, tenant_id: UUID) -> models.Task:
    """Create a new task in the database for a specific tenant"""
    db_task = models.Task(
        tenant_id=tenant_id,
        payload=task.payload,
        callback_url=task.callback_url,
        max_retries=task.max_retries,
        on_success_next_task=task.on_success_next_task
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def get_task(db: Session, task_id: UUID, tenant_id: UUID) -> models.Task | None:
    """Retrieve a task by its ID, filtered by tenant_id for security"""
    return db.query(models.Task).filter(
        models.Task.id == task_id,
        models.Task.tenant_id == tenant_id
    ).first()

def update_task_status(db: Session, task_id: UUID, status: str, result: dict | None = None, tenant_id: UUID | None = None) -> models.Task | None:
    """Update a task's status and optionally its result"""
    if tenant_id:
        db_task = get_task(db, task_id, tenant_id)
    else:
        db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    
    if db_task:
        db_task.status = status
        if result is not None:
            db_task.result = result
        db.commit()
        db.refresh(db_task)
    return db_task

def create_task_log(db: Session, task_id: UUID, message: str, tenant_id: UUID | None = None) -> models.TaskLog:
    """Create an audit log entry for a task"""
    if tenant_id is None:
        task = db.query(models.Task).filter(models.Task.id == task_id).first()
        if task:
            tenant_id = task.tenant_id
        else:
            raise ValueError(f"Task {task_id} not found")
    
    log_entry = models.TaskLog(task_id=task_id, tenant_id=tenant_id, message=message)
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry

def has_active_aoa_job(db: Session, tenant_id: UUID) -> bool:
    """
    Check if there are any active (queued or in_progress) AOA tasks for a tenant.
    AOA tasks are identified by actions: aoa_connect, aoa_reset, aoa_toggle_dev_mode
    """
    from sqlalchemy import cast, String
    
    aoa_actions = ["aoa_connect", "aoa_reset", "aoa_toggle_dev_mode"]
    
    active_task = db.query(models.Task).filter(
        models.Task.tenant_id == tenant_id,
        models.Task.status.in_(["queued", "in_progress"]),
        cast(models.Task.payload["action"], String).in_(aoa_actions)
    ).first()
    
    return active_task is not None
