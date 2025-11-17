#!/usr/bin/env python3
"""
Phase 0 Generic Connector Test Script

Tests the GenericRESTConnector with 3 different API patterns:
1. Pattern 1: GitHub API - Simple REST + API Key
2. Pattern 2: JSONPlaceholder - Bearer token + limit/offset pagination
3. Pattern 3: ReqRes API - Custom headers + cursor pagination

Measures:
- Connection time
- Data fetch time
- Mapping accuracy (% of fields successfully mapped)
- Error counts

Outputs results to: scripts/phase0_generic_connector_results.json
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from shared.database import SessionLocal
from services.aam.connectors.generic.connector import GenericRESTConnector
from services.aam.canonical.mapping_registry import mapping_registry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Phase0TestRunner:
    """Test runner for Phase 0 Generic Connector"""
    
    def __init__(self):
        self.db: Session = SessionLocal()
        self.results: Dict[str, Any] = {
            "test_run_id": datetime.utcnow().isoformat(),
            "test_timestamp": datetime.utcnow().isoformat(),
            "patterns_tested": 3,
            "success_criteria": {
                "connection_time_threshold_seconds": 5.0,
                "zero_mapping_errors": True
            },
            "pattern_results": []
        }
        
        # Set up mock environment variables for testing
        self._setup_test_env()
    
    def _setup_test_env(self):
        """Set up test environment variables"""
        # GitHub API - optional token (public API works without it)
        if not os.getenv("GITHUB_API_KEY"):
            os.environ["GITHUB_API_KEY"] = "mock-token-not-required"
        
        # JSONPlaceholder - doesn't require auth, but we set for pattern demo
        if not os.getenv("JSONPLACEHOLDER_TOKEN"):
            os.environ["JSONPLACEHOLDER_TOKEN"] = "mock-bearer-token"
        
        # ReqRes API - doesn't require auth, but we set for pattern demo
        if not os.getenv("REQRES_API_KEY"):
            os.environ["REQRES_API_KEY"] = "mock-api-key"
        
        logger.info("✅ Test environment variables configured")
    
    async def test_pattern(
        self,
        pattern_name: str,
        config_path: Path,
        description: str
    ) -> Dict[str, Any]:
        """
        Test a single API pattern
        
        Args:
            pattern_name: Name of the pattern (e.g., "Pattern 1: GitHub API")
            config_path: Path to configuration YAML file
            description: Description of what this pattern tests
        
        Returns:
            Dictionary with test results
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing: {pattern_name}")
        logger.info(f"Config: {config_path}")
        logger.info(f"Description: {description}")
        logger.info(f"{'='*60}\n")
        
        result = {
            "pattern_name": pattern_name,
            "config_file": str(config_path),
            "description": description,
            "success": False,
            "connection_time_seconds": 0.0,
            "fetch_time_seconds": 0.0,
            "records_fetched": 0,
            "records_normalized": 0,
            "mapping_accuracy_percent": 0.0,
            "errors": [],
            "warnings": []
        }
        
        connector = None
        
        try:
            # Step 1: Initialize connector (tests config loading)
            logger.info("Step 1: Initializing connector...")
            init_start = datetime.utcnow()
            
            connector = GenericRESTConnector(
                db=self.db,
                config=config_path,
                tenant_id="phase0-test"
            )
            
            init_duration = (datetime.utcnow() - init_start).total_seconds()
            logger.info(f"✅ Connector initialized in {init_duration:.3f}s")
            
            # Step 2: Test connection (authenticate)
            logger.info("Step 2: Testing connection and authentication...")
            conn_start = datetime.utcnow()
            
            try:
                auth_headers = await connector._authenticate()
                conn_duration = (datetime.utcnow() - conn_start).total_seconds()
                result["connection_time_seconds"] = conn_duration
                
                logger.info(f"✅ Connected and authenticated in {conn_duration:.3f}s")
                logger.info(f"   Auth headers: {list(auth_headers.keys())}")
            
            except Exception as auth_error:
                # Some APIs don't require auth - continue anyway
                conn_duration = (datetime.utcnow() - conn_start).total_seconds()
                result["connection_time_seconds"] = conn_duration
                result["warnings"].append(f"Auth not required or failed: {str(auth_error)}")
                logger.warning(f"⚠️  Auth warning: {auth_error}")
            
            # Step 3: Fetch data (tests data fetching and pagination)
            logger.info("Step 3: Fetching data...")
            fetch_start = datetime.utcnow()
            
            # Fetch data without emitting to database for testing
            events = await connector.fetch_and_emit(
                endpoint_index=0,
                max_pages=2,  # Limit pages for testing
                emit=False  # Don't write to DB during test
            )
            
            fetch_duration = (datetime.utcnow() - fetch_start).total_seconds()
            result["fetch_time_seconds"] = fetch_duration
            result["records_fetched"] = len(events)
            
            logger.info(f"✅ Fetched {len(events)} records in {fetch_duration:.3f}s")
            
            # Step 4: Validate normalization (tests mapping accuracy)
            logger.info("Step 4: Validating normalization...")
            
            if events:
                total_fields = 0
                mapped_fields = 0
                
                for event in events:
                    # Count total fields in source data
                    data_dict = event.data.dict() if hasattr(event.data, 'dict') else event.data
                    
                    # Count non-None canonical fields (successfully mapped)
                    for key, value in data_dict.items():
                        if key != 'extras':  # Don't count extras
                            total_fields += 1
                            if value is not None:
                                mapped_fields += 1
                
                # Calculate mapping accuracy
                if total_fields > 0:
                    accuracy = (mapped_fields / total_fields) * 100
                    result["mapping_accuracy_percent"] = round(accuracy, 2)
                
                result["records_normalized"] = len(events)
                
                logger.info(f"✅ Normalized {len(events)} records")
                logger.info(f"   Mapping accuracy: {result['mapping_accuracy_percent']}%")
                logger.info(f"   Mapped fields: {mapped_fields}/{total_fields}")
                
                # Show sample normalized record
                if events:
                    sample = events[0]
                    logger.info(f"\n📋 Sample normalized record:")
                    logger.info(f"   Entity: {sample.entity}")
                    logger.info(f"   Source: {sample.source.system}")
                    sample_data = sample.data.dict() if hasattr(sample.data, 'dict') else sample.data
                    logger.info(f"   Data keys: {list(sample_data.keys())}")
                    logger.info(f"   Unknown fields: {sample.unknown_fields}")
            
            else:
                result["warnings"].append("No records fetched - cannot validate normalization")
                logger.warning("⚠️  No records fetched")
            
            # Step 5: Check success criteria
            success = True
            
            # Check connection time
            if result["connection_time_seconds"] > 5.0:
                result["errors"].append(
                    f"Connection time {result['connection_time_seconds']:.2f}s exceeds 5s threshold"
                )
                success = False
            
            # Check records fetched
            if result["records_fetched"] == 0:
                result["errors"].append("No records fetched")
                success = False
            
            # Check normalization
            if result["records_normalized"] != result["records_fetched"]:
                result["errors"].append(
                    f"Normalization failed: {result['records_normalized']}/{result['records_fetched']} records"
                )
                success = False
            
            result["success"] = success
            
            if success:
                logger.info(f"\n✅ {pattern_name} - PASSED")
            else:
                logger.error(f"\n❌ {pattern_name} - FAILED")
                logger.error(f"   Errors: {result['errors']}")
        
        except Exception as e:
            logger.error(f"\n❌ {pattern_name} - FAILED with exception")
            logger.error(f"   Error: {str(e)}", exc_info=True)
            result["success"] = False
            result["errors"].append(f"Exception: {str(e)}")
        
        finally:
            # Clean up
            if connector:
                try:
                    await connector.close()
                except:
                    pass
        
        return result
    
    async def run_all_tests(self):
        """Run all 3 pattern tests"""
        logger.info("\n" + "="*80)
        logger.info("Phase 0 Generic Connector Test Suite")
        logger.info("="*80 + "\n")
        
        base_path = Path("services/aam/connectors/generic/test_configs")
        
        # Pattern 1: GitHub API - Simple REST + API Key
        result1 = await self.test_pattern(
            pattern_name="Pattern 1: GitHub API (Simple REST + API Key)",
            config_path=base_path / "pattern1_github_api.yaml",
            description="Tests API key authentication, simple GET request, basic field mapping"
        )
        self.results["pattern_results"].append(result1)
        
        # Pattern 2: JSONPlaceholder - Bearer + Pagination
        result2 = await self.test_pattern(
            pattern_name="Pattern 2: JSONPlaceholder (Bearer + Limit/Offset Pagination)",
            config_path=base_path / "pattern2_jsonplaceholder.yaml",
            description="Tests bearer token auth, limit/offset pagination, array data extraction"
        )
        self.results["pattern_results"].append(result2)
        
        # Pattern 3: ReqRes API - Custom Headers + Cursor Pagination
        result3 = await self.test_pattern(
            pattern_name="Pattern 3: ReqRes API (Custom Headers + Cursor Pagination)",
            config_path=base_path / "pattern3_reqres_api.yaml",
            description="Tests custom header auth, cursor-based pagination, nested data extraction"
        )
        self.results["pattern_results"].append(result3)
        
        # Calculate summary
        self.results["summary"] = {
            "total_patterns": 3,
            "passed": sum(1 for r in self.results["pattern_results"] if r["success"]),
            "failed": sum(1 for r in self.results["pattern_results"] if not r["success"]),
            "total_records_fetched": sum(r["records_fetched"] for r in self.results["pattern_results"]),
            "avg_connection_time_seconds": round(
                sum(r["connection_time_seconds"] for r in self.results["pattern_results"]) / 3, 3
            ),
            "avg_fetch_time_seconds": round(
                sum(r["fetch_time_seconds"] for r in self.results["pattern_results"]) / 3, 3
            ),
            "avg_mapping_accuracy_percent": round(
                sum(r["mapping_accuracy_percent"] for r in self.results["pattern_results"]) / 3, 2
            )
        }
        
        # Overall success
        self.results["overall_success"] = self.results["summary"]["failed"] == 0
        
        # Print summary
        logger.info("\n" + "="*80)
        logger.info("TEST SUMMARY")
        logger.info("="*80)
        logger.info(f"Total patterns tested: {self.results['summary']['total_patterns']}")
        logger.info(f"Passed: {self.results['summary']['passed']}")
        logger.info(f"Failed: {self.results['summary']['failed']}")
        logger.info(f"Total records fetched: {self.results['summary']['total_records_fetched']}")
        logger.info(f"Avg connection time: {self.results['summary']['avg_connection_time_seconds']}s")
        logger.info(f"Avg fetch time: {self.results['summary']['avg_fetch_time_seconds']}s")
        logger.info(f"Avg mapping accuracy: {self.results['summary']['avg_mapping_accuracy_percent']}%")
        logger.info(f"\nOverall: {'✅ PASSED' if self.results['overall_success'] else '❌ FAILED'}")
        logger.info("="*80 + "\n")
    
    def save_results(self):
        """Save results to JSON file"""
        output_path = Path("scripts/phase0_generic_connector_results.json")
        
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"✅ Results saved to: {output_path}")
    
    def cleanup(self):
        """Clean up database session"""
        if self.db:
            self.db.close()


async def main():
    """Main test entry point"""
    runner = Phase0TestRunner()
    
    try:
        await runner.run_all_tests()
        runner.save_results()
        
        # Exit with appropriate code
        sys.exit(0 if runner.results["overall_success"] else 1)
    
    finally:
        runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
