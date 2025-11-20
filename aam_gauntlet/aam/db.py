"""Database layer for metrics and DLQ storage using SQLite."""
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from pathlib import Path


class MetricsDB:
    """SQLite database for storing AAM metrics and logs."""
    
    def __init__(self, db_path: str = "aam_metrics.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables."""
        with self._get_conn() as conn:
            # Connector logs table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS connector_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    connector_id TEXT NOT NULL,
                    service_id TEXT NOT NULL,
                    tenant_id TEXT,
                    timestamp DATETIME NOT NULL,
                    endpoint TEXT NOT NULL,
                    method TEXT NOT NULL,
                    http_status INTEGER,
                    error_class TEXT,
                    retries INTEGER DEFAULT 0,
                    idempotency_key TEXT,
                    latency_ms REAL,
                    request_data TEXT,
                    response_data TEXT
                )
            """)
            
            # Dead Letter Queue table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dlq_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    connector_id TEXT NOT NULL,
                    tenant_id TEXT,
                    timestamp DATETIME NOT NULL,
                    endpoint TEXT NOT NULL,
                    method TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    error_type TEXT NOT NULL,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    idempotency_key TEXT UNIQUE,
                    status TEXT DEFAULT 'pending'
                )
            """)
            
            # Token refresh logs
            conn.execute("""
                CREATE TABLE IF NOT EXISTS token_refresh_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    connector_id TEXT NOT NULL,
                    service_id TEXT NOT NULL,
                    tenant_id TEXT,
                    timestamp DATETIME NOT NULL,
                    old_token_expiry DATETIME,
                    new_token_expiry DATETIME,
                    success BOOLEAN,
                    error_message TEXT
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_connector_logs_timestamp ON connector_logs(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_connector_logs_connector ON connector_logs(connector_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_dlq_status ON dlq_entries(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_dlq_idempotency ON dlq_entries(idempotency_key)")
    
    @contextmanager
    def _get_conn(self):
        """Get database connection with context manager."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    
    def log_request(
        self,
        connector_id: str,
        service_id: str,
        tenant_id: Optional[str],
        endpoint: str,
        method: str,
        http_status: Optional[int],
        error_class: Optional[str],
        retries: int,
        idempotency_key: Optional[str],
        latency_ms: float,
        request_data: Optional[Dict] = None,
        response_data: Optional[Dict] = None
    ):
        """Log an API request."""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO connector_logs 
                (connector_id, service_id, tenant_id, timestamp, endpoint, method,
                 http_status, error_class, retries, idempotency_key, latency_ms,
                 request_data, response_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                connector_id, service_id, tenant_id, datetime.utcnow(),
                endpoint, method, http_status, error_class, retries,
                idempotency_key, latency_ms,
                json.dumps(request_data) if request_data else None,
                json.dumps(response_data) if response_data else None
            ))
    
    def add_to_dlq(
        self,
        connector_id: str,
        tenant_id: Optional[str],
        endpoint: str,
        method: str,
        payload: Dict,
        error_type: str,
        error_message: str,
        idempotency_key: Optional[str] = None,
        max_retries: int = 3
    ):
        """Add a failed request to the Dead Letter Queue."""
        with self._get_conn() as conn:
            try:
                conn.execute("""
                    INSERT INTO dlq_entries 
                    (connector_id, tenant_id, timestamp, endpoint, method, payload,
                     error_type, error_message, retry_count, max_retries, 
                     idempotency_key, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, 'pending')
                """, (
                    connector_id, tenant_id, datetime.utcnow(), endpoint, method,
                    json.dumps(payload), error_type, error_message, max_retries,
                    idempotency_key
                ))
                return True
            except sqlite3.IntegrityError:
                # Duplicate idempotency key
                return False
    
    def get_dlq_entries(
        self,
        status: str = "pending",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Retrieve entries from the DLQ."""
        with self._get_conn() as conn:
            cursor = conn.execute("""
                SELECT * FROM dlq_entries 
                WHERE status = ? 
                ORDER BY timestamp ASC 
                LIMIT ?
            """, (status, limit))
            
            entries = []
            for row in cursor:
                entry = dict(row)
                entry['payload'] = json.loads(entry['payload']) if entry['payload'] else None
                entries.append(entry)
            
            return entries
    
    def update_dlq_entry(
        self,
        dlq_id: int,
        status: str,
        retry_count: Optional[int] = None,
        error_message: Optional[str] = None
    ):
        """Update a DLQ entry status."""
        with self._get_conn() as conn:
            update_parts = ["status = ?"]
            params = [status]
            
            if retry_count is not None:
                update_parts.append("retry_count = ?")
                params.append(retry_count)
            
            if error_message is not None:
                update_parts.append("error_message = ?")
                params.append(error_message)
            
            params.append(dlq_id)
            
            conn.execute(f"""
                UPDATE dlq_entries 
                SET {', '.join(update_parts)}
                WHERE id = ?
            """, params)
    
    def log_token_refresh(
        self,
        connector_id: str,
        service_id: str,
        tenant_id: Optional[str],
        old_expiry: Optional[datetime],
        new_expiry: Optional[datetime],
        success: bool,
        error_message: Optional[str] = None
    ):
        """Log a token refresh event."""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO token_refresh_logs 
                (connector_id, service_id, tenant_id, timestamp, 
                 old_token_expiry, new_token_expiry, success, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                connector_id, service_id, tenant_id, datetime.utcnow(),
                old_expiry, new_expiry, success, error_message
            ))
    
    def get_metrics_summary(
        self,
        connector_id: Optional[str] = None,
        last_minutes: int = 10
    ) -> Dict[str, Any]:
        """Get metrics summary for dashboard."""
        with self._get_conn() as conn:
            # Base query
            base_where = "WHERE timestamp > datetime('now', ?)"
            params = [f'-{last_minutes} minutes']
            
            if connector_id:
                base_where += " AND connector_id = ?"
                params.append(connector_id)
            
            # Total requests
            cursor = conn.execute(
                f"SELECT COUNT(*) as total FROM connector_logs {base_where}",
                params
            )
            total_requests = cursor.fetchone()['total']
            
            # Success/failure breakdown
            cursor = conn.execute(f"""
                SELECT 
                    COUNT(CASE WHEN http_status >= 200 AND http_status < 300 THEN 1 END) as success,
                    COUNT(CASE WHEN http_status >= 400 THEN 1 END) as failures
                FROM connector_logs {base_where}
            """, params)
            row = cursor.fetchone()
            
            # Error class breakdown
            cursor = conn.execute(f"""
                SELECT error_class, COUNT(*) as count
                FROM connector_logs 
                {base_where} AND error_class IS NOT NULL
                GROUP BY error_class
            """, params + (params[1:] if connector_id else []))
            error_breakdown = {row['error_class']: row['count'] for row in cursor}
            
            # Average latency
            cursor = conn.execute(f"""
                SELECT AVG(latency_ms) as avg_latency
                FROM connector_logs {base_where}
            """, params)
            avg_latency = cursor.fetchone()['avg_latency'] or 0
            
            # DLQ stats
            cursor = conn.execute("""
                SELECT status, COUNT(*) as count
                FROM dlq_entries
                GROUP BY status
            """)
            dlq_stats = {row['status']: row['count'] for row in cursor}
            
            # Token refresh stats
            cursor = conn.execute(f"""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN success = 1 THEN 1 END) as successful
                FROM token_refresh_logs {base_where}
            """, params)
            token_stats = cursor.fetchone()
            
            return {
                "total_requests": total_requests,
                "successful_requests": row['success'],
                "failed_requests": row['failures'],
                "success_rate": (row['success'] / total_requests * 100) if total_requests > 0 else 0,
                "error_breakdown": error_breakdown,
                "avg_latency_ms": round(avg_latency, 2),
                "dlq_stats": dlq_stats,
                "token_refreshes": {
                    "total": token_stats['total'],
                    "successful": token_stats['successful']
                }
            }