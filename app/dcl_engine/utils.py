"""
Utility functions for DCL Engine.
"""
import os
import glob
import yaml
import warnings
import pandas as pd
from pathlib import Path
from typing import Dict, Any


# Use paths relative to this module's directory
DCL_BASE_PATH = Path(__file__).parent
DB_PATH = str(DCL_BASE_PATH / "registry.duckdb")
ONTOLOGY_PATH = str(DCL_BASE_PATH / "ontology" / "catalog.yml")
AGENTS_CONFIG_PATH = str(DCL_BASE_PATH / "agents" / "config.yml")
SCHEMAS_DIR = str(DCL_BASE_PATH / "schemas")

# Configuration constants
CONF_THRESHOLD = 0.70
AUTO_PUBLISH_PARTIAL = True
AUTH_ENABLED = False  # Set to True to enable authentication, False to bypass


def load_ontology():
    """Load ontology from YAML file."""
    with open(ONTOLOGY_PATH, "r") as f:
        return yaml.safe_load(f)


def load_agents_config():
    """Load agents configuration from YAML file."""
    try:
        with open(AGENTS_CONFIG_PATH, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        # Note: logging is handled by caller
        return {"agents": {}}


def infer_types(df: pd.DataFrame) -> Dict[str, str]:
    """Infer SQL types from pandas DataFrame columns."""
    mapping = {}
    for col in df.columns:
        series = df[col]
        if pd.api.types.is_integer_dtype(series):
            mapping[col] = "integer"
        elif pd.api.types.is_float_dtype(series):
            mapping[col] = "numeric"
        else:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    pd.to_datetime(series.dropna().head(50),
                                   format="%Y-%m-%d %H:%M:%S",
                                   errors="raise")
                mapping[col] = "datetime"
            except Exception:
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        pd.to_datetime(series.dropna().head(50), errors="coerce")
                    mapping[col] = "datetime"
                except Exception:
                    mapping[col] = "string"
    return mapping


def snapshot_tables_from_dir(source_key: str, dir_path: str) -> Dict[str, Any]:
    """Snapshot CSV tables from a directory."""
    tables = {}
    for path in glob.glob(os.path.join(dir_path, "*.csv")):
        tname = os.path.splitext(os.path.basename(path))[0]
        df = pd.read_csv(path)
        tables[tname] = {
            "path": path,
            "schema": infer_types(df),
            "samples": df.head(8).to_dict(orient="records")
        }
    return tables


def mk_sql_expr(src: Any, transform: str):
    """Generate SQL expression for field transformation."""
    if isinstance(src, list):
        parts = " || ' ' || ".join([f"COALESCE({c}, '')" for c in src])
        return parts + " AS value"
    if transform.startswith("cast"):
        return f"CAST({src} AS DOUBLE) AS value"
    if transform.startswith("parse_timestamp"):
        return f"TRY_STRPTIME({src}, '%Y-%m-%d %H:%M:%S') AS value"
    if transform.startswith("lower") or transform == 'lower_trim':
        return f"LOWER(TRIM({src})) AS value"
    return f"{src} AS value"
