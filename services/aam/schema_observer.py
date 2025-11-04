"""
Schema Observer for AAM
Fingerprints schemas from Supabase and MongoDB to detect drift
"""
import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from sqlalchemy import create_engine, text
from pymongo import MongoClient

logger = logging.getLogger(__name__)


class SchemaObserver:
    """
    Schema Observer for detecting drift in Supabase and MongoDB
    
    Features:
    - Fingerprint Postgres schemas via information_schema
    - Fingerprint MongoDB schemas via document sampling
    - Detect drift by comparing to stored fingerprints
    - Generate drift tickets for repair
    """
    
    def __init__(self):
        self.stored_fingerprints: Dict[str, Any] = {}
    
    def fingerprint_supabase(self) -> List[Dict[str, Any]]:
        """
        Fingerprint Supabase (Postgres) schema
        
        Returns:
            List of drift tickets if drift detected
        """
        supabase_db_url = os.getenv("SUPABASE_DB_URL", "")
        if not supabase_db_url:
            logger.warning("SUPABASE_DB_URL not set, skipping Supabase fingerprinting")
            return []
        
        schema = os.getenv("SUPABASE_SCHEMA", "public")
        
        try:
            engine = create_engine(supabase_db_url, pool_pre_ping=True)
            
            with engine.connect() as conn:
                # Query information_schema for table and column information
                result = conn.execute(text(f"""
                    SELECT 
                        table_name,
                        column_name,
                        data_type,
                        is_nullable,
                        column_default,
                        ordinal_position
                    FROM information_schema.columns
                    WHERE table_schema = :schema
                    AND table_name IN ('accounts', 'opportunities')
                    ORDER BY table_name, ordinal_position
                """), {'schema': schema})
                
                # Build fingerprint
                current_fingerprint = {}
                for row in result:
                    table = row.table_name
                    if table not in current_fingerprint:
                        current_fingerprint[table] = {}
                    
                    current_fingerprint[table][row.column_name] = {
                        'type': row.data_type,
                        'nullable': row.is_nullable,
                        'default': row.column_default,
                        'position': row.ordinal_position
                    }
                
                logger.info(f"Supabase schema fingerprint: {len(current_fingerprint)} tables")
                
                # Check for drift
                drift_tickets = []
                stored_key = "supabase"
                
                if stored_key in self.stored_fingerprints:
                    stored = self.stored_fingerprints[stored_key]
                    
                    # Detect changes
                    for table, columns in current_fingerprint.items():
                        if table not in stored:
                            drift_tickets.append({
                                'type': 'table_added',
                                'table': table,
                                'confidence': 1.0,
                                'timestamp': datetime.utcnow().isoformat()
                            })
                            continue
                        
                        stored_cols = stored[table]
                        
                        # Check for renamed or removed columns
                        for col_name in stored_cols:
                            if col_name not in columns:
                                # Column missing - might be renamed
                                drift_tickets.append({
                                    'type': 'column_removed_or_renamed',
                                    'table': table,
                                    'column': col_name,
                                    'confidence': 0.75,
                                    'timestamp': datetime.utcnow().isoformat()
                                })
                        
                        # Check for new columns
                        for col_name in columns:
                            if col_name not in stored_cols:
                                drift_tickets.append({
                                    'type': 'column_added',
                                    'table': table,
                                    'column': col_name,
                                    'confidence': 1.0,
                                    'timestamp': datetime.utcnow().isoformat()
                                })
                            elif columns[col_name]['type'] != stored_cols[col_name]['type']:
                                # Type changed
                                drift_tickets.append({
                                    'type': 'type_changed',
                                    'table': table,
                                    'column': col_name,
                                    'old_type': stored_cols[col_name]['type'],
                                    'new_type': columns[col_name]['type'],
                                    'confidence': 0.90,
                                    'timestamp': datetime.utcnow().isoformat()
                                })
                
                # Store current fingerprint
                self.stored_fingerprints[stored_key] = current_fingerprint
                
                return drift_tickets
                
        except Exception as e:
            logger.error(f"Failed to fingerprint Supabase schema: {e}")
            return []
    
    def fingerprint_mongodb(self) -> List[Dict[str, Any]]:
        """
        Fingerprint MongoDB schema by sampling documents
        
        Returns:
            List of drift tickets if drift detected
        """
        mongo_uri = os.getenv("MONGODB_URI", "")
        if not mongo_uri:
            logger.warning("MONGODB_URI not set, skipping MongoDB fingerprinting")
            return []
        
        mongo_db_name = os.getenv("MONGODB_DB", "autonomos")
        
        try:
            client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
            mongo_db = client[mongo_db_name]
            
            # Collections to fingerprint
            collections = ['accounts', 'opportunities']
            
            current_fingerprint = {}
            
            for collection_name in collections:
                collection = mongo_db[collection_name]
                
                # Sample up to 50 documents
                sample = list(collection.find().limit(50))
                
                if not sample:
                    logger.warning(f"No documents found in {collection_name}")
                    continue
                
                # Infer schema from sample
                field_types = {}
                for doc in sample:
                    for field, value in doc.items():
                        type_name = type(value).__name__
                        
                        if field not in field_types:
                            field_types[field] = {type_name: 1}
                        elif type_name not in field_types[field]:
                            field_types[field][type_name] = 1
                        else:
                            field_types[field][type_name] += 1
                
                # Determine dominant type for each field
                schema = {}
                for field, types in field_types.items():
                    dominant_type = max(types, key=types.get)
                    schema[field] = {
                        'type': dominant_type,
                        'type_distribution': types,
                        'sample_size': len(sample)
                    }
                
                current_fingerprint[collection_name] = schema
            
            logger.info(f"MongoDB schema fingerprint: {len(current_fingerprint)} collections")
            
            # Check for drift
            drift_tickets = []
            stored_key = "mongodb"
            
            if stored_key in self.stored_fingerprints:
                stored = self.stored_fingerprints[stored_key]
                
                # Detect changes
                for collection, fields in current_fingerprint.items():
                    if collection not in stored:
                        drift_tickets.append({
                            'type': 'collection_added',
                            'collection': collection,
                            'confidence': 1.0,
                            'timestamp': datetime.utcnow().isoformat()
                        })
                        continue
                    
                    stored_fields = stored[collection]
                    
                    # Check for renamed or removed fields
                    for field_name in stored_fields:
                        if field_name not in fields:
                            # Field missing - might be renamed
                            drift_tickets.append({
                                'type': 'field_removed_or_renamed',
                                'collection': collection,
                                'field': field_name,
                                'confidence': 0.75,
                                'timestamp': datetime.utcnow().isoformat()
                            })
                    
                    # Check for new fields
                    for field_name in fields:
                        if field_name not in stored_fields:
                            drift_tickets.append({
                                'type': 'field_added',
                                'collection': collection,
                                'field': field_name,
                                'confidence': 1.0,
                                'timestamp': datetime.utcnow().isoformat()
                            })
                        elif fields[field_name]['type'] != stored_fields[field_name]['type']:
                            # Type changed
                            drift_tickets.append({
                                'type': 'type_changed',
                                'collection': collection,
                                'field': field_name,
                                'old_type': stored_fields[field_name]['type'],
                                'new_type': fields[field_name]['type'],
                                'confidence': 0.85,
                                'timestamp': datetime.utcnow().isoformat()
                            })
            
            # Store current fingerprint
            self.stored_fingerprints[stored_key] = current_fingerprint
            
            client.close()
            
            return drift_tickets
            
        except Exception as e:
            logger.error(f"Failed to fingerprint MongoDB schema: {e}")
            return []


# Global instance
schema_observer = SchemaObserver()
