"""
FileSource Connector Adapter

Provides a consistent interface for managing file-based data source connections.
Supports CSV, JSON, and YAML file formats.
Implements validation, connection testing, schema extraction, and health checks.
"""

import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


async def validate_config(config: dict) -> bool:
    """
    Validate FileSource connector configuration.
    
    Args:
        config: Configuration dictionary with file source details
                Expected keys: file_path, format
                
    Returns:
        True if configuration is valid, False otherwise
        
    Example:
        config = {
            "file_path": "/path/to/data.csv",
            "format": "csv"
        }
    """
    try:
        required_fields = ["file_path", "format"]
        
        if not isinstance(config, dict):
            logger.error("Config must be a dictionary")
            return False
        
        missing_fields = [field for field in required_fields if field not in config]
        if missing_fields:
            logger.error(f"Missing required fields: {missing_fields}")
            return False
        
        valid_formats = ["csv", "json", "yaml", "yml"]
        file_format = config["format"].lower()
        
        if file_format not in valid_formats:
            logger.error(f"Invalid format '{file_format}'. Must be one of: {valid_formats}")
            return False
        
        file_path = Path(config["file_path"])
        if not file_path.suffix:
            logger.warning("File path has no extension")
        
        logger.info("FileSource config validation passed")
        return True
        
    except Exception as e:
        logger.error(f"Error validating FileSource config: {e}")
        return False


async def test_connection(config: dict) -> dict:
    """
    Test file accessibility and format compatibility.
    
    Args:
        config: Configuration dictionary with file source details
        
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
        
        file_path = Path(config["file_path"])
        logger.info(f"Testing FileSource connection for: {file_path}")
        
        file_exists = file_path.exists() if file_path.is_absolute() else False
        
        return {
            "success": True,
            "message": f"File source test successful (mock, file_exists={file_exists})",
            "details": {
                "file_path": str(file_path),
                "format": config["format"],
                "file_exists": file_exists,
                "mock": True
            }
        }
        
    except Exception as e:
        logger.error(f"Error testing FileSource connection: {e}")
        return {
            "success": False,
            "message": f"Connection test failed: {str(e)}",
            "details": None
        }


async def get_schema(config: dict) -> dict:
    """
    Extract schema/structure from file source.
    
    Args:
        config: Configuration dictionary with file source details
        
    Returns:
        Dictionary containing the schema structure
        {
            "columns": List[dict] (for CSV/tabular),
            "structure": dict (for JSON/YAML),
            "format": str,
            "mock": bool
        }
    """
    try:
        if not await validate_config(config):
            return {
                "error": "Invalid configuration",
                "columns": [],
                "format": None
            }
        
        file_path = Path(config["file_path"])
        file_format = config["format"].lower()
        
        logger.info(f"Fetching schema from FileSource: {file_path} (format: {file_format})")
        
        if file_format == "csv":
            mock_schema = {
                "columns": [
                    {"name": "id", "type": "string", "nullable": False},
                    {"name": "name", "type": "string", "nullable": True},
                    {"name": "email", "type": "string", "nullable": True},
                    {"name": "created_at", "type": "datetime", "nullable": True}
                ],
                "format": "csv",
                "row_count_estimate": 100,
                "mock": True,
                "file_path": str(file_path)
            }
        elif file_format in ["json", "yaml", "yml"]:
            mock_schema = {
                "structure": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "name": {"type": "string"},
                            "email": {"type": "string"},
                            "created_at": {"type": "string", "format": "date-time"}
                        }
                    }
                },
                "format": file_format,
                "mock": True,
                "file_path": str(file_path)
            }
        else:
            mock_schema = {
                "error": f"Unsupported format: {file_format}",
                "format": file_format
            }
        
        return mock_schema
        
    except Exception as e:
        logger.error(f"Error fetching FileSource schema: {e}")
        return {
            "error": str(e),
            "columns": [],
            "format": config.get("format")
        }


async def health_check(config: dict) -> dict:
    """
    Check health status of file source.
    
    Args:
        config: Configuration dictionary with file source details
        
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
        
        file_path = Path(config["file_path"])
        logger.info(f"Performing health check on FileSource: {file_path}")
        
        file_accessible = True
        error_message = None
        
        if file_path.is_absolute() and not file_path.exists():
            file_accessible = False
            error_message = f"File not found: {file_path}"
        
        response_time = (time.time() - start_time) * 1000
        
        if not file_accessible:
            return {
                "status": "down",
                "response_time_ms": response_time,
                "error_message": error_message
            }
        
        if response_time > 1000:
            return {
                "status": "degraded",
                "response_time_ms": response_time,
                "error_message": "File access time exceeds threshold"
            }
        
        return {
            "status": "healthy",
            "response_time_ms": response_time,
            "error_message": None
        }
        
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        logger.error(f"Health check failed for FileSource: {e}")
        return {
            "status": "down",
            "response_time_ms": response_time,
            "error_message": str(e)
        }
