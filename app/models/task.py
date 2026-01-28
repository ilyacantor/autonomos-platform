"""
Task models - background job processing.
"""
from app.models.base import (
    uuid, Column, String, JSON, DateTime, Integer, ForeignKey, func, UUID, relationship, Base
)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    status = Column(String, default="queued", nullable=False)
    payload = Column(JSON, nullable=False)
    result = Column(JSON, nullable=True)
    callback_url = Column(String, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=0, nullable=False)
    on_success_next_task = Column(JSON, nullable=True)
    next_task_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    tenant = relationship("Tenant", back_populates="tasks")
    logs = relationship("TaskLog", back_populates="task")


class TaskLog(Base):
    __tablename__ = "task_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    message = Column(String, nullable=False)

    task = relationship("Task", back_populates="logs")
    tenant = relationship("Tenant", back_populates="task_logs")
