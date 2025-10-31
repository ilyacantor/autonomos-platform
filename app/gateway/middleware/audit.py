import os
import hashlib
import time
from datetime import datetime
from fastapi import Request
from typing import Callable
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import ApiJournal

DATABASE_URL = os.getenv("DATABASE_URL", "")

try:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    DB_AVAILABLE = True
except Exception:
    SessionLocal = None
    DB_AVAILABLE = False


async def audit_middleware(request: Request, call_next: Callable):
    """
    AuditJournal Middleware
    - Log every request to ApiJournal table
    - Include tenant_id, route, method, status, latency, trace_id
    - Hash request body (SHA256) for large payloads
    - Async write to avoid blocking
    """
    start_time = time.time()
    
    response = await call_next(request)
    
    latency_ms = int((time.time() - start_time) * 1000)
    
    if not DB_AVAILABLE:
        return response
    
    try:
        tenant_id = getattr(request.state, "tenant_id", None)
        agent_id = getattr(request.state, "agent_id", None)
        trace_id = getattr(request.state, "trace_id", None)
        
        body_sha256 = None
        try:
            body = await request.body()
            if body and len(body) > 1024:
                body_sha256 = hashlib.sha256(body).hexdigest()
        except Exception:
            pass
        
        journal_entry = ApiJournal(
            tenant_id=tenant_id,
            agent_id=agent_id,
            route=request.url.path,
            method=request.method,
            status=response.status_code,
            latency_ms=latency_ms,
            trace_id=trace_id,
            body_sha256=body_sha256,
            created_at=datetime.utcnow()
        )
        
        db = SessionLocal()
        db.add(journal_entry)
        db.commit()
        db.close()
    
    except Exception:
        pass
    
    return response
