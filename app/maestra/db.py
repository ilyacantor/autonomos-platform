"""
Database connection for Maestra.
Connects to the same Supabase PG as DCL.
Uses psycopg2 (sync) to match DCL's pattern.
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor


def get_connection():
    """Get a PG connection using SUPABASE_DB_URL."""
    url = os.environ.get("SUPABASE_DB_URL")
    if not url:
        raise RuntimeError(
            "SUPABASE_DB_URL not set. Maestra requires Supabase PG — "
            "set SUPABASE_DB_URL to the same connection string DCL uses."
        )
    return psycopg2.connect(url, cursor_factory=RealDictCursor)


def get_tenant_id() -> str:
    """Get tenant ID from environment."""
    tid = os.environ.get("TENANT_ID")
    if not tid:
        raise RuntimeError(
            "TENANT_ID not set. Maestra requires a tenant ID for multi-tenant isolation."
        )
    return tid
