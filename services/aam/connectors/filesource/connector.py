import os
import csv
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models import CanonicalStream


class FileSourceConnector:
    def __init__(self, db: Session, tenant_id: str = "default-tenant"):
        self.db = db
        self.tenant_id = tenant_id
        self.sources_dir = Path(__file__).parent / "mock_sources"
    
    def read_csv(self, filename: str) -> List[Dict[str, Any]]:
        """Read CSV file and return list of dictionaries"""
        filepath = self.sources_dir / filename
        
        if not filepath.exists():
            raise FileNotFoundError(f"CSV file not found: {filepath}")
        
        data = []
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(dict(row))
        
        return data
    
    def emit_to_canonical_stream(self, entity: str, data: Dict[str, Any], trace_id: str = None):
        """Emit a record to the canonical_streams table"""
        if trace_id is None:
            trace_id = str(uuid.uuid4())
        
        canonical_entry = CanonicalStream(
            tenant_id=self.tenant_id,
            entity=entity,
            data=data,
            meta={
                "version": "1.0.0",
                "tenant": self.tenant_id,
                "trace_id": trace_id,
                "emitted_at": datetime.utcnow().isoformat()
            },
            source={
                "system": "filesource",
                "connection_id": "filesource-default",
                "schema_version": "1.0.0"
            },
            emitted_at=datetime.utcnow()
        )
        
        self.db.add(canonical_entry)
    
    def replay_accounts(self):
        """Load accounts from CSV and emit to canonical streams"""
        accounts = self.read_csv("accounts.csv")
        trace_id = str(uuid.uuid4())
        
        for account in accounts:
            self.emit_to_canonical_stream("account", account, trace_id)
        
        self.db.commit()
        return len(accounts)
    
    def replay_opportunities(self):
        """Load opportunities from CSV and emit to canonical streams"""
        opportunities = self.read_csv("opportunities.csv")
        trace_id = str(uuid.uuid4())
        
        for opp in opportunities:
            self.emit_to_canonical_stream("opportunity", opp, trace_id)
        
        self.db.commit()
        return len(opportunities)
    
    def replay_all(self):
        """Replay all available CSV files"""
        results = {}
        
        results['accounts'] = self.replay_accounts()
        results['opportunities'] = self.replay_opportunities()
        
        return results
