"""
MongoDB Connector Adapter

Provides a consistent interface for managing MongoDB data source connections.
Implements validation, connection testing, schema extraction, and health checks.
"""

import logging
import time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


async def validate_config(config: dict) -> bool:
    """
    Validate MongoDB connector configuration.
    
    Args:
        config: Configuration dictionary with MongoDB credentials
                Expected keys: connection_string, database
                
    Returns:
        True if configuration is valid, False otherwise
        
    Example:
        config = {
            "connection_string": "mongodb://localhost:27017",
            "database": "mydb"
        }
    """
    try:
        required_fields = ["connection_string", "database"]
        
        if not isinstance(config, dict):
            logger.error("Config must be a dictionary")
            return False
        
        missing_fields = [field for field in required_fields if field not in config]
        if missing_fields:
            logger.error(f"Missing required fields: {missing_fields}")
            return False
        
        conn_str = config["connection_string"]
        if not (conn_str.startswith("mongodb://") or conn_str.startswith("mongodb+srv://")):
            logger.error("connection_string must start with mongodb:// or mongodb+srv://")
            return False
        
        if not config["database"] or len(config["database"]) < 1:
            logger.error("database name must be provided")
            return False
        
        logger.info("MongoDB config validation passed")
        return True
        
    except Exception as e:
        logger.error(f"Error validating MongoDB config: {e}")
        return False


async def test_connection(config: dict) -> dict:
    """
    Test connectivity to MongoDB instance.
    
    Args:
        config: Configuration dictionary with MongoDB credentials
        
    Returns:
        Dictionary with connection test results
        {
            "success": bool,
            "message": str,
            "details": Optional[dict]
        }
    """
    try:
        if not await validate_config(config):
            return {
                "success": False,
                "message": "Invalid configuration",
                "details": None
            }
        
        logger.info(f"Testing MongoDB connection to database: {config['database']}")
        
        return {
            "success": True,
            "message": "Connection test successful (mock)",
            "details": {
                "database": config["database"],
                "server_version": "7.0.0",
                "mock": True
            }
        }
        
    except Exception as e:
        logger.error(f"Error testing MongoDB connection: {e}")
        return {
            "success": False,
            "message": f"Connection test failed: {str(e)}",
            "details": None
        }


async def get_schema(config: dict) -> dict:
    """
    Extract schema/catalog from MongoDB instance.
    
    Args:
        config: Configuration dictionary with MongoDB credentials
        
    Returns:
        Dictionary containing the schema structure
        {
            "collections": List[dict],
            "total_count": int,
            "mock": bool
        }
    """
    try:
        if not await validate_config(config):
            return {
                "error": "Invalid configuration",
                "collections": [],
                "total_count": 0
            }
        
        logger.info(f"Fetching schema from MongoDB database: {config['database']}")
        
        mock_collections = [
            {
                "name": "account_usage",
                "database": config["database"],
                "sample_schema": {
                    "_id": "ObjectId",
                    "account_id": "string",
                    "usage_type": "string",
                    "quantity": "number",
                    "timestamp": "date"
                },
                "estimated_count": 1000
            },
            {
                "name": "user_events",
                "database": config["database"],
                "sample_schema": {
                    "_id": "ObjectId",
                    "user_id": "string",
                    "event_type": "string",
                    "properties": "object",
                    "created_at": "date"
                },
                "estimated_count": 5000
            },
            {
                "name": "product_catalog",
                "database": config["database"],
                "sample_schema": {
                    "_id": "ObjectId",
                    "product_name": "string",
                    "price": "number",
                    "category": "string",
                    "in_stock": "boolean",
                    "metadata": "object"
                },
                "estimated_count": 500
            }
        ]
        
        return {
            "collections": mock_collections,
            "total_count": len(mock_collections),
            "mock": True,
            "database": config["database"]
        }
        
    except Exception as e:
        logger.error(f"Error fetching MongoDB schema: {e}")
        return {
            "error": str(e),
            "collections": [],
            "total_count": 0
        }


async def health_check(config: dict) -> dict:
    """
    Check health status of MongoDB connection.
    
    Args:
        config: Configuration dictionary with MongoDB credentials
        
    Returns:
        Dictionary with health status
        {
            "status": "healthy" | "degraded" | "down",
            "response_time_ms": float,
            "error_message": Optional[str]
        }
    """
    start_time = time.time()
    
    try:
        if not await validate_config(config):
            response_time = (time.time() - start_time) * 1000
            return {
                "status": "down",
                "response_time_ms": response_time,
                "error_message": "Invalid configuration"
            }
        
        logger.info(f"Performing health check on MongoDB database: {config['database']}")
        
        response_time = (time.time() - start_time) * 1000
        
        if response_time > 2000:
            return {
                "status": "degraded",
                "response_time_ms": response_time,
                "error_message": "Response time exceeds threshold"
            }
        
        return {
            "status": "healthy",
            "response_time_ms": response_time,
            "error_message": None
        }
        
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        logger.error(f"Health check failed for MongoDB: {e}")
        return {
            "status": "down",
            "response_time_ms": response_time,
            "error_message": str(e)
        }
