import httpx
import logging
from uuid import UUID
from redis import Redis
from rq import Worker, Queue, get_current_job
import asyncio

from app.config import settings
from app.database import SessionLocal
from app import crud, models

logger = logging.getLogger(__name__)

def send_callback(task_data: dict, callback_url: str, db, task_id):
    """
    Send task completion callback to the specified URL.
    This function handles errors gracefully - a failed callback
    does not affect the task status.
    """
    try:
        crud.create_task_log(db, task_id, f"Attempting to send callback to {callback_url}")
        response = httpx.post(
            callback_url,
            json=task_data,
            timeout=10.0
        )
        response.raise_for_status()
        crud.create_task_log(db, task_id, f"Successfully sent callback with status {response.status_code}")
        logger.info(f"Successfully sent callback to {callback_url} with status {response.status_code}")
    except Exception as e:
        crud.create_task_log(db, task_id, f"Failed to send callback: {str(e)}")
        logger.error(f"Failed to send callback to {callback_url}: {str(e)}")

def handle_post_to_slack(db, task_id, payload):
    """Handler for post_to_slack action"""
    channel = payload.get("channel", "#general")
    message = payload.get("message", "")
    
    slack_payload = {
        "text": message,
        "channel": channel
    }
    
    crud.create_task_log(db, task_id, f"Attempting to post message to Slack channel {channel}")
    
    response = httpx.post(
        settings.SLACK_WEBHOOK_URL,
        json=slack_payload,
        timeout=10.0
    )
    response.raise_for_status()
    
    crud.create_task_log(db, task_id, f"Successfully posted to Slack with status {response.status_code}")
    
    return {
        "message": "Successfully posted to Slack",
        "channel": channel,
        "slack_response_status": response.status_code
    }

def handle_aoa_connect(db, task_id, payload):
    """Handler for aoa_connect action - DCL v2 external service stub"""
    tenant_id = payload.get("tenant_id")
    sources = payload.get("sources", "")
    agents = payload.get("agents", "")
    
    crud.create_task_log(db, task_id, f"AOA connect for tenant {tenant_id} with sources={sources}, agents={agents}")
    logger.info(f"AOA connect for tenant {tenant_id} - DCL v2 external service")
    
    source_list = [s.strip() for s in sources.split(",") if s.strip()]
    agent_list = [a.strip() for a in agents.split(",") if a.strip()]
    
    crud.create_task_log(db, task_id, f"AOA connect acknowledged - DCL v2 external service")
    
    return {
        "message": "AOA connect acknowledged - DCL v2 external service",
        "tenant_id": tenant_id,
        "sources": source_list,
        "agents": agent_list,
        "ok": True,
        "note": "DCL v1 removed. Use DCL v2 external service for data orchestration."
    }

def handle_aoa_reset(db, task_id, payload):
    """Handler for aoa_reset action - DCL v2 external service stub"""
    tenant_id = payload.get("tenant_id")
    
    crud.create_task_log(db, task_id, f"AOA reset for tenant {tenant_id}")
    logger.info(f"AOA reset for tenant {tenant_id} - DCL v2 external service")
    
    crud.create_task_log(db, task_id, f"AOA reset acknowledged - DCL v2 external service")
    
    return {
        "message": "AOA reset acknowledged - DCL v2 external service",
        "tenant_id": tenant_id,
        "ok": True,
        "note": "DCL v1 removed. Use DCL v2 external service for data orchestration."
    }

def handle_aoa_toggle_dev_mode(db, task_id, payload):
    """Handler for aoa_toggle_dev_mode action - DCL v2 external service stub"""
    tenant_id = payload.get("tenant_id")
    enabled = payload.get("enabled", False)
    
    crud.create_task_log(db, task_id, f"AOA toggle dev mode for tenant {tenant_id}, enabled={enabled}")
    logger.info(f"AOA toggle dev mode for tenant {tenant_id} - DCL v2 external service")
    
    status = "enabled" if enabled else "disabled"
    crud.create_task_log(db, task_id, f"AOA toggle dev mode acknowledged - DCL v2 external service")
    
    return {
        "message": "AOA toggle dev mode acknowledged - DCL v2 external service",
        "tenant_id": tenant_id,
        "dev_mode": enabled,
        "status": status,
        "note": "DCL v1 removed. Use DCL v2 external service for data orchestration."
    }

def execute_task(task_id_str: str):
    """
    Worker function to process a task.
    This is the core background processing logic.
    """
    task_id = UUID(task_id_str)
    db = SessionLocal()
    
    try:
        task = db.query(models.Task).filter(models.Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        task.status = "in_progress"
        db.commit()
        crud.create_task_log(db, task_id, "Task execution started")
        
        payload = task.payload
        action = payload.get("action")
        
        result = None
        
        if action == "post_to_slack":
            result = handle_post_to_slack(db, task_id, payload)
        elif action == "aoa_connect":
            result = handle_aoa_connect(db, task_id, payload)
        elif action == "aoa_reset":
            result = handle_aoa_reset(db, task_id, payload)
        elif action == "aoa_toggle_dev_mode":
            result = handle_aoa_toggle_dev_mode(db, task_id, payload)
        else:
            raise ValueError(f"Unknown action: {action}")
        
        task.status = "success"
        task.result = result
        db.commit()
        
        task = db.query(models.Task).filter(models.Task.id == task_id).first()
        if task and task.on_success_next_task:
            crud.create_task_log(db, task_id, "Task succeeded, creating chained task")
            
            from app.schemas import TaskCreate
            next_task_data = TaskCreate(**task.on_success_next_task)
            next_task = crud.create_task(db, next_task_data, task.tenant_id)
            
            task.next_task_id = next_task.id
            db.commit()
            
            crud.create_task_log(db, task_id, f"Created and enqueued chained task {next_task.id}")
            
            from rq import Queue as RQQueue, Retry
            from redis import Redis as RedisClient
            import os
            
            # Use REDIS_URL if available (production), otherwise use host/port (development)
            REDIS_URL = os.getenv("REDIS_URL")
            if REDIS_URL:
                chain_redis_conn = RedisClient.from_url(REDIS_URL, decode_responses=False)
            else:
                chain_redis_conn = RedisClient(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)
            task_queue = RQQueue(connection=chain_redis_conn)
            
            retry_config = None
            if next_task_data.max_retries and next_task_data.max_retries > 0:
                retry_config = Retry(max=next_task_data.max_retries, interval=[10, 30, 60])
            
            task_queue.enqueue(
                execute_task,
                str(next_task.id),
                job_timeout=next_task_data.timeout_seconds,
                retry=retry_config
            )
        
    except Exception as e:
        error_result = {"error": str(e), "error_type": type(e).__name__}
        crud.create_task_log(db, task_id, f"Task failed with error: {str(e)}")
        
        task = db.query(models.Task).filter(models.Task.id == task_id).first()
        current_job = get_current_job()
        
        if task and current_job:
            if task.retry_count < task.max_retries:
                task.retry_count = task.retry_count + 1
                db.commit()
                crud.create_task_log(db, task_id, f"Scheduling retry {task.retry_count}/{task.max_retries}")
                logger.warning(f"Task {task_id} failed, will retry ({task.retry_count}/{task.max_retries})")
                db.close()
                raise
        
        task.status = "failed"
        task.result = error_result
        db.commit()
        crud.create_task_log(db, task_id, "Task permanently failed after all retries")
        logger.error(f"Task {task_id} permanently failed: {str(e)}")
    finally:
        final_task = db.query(models.Task).filter(models.Task.id == task_id).first()
        if final_task and final_task.callback_url:
            task_data = {
                "id": str(final_task.id),
                "status": final_task.status,
                "payload": final_task.payload,
                "result": final_task.result,
                "callback_url": final_task.callback_url,
                "created_at": final_task.created_at.isoformat(),
                "updated_at": final_task.updated_at.isoformat()
            }
            send_callback(task_data, final_task.callback_url, db, task_id)
        
        db.close()

if __name__ == "__main__":
    import os
    import ssl as ssl_module
    
    # Use REDIS_URL if available (production), otherwise use host/port (development)
    REDIS_URL = os.getenv("REDIS_URL")
    if REDIS_URL:
        # Respect the URL scheme - use TLS if rediss://, plain if redis://
        if REDIS_URL.startswith("rediss://"):
            # TLS/SSL connection with certificate validation
            CA_CERT_PATH = os.path.join(os.path.dirname(__file__), "..", "certs", "redis_ca.pem")
            redis_conn = Redis.from_url(
                REDIS_URL, 
                decode_responses=False, 
                ssl_cert_reqs=ssl_module.CERT_REQUIRED,
                ssl_ca_certs=CA_CERT_PATH
            )
            logger.info("Worker using external Redis with TLS/SSL certificate validation")
        else:
            # Plain connection
            redis_conn = Redis.from_url(REDIS_URL, decode_responses=False)
            logger.warning("Worker using non-TLS Redis - ensure this is intentional for dev/local only")
    else:
        logger.info(f"Worker using local Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        redis_conn = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)
    
    queue = Queue(connection=redis_conn)
    worker = Worker([queue], connection=redis_conn)
    
    logger.info("Starting RQ worker...")
    worker.work()
