"""
AOS Custom Checkpointer with Blob Offload

Implements ARB Condition 3: Checkpoint blobs >100KB are offloaded to S3/MinIO.
Wraps LangGraph's PostgresSaver with additional functionality.
"""

import json
import logging
import hashlib
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional, Iterator
from uuid import UUID
import sys

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models import AgentCheckpoint

logger = logging.getLogger(__name__)

# Blob offload threshold (ARB Condition 3)
BLOB_OFFLOAD_THRESHOLD_BYTES = 100 * 1024  # 100KB


class BlobStore(ABC):
    """
    Abstract blob store interface for checkpoint offload.
    Implementations: S3BlobStore, MinIOBlobStore, LocalBlobStore (dev).
    """

    @abstractmethod
    def put(self, key: str, data: bytes) -> None:
        """Store blob data."""
        pass

    @abstractmethod
    def get(self, key: str) -> Optional[bytes]:
        """Retrieve blob data."""
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete blob data."""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if blob exists."""
        pass


class LocalBlobStore(BlobStore):
    """
    Local filesystem blob store for development.
    NOT for production use.
    """

    def __init__(self, base_path: str = "/tmp/aos-checkpoints"):
        import os
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)

    def _path(self, key: str) -> str:
        import os
        # Sanitize key for filesystem
        safe_key = key.replace("/", "_").replace("\\", "_")
        return os.path.join(self.base_path, safe_key)

    def put(self, key: str, data: bytes) -> None:
        with open(self._path(key), 'wb') as f:
            f.write(data)

    def get(self, key: str) -> Optional[bytes]:
        try:
            with open(self._path(key), 'rb') as f:
                return f.read()
        except FileNotFoundError:
            return None

    def delete(self, key: str) -> None:
        import os
        try:
            os.remove(self._path(key))
        except FileNotFoundError:
            pass

    def exists(self, key: str) -> bool:
        import os
        return os.path.exists(self._path(key))


class S3BlobStore(BlobStore):
    """
    S3-compatible blob store for production.
    Works with AWS S3, MinIO, and other S3-compatible services.
    """

    def __init__(
        self,
        bucket: str,
        prefix: str = "checkpoints/",
        endpoint_url: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: str = "us-east-1"
    ):
        try:
            import boto3
        except ImportError:
            raise ImportError("boto3 required for S3BlobStore. Install with: pip install boto3")

        self.bucket = bucket
        self.prefix = prefix

        # Create S3 client
        client_kwargs = {"region_name": region_name}
        if endpoint_url:
            client_kwargs["endpoint_url"] = endpoint_url
        if aws_access_key_id:
            client_kwargs["aws_access_key_id"] = aws_access_key_id
            client_kwargs["aws_secret_access_key"] = aws_secret_access_key

        self.client = boto3.client("s3", **client_kwargs)

    def _key(self, key: str) -> str:
        return f"{self.prefix}{key}"

    def put(self, key: str, data: bytes) -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key=self._key(key),
            Body=data
        )

    def get(self, key: str) -> Optional[bytes]:
        try:
            response = self.client.get_object(
                Bucket=self.bucket,
                Key=self._key(key)
            )
            return response["Body"].read()
        except self.client.exceptions.NoSuchKey:
            return None

    def delete(self, key: str) -> None:
        try:
            self.client.delete_object(
                Bucket=self.bucket,
                Key=self._key(key)
            )
        except Exception:
            pass

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(
                Bucket=self.bucket,
                Key=self._key(key)
            )
            return True
        except Exception:
            return False


class AOSCheckpointer:
    """
    Custom checkpointer for the AOS Agentic Platform.

    Features:
    - PostgreSQL-backed checkpoint storage
    - Automatic blob offload for large checkpoints (>100KB)
    - LangGraph-compatible interface
    - Multi-tenant isolation
    """

    def __init__(
        self,
        db_session_factory,
        blob_store: Optional[BlobStore] = None,
        offload_threshold: int = BLOB_OFFLOAD_THRESHOLD_BYTES
    ):
        """
        Initialize the checkpointer.

        Args:
            db_session_factory: Callable that returns a SQLAlchemy Session
            blob_store: BlobStore for offloading large checkpoints
            offload_threshold: Size in bytes above which to offload (default 100KB)
        """
        self.db_session_factory = db_session_factory
        self.blob_store = blob_store or LocalBlobStore()
        self.offload_threshold = offload_threshold

    def _generate_blob_key(self, run_id: UUID, thread_ts: str) -> str:
        """Generate a unique blob key for a checkpoint."""
        return f"{run_id}/{thread_ts}.json"

    def put(
        self,
        config: dict,
        checkpoint: dict,
        metadata: Optional[dict] = None
    ) -> dict:
        """
        Save a checkpoint.

        Args:
            config: LangGraph config with thread_id, thread_ts, etc.
            checkpoint: The checkpoint data to save
            metadata: Optional metadata about the checkpoint

        Returns:
            Updated config with checkpoint info
        """
        thread_id = config["configurable"]["thread_id"]
        thread_ts = config["configurable"].get("thread_ts", datetime.utcnow().isoformat())
        parent_ts = config["configurable"].get("parent_ts")

        # Extract tenant and run info from thread_id (format: "run_<uuid>")
        run_id = UUID(thread_id.replace("run_", "")) if thread_id.startswith("run_") else UUID(thread_id)

        # Serialize checkpoint
        checkpoint_json = json.dumps(checkpoint, default=str)
        checkpoint_bytes = checkpoint_json.encode("utf-8")
        checkpoint_size = len(checkpoint_bytes)

        db = self.db_session_factory()
        try:
            # Determine if we need to offload
            if checkpoint_size > self.offload_threshold:
                # Offload to blob store
                blob_key = self._generate_blob_key(run_id, thread_ts)
                self.blob_store.put(blob_key, checkpoint_bytes)
                logger.info(f"Offloaded checkpoint blob: {blob_key} ({checkpoint_size} bytes)")

                # Create checkpoint record with blob reference
                cp = AgentCheckpoint(
                    run_id=run_id,
                    tenant_id=self._get_tenant_id(db, run_id),
                    thread_id=str(thread_id),
                    thread_ts=thread_ts,
                    parent_ts=parent_ts,
                    checkpoint_data=None,  # Data is in blob store
                    blob_key=blob_key,
                    blob_size_bytes=checkpoint_size,
                    step_number=metadata.get("step", 0) if metadata else 0
                )
            else:
                # Store inline
                cp = AgentCheckpoint(
                    run_id=run_id,
                    tenant_id=self._get_tenant_id(db, run_id),
                    thread_id=str(thread_id),
                    thread_ts=thread_ts,
                    parent_ts=parent_ts,
                    checkpoint_data=checkpoint,
                    blob_key=None,
                    blob_size_bytes=None,
                    step_number=metadata.get("step", 0) if metadata else 0
                )

            db.add(cp)
            db.commit()

            # Return updated config
            return {
                **config,
                "configurable": {
                    **config["configurable"],
                    "thread_ts": thread_ts
                }
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save checkpoint: {e}")
            raise
        finally:
            db.close()

    def get(self, config: dict) -> Optional[dict]:
        """
        Retrieve a checkpoint.

        Args:
            config: LangGraph config with thread_id and optionally thread_ts

        Returns:
            The checkpoint data or None if not found
        """
        thread_id = config["configurable"]["thread_id"]
        thread_ts = config["configurable"].get("thread_ts")

        db = self.db_session_factory()
        try:
            query = db.query(AgentCheckpoint).filter(
                AgentCheckpoint.thread_id == str(thread_id)
            )

            if thread_ts:
                cp = query.filter(AgentCheckpoint.thread_ts == thread_ts).first()
            else:
                # Get latest checkpoint
                cp = query.order_by(AgentCheckpoint.created_at.desc()).first()

            if not cp:
                return None

            # Load checkpoint data
            if cp.blob_key:
                # Load from blob store
                blob_data = self.blob_store.get(cp.blob_key)
                if blob_data is None:
                    logger.error(f"Blob not found: {cp.blob_key}")
                    return None
                return json.loads(blob_data.decode("utf-8"))
            else:
                return cp.checkpoint_data

        finally:
            db.close()

    def get_tuple(self, config: dict) -> Optional[tuple]:
        """
        Get checkpoint with config tuple (LangGraph compatibility).

        Returns:
            Tuple of (config, checkpoint) or None
        """
        checkpoint = self.get(config)
        if checkpoint is None:
            return None

        thread_id = config["configurable"]["thread_id"]
        db = self.db_session_factory()
        try:
            cp = db.query(AgentCheckpoint).filter(
                AgentCheckpoint.thread_id == str(thread_id)
            ).order_by(AgentCheckpoint.created_at.desc()).first()

            if not cp:
                return None

            updated_config = {
                **config,
                "configurable": {
                    **config["configurable"],
                    "thread_ts": cp.thread_ts,
                    "parent_ts": cp.parent_ts
                }
            }

            return (updated_config, checkpoint)
        finally:
            db.close()

    def list(
        self,
        config: dict,
        *,
        before: Optional[str] = None,
        limit: Optional[int] = None
    ) -> Iterator[tuple]:
        """
        List checkpoints for a thread.

        Args:
            config: LangGraph config with thread_id
            before: Only return checkpoints before this timestamp
            limit: Maximum number of checkpoints to return

        Yields:
            Tuples of (config, checkpoint)
        """
        thread_id = config["configurable"]["thread_id"]

        db = self.db_session_factory()
        try:
            query = db.query(AgentCheckpoint).filter(
                AgentCheckpoint.thread_id == str(thread_id)
            )

            if before:
                query = query.filter(AgentCheckpoint.thread_ts < before)

            query = query.order_by(AgentCheckpoint.created_at.desc())

            if limit:
                query = query.limit(limit)

            for cp in query.all():
                # Load checkpoint data
                if cp.blob_key:
                    blob_data = self.blob_store.get(cp.blob_key)
                    if blob_data is None:
                        continue
                    checkpoint = json.loads(blob_data.decode("utf-8"))
                else:
                    checkpoint = cp.checkpoint_data

                cp_config = {
                    **config,
                    "configurable": {
                        **config["configurable"],
                        "thread_ts": cp.thread_ts,
                        "parent_ts": cp.parent_ts
                    }
                }

                yield (cp_config, checkpoint)
        finally:
            db.close()

    def _get_tenant_id(self, db: Session, run_id: UUID) -> UUID:
        """Get tenant_id from the agent run."""
        from app.models import AgentRun
        run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
        if run:
            return run.tenant_id
        raise ValueError(f"Run {run_id} not found")

    def cleanup_old_checkpoints(
        self,
        run_id: UUID,
        keep_last: int = 10
    ) -> int:
        """
        Clean up old checkpoints for a run, keeping the most recent ones.

        Args:
            run_id: The run to clean up
            keep_last: Number of recent checkpoints to keep

        Returns:
            Number of checkpoints deleted
        """
        db = self.db_session_factory()
        try:
            # Get all checkpoints for this run
            all_cps = db.query(AgentCheckpoint).filter(
                AgentCheckpoint.run_id == run_id
            ).order_by(AgentCheckpoint.created_at.desc()).all()

            # Delete old ones
            deleted = 0
            for cp in all_cps[keep_last:]:
                # Delete blob if exists
                if cp.blob_key:
                    self.blob_store.delete(cp.blob_key)
                db.delete(cp)
                deleted += 1

            db.commit()
            return deleted
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to cleanup checkpoints: {e}")
            raise
        finally:
            db.close()


def create_checkpointer(
    db_session_factory,
    blob_store_type: str = "local",
    **blob_store_kwargs
) -> AOSCheckpointer:
    """
    Factory function to create a checkpointer with appropriate blob store.

    Args:
        db_session_factory: SQLAlchemy session factory
        blob_store_type: "local", "s3", or "minio"
        **blob_store_kwargs: Arguments for the blob store

    Returns:
        Configured AOSCheckpointer
    """
    if blob_store_type == "local":
        blob_store = LocalBlobStore(
            base_path=blob_store_kwargs.get("base_path", "/tmp/aos-checkpoints")
        )
    elif blob_store_type in ("s3", "minio"):
        blob_store = S3BlobStore(**blob_store_kwargs)
    else:
        raise ValueError(f"Unknown blob store type: {blob_store_type}")

    return AOSCheckpointer(
        db_session_factory=db_session_factory,
        blob_store=blob_store
    )
