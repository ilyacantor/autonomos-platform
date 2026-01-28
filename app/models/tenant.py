"""
Tenant model - core multi-tenancy entity.
"""
from app.models.base import (
    uuid, Column, String, DateTime, func, UUID, relationship, Base
)


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    users = relationship("User", back_populates="tenant")
    tasks = relationship("Task", back_populates="tenant")
    task_logs = relationship("TaskLog", back_populates="tenant")
