"""
AAM Connector Adapters

This package provides consistent adapters for managing different data source types
in the Adaptive API Mesh (AAM) system.

Each adapter implements a common interface:
- validate_config(config: dict) -> bool
- test_connection(config: dict) -> dict
- get_schema(config: dict) -> dict
- health_check(config: dict) -> dict

Available Adapters:
- salesforce_adapter: Salesforce CRM integration
- supabase_adapter: Supabase (PostgreSQL) integration
- mongodb_adapter: MongoDB database integration
- filesource_adapter: File-based data sources (CSV, JSON, YAML)

Usage:
    from aam-hybrid.connectors import salesforce_adapter
    
    config = {
        "instance_url": "https://mycompany.salesforce.com",
        "access_token": "..."
    }
    
    is_valid = await salesforce_adapter.validate_config(config)
    if is_valid:
        result = await salesforce_adapter.test_connection(config)
        schema = await salesforce_adapter.get_schema(config)
        health = await salesforce_adapter.health_check(config)
"""

from . import salesforce_adapter
from . import supabase_adapter
from . import mongodb_adapter
from . import filesource_adapter

__all__ = [
    "salesforce_adapter",
    "supabase_adapter",
    "mongodb_adapter",
    "filesource_adapter",
]

__version__ = "0.1.0"
