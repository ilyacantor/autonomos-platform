"""
DuckDB database operations for DCL Engine.
Handles table creation, queries, and schema inspection.
"""
import pandas as pd
from typing import Dict, Any, List


def register_src_views(con, source_key: str, tables: Dict[str, Any]):
    """Register source tables as DuckDB views."""
    for tname, info in tables.items():
        path = info["path"]
        view_name = f"src_{source_key}_{tname}"
        con.sql(f"CREATE OR REPLACE VIEW {view_name} AS SELECT * FROM read_csv_auto('{path}')")


def preview_table(con, name: str, limit: int = 6) -> List[Dict[str, Any]]:
    """Preview a table with limited rows, handling NaN and timestamp values."""
    try:
        df = con.sql(f"SELECT * FROM {name} LIMIT {limit}").to_df()
        records = df.to_dict(orient="records")
        for record in records:
            for key, value in record.items():
                if pd.isna(value):
                    record[key] = None
                elif isinstance(value, (pd.Timestamp, pd.Timedelta)):
                    record[key] = str(value)
        return records
    except Exception:
        return []
