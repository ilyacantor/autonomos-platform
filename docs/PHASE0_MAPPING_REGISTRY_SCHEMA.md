# Phase 0: Enterprise Mapping Registry Database Schema

## Overview
This document defines the enterprise-grade database schema for the AAM-DCL mapping registry, replacing the file-based YAML approach with a properly normalized, auditable, and RAG-enabled database architecture.

## Design Principles
1. **Proper Normalization**: Separate concerns into distinct tables with clear relationships
2. **Audit Trail**: Complete history of all changes for compliance (GDPR, SOC2)
3. **RAG-First**: Native support for vector embeddings and semantic search
4. **Versioning**: Track mapping evolution over time
5. **Performance**: Optimized indexes for sub-100ms lookups
6. **Multi-Tenant**: Complete tenant isolation with proper foreign keys

## Schema Architecture

### Core Tables

#### 1. `connector_definitions`
Defines registered data sources (Salesforce, HubSpot, etc.)

```sql
CREATE TABLE connector_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    connector_name VARCHAR(255) NOT NULL,  -- 'salesforce', 'hubspot', etc.
    connector_type VARCHAR(50) NOT NULL,   -- 'rest_api', 'database', 'file'
    description TEXT,
    metadata JSONB DEFAULT '{}',           -- API version, auth type, etc.
    status VARCHAR(50) DEFAULT 'active',   -- 'active', 'deprecated', 'archived'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_tenant_connector UNIQUE(tenant_id, connector_name)
);

CREATE INDEX idx_connector_tenant_status ON connector_definitions(tenant_id, status);
```

#### 2. `entity_schemas`
Defines canonical entities (account, opportunity, contact, etc.)

```sql
CREATE TABLE entity_schemas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_name VARCHAR(255) NOT NULL,     -- 'account', 'opportunity', 'contact'
    entity_version VARCHAR(50) DEFAULT '1.0.0',
    schema_definition JSONB NOT NULL,      -- Full Pydantic schema
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_entity_version UNIQUE(entity_name, entity_version)
);

CREATE INDEX idx_entity_name ON entity_schemas(entity_name);
```

#### 3. `field_mappings`
Core mapping table - maps source fields to canonical fields

```sql
CREATE TABLE field_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    connection_id UUID,                    -- Specific connection instance
    connector_id UUID NOT NULL REFERENCES connector_definitions(id),
    entity_schema_id UUID NOT NULL REFERENCES entity_schemas(id),
    
    -- Source field information
    source_table VARCHAR(255) NOT NULL,    -- e.g., 'Accounts', 'Opportunities'
    source_field VARCHAR(255) NOT NULL,    -- e.g., 'Id', 'AccountName'
    source_data_type VARCHAR(100),         -- e.g., 'varchar', 'integer', 'timestamp'
    
    -- Target canonical field
    canonical_entity VARCHAR(255) NOT NULL, -- e.g., 'account', 'opportunity'
    canonical_field VARCHAR(255) NOT NULL,  -- e.g., 'account_id', 'name'
    canonical_data_type VARCHAR(100),       -- Expected type in canonical schema
    
    -- Transformation logic
    mapping_type VARCHAR(50) DEFAULT 'direct',  -- 'direct', 'computed', 'aggregated', 'transformed'
    transformation_rule JSONB,              -- Complex transformations
    coercion_function VARCHAR(255),         -- e.g., 'uppercase', 'trim', 'to_decimal'
    
    -- Quality metrics
    confidence_score FLOAT DEFAULT 1.0,     -- 0.0 to 1.0 (AI-generated vs manual)
    validation_status VARCHAR(50) DEFAULT 'pending',  -- 'pending', 'validated', 'failed'
    success_rate FLOAT,                     -- Historical success rate
    avg_processing_time_ms INTEGER,        -- Performance tracking
    error_count INTEGER DEFAULT 0,
    last_validated_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    mapping_source VARCHAR(50) DEFAULT 'manual',  -- 'manual', 'rag', 'llm', 'auto_detected'
    version INTEGER DEFAULT 1,
    status VARCHAR(50) DEFAULT 'active',    -- 'active', 'deprecated', 'pending_review'
    notes TEXT,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by UUID REFERENCES users(id),
    
    CONSTRAINT unique_tenant_mapping UNIQUE(
        tenant_id, connector_id, source_table, source_field, canonical_entity, canonical_field
    )
);

-- Performance indexes
CREATE INDEX idx_mapping_tenant_connector ON field_mappings(tenant_id, connector_id);
CREATE INDEX idx_mapping_entity ON field_mappings(canonical_entity);
CREATE INDEX idx_mapping_status ON field_mappings(status);
CREATE INDEX idx_mapping_confidence ON field_mappings(confidence_score);
CREATE INDEX idx_mapping_source ON field_mappings(mapping_source);
```

#### 4. `mapping_embeddings`
RAG support - vector embeddings for semantic search

```sql
CREATE TABLE mapping_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    field_mapping_id UUID NOT NULL REFERENCES field_mappings(id) ON DELETE CASCADE,
    
    -- Embedding data
    embedding_text TEXT NOT NULL,           -- Combined text for similarity: "source_field canonical_field transformation_rule"
    embedding_vector vector(1536),          -- OpenAI ada-002 or similar
    embedding_model VARCHAR(100) DEFAULT 'text-embedding-ada-002',
    
    -- Metadata for similarity matching
    metadata JSONB DEFAULT '{}',            -- Field types, common patterns, etc.
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_embedding_mapping UNIQUE(field_mapping_id)
);

-- Vector similarity search index (requires pgvector extension)
CREATE INDEX idx_embedding_vector ON mapping_embeddings USING ivfflat (embedding_vector vector_cosine_ops);
CREATE INDEX idx_embedding_mapping ON mapping_embeddings(field_mapping_id);
```

#### 5. `mapping_audit_log`
Complete audit trail for compliance

```sql
CREATE TABLE mapping_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    field_mapping_id UUID NOT NULL REFERENCES field_mappings(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    
    -- Change tracking
    action VARCHAR(50) NOT NULL,            -- 'created', 'updated', 'deleted', 'validated', 'deprecated'
    field_changed VARCHAR(255),             -- Which field was modified
    old_value JSONB,                        -- Previous value
    new_value JSONB,                        -- New value
    
    -- Context
    changed_by UUID REFERENCES users(id),
    change_reason TEXT,                     -- Why the change was made
    confidence_delta FLOAT,                 -- Change in confidence score
    
    -- Audit metadata
    ip_address VARCHAR(45),
    user_agent TEXT,
    trace_id VARCHAR(255),                  -- For debugging
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_audit_mapping ON mapping_audit_log(field_mapping_id),
    INDEX idx_audit_tenant_created ON mapping_audit_log(tenant_id, created_at DESC)
);
```

#### 6. `mapping_validation_results`
Track validation outcomes for quality assurance

```sql
CREATE TABLE mapping_validation_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    field_mapping_id UUID NOT NULL REFERENCES field_mappings(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    
    -- Validation details
    validation_type VARCHAR(50) NOT NULL,   -- 'type_check', 'range_check', 'format_check', 'live_test'
    validation_status VARCHAR(50) NOT NULL, -- 'passed', 'failed', 'warning'
    error_message TEXT,
    sample_input JSONB,                     -- Sample source data
    sample_output JSONB,                    -- Transformed result
    
    -- Metrics
    test_count INTEGER DEFAULT 1,
    pass_count INTEGER DEFAULT 0,
    fail_count INTEGER DEFAULT 0,
    
    validated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    validated_by UUID REFERENCES users(id),
    
    INDEX idx_validation_mapping ON mapping_validation_results(field_mapping_id),
    INDEX idx_validation_status ON mapping_validation_results(validation_status, validated_at DESC)
);
```

## Materialized Views for Performance

### `mv_mapping_lineage_grid`
Optimized view for the Tabular Lineage Grid reporting view

```sql
CREATE MATERIALIZED VIEW mv_mapping_lineage_grid AS
SELECT 
    fm.id,
    fm.tenant_id,
    cd.connector_name AS source_system,
    fm.source_table,
    fm.source_field,
    fm.canonical_entity AS target_entity,
    fm.canonical_field AS target_field,
    fm.mapping_type,
    fm.confidence_score,
    fm.transformation_rule,
    fm.validation_status,
    fm.success_rate,
    fm.avg_processing_time_ms,
    fm.error_count,
    fm.mapping_source,
    fm.status,
    fm.created_at,
    fm.updated_at,
    u_created.email AS created_by_email,
    u_updated.email AS updated_by_email
FROM field_mappings fm
JOIN connector_definitions cd ON fm.connector_id = cd.id
LEFT JOIN users u_created ON fm.created_by = u_created.id
LEFT JOIN users u_updated ON fm.updated_by = u_updated.id
WHERE fm.status = 'active';

CREATE INDEX idx_mv_lineage_tenant ON mv_mapping_lineage_grid(tenant_id);
CREATE INDEX idx_mv_lineage_source ON mv_mapping_lineage_grid(source_system);
CREATE INDEX idx_mv_lineage_entity ON mv_mapping_lineage_grid(target_entity);
CREATE INDEX idx_mv_lineage_confidence ON mv_mapping_lineage_grid(confidence_score);
```

## Migration Strategy

### Phase 0 Dual-Write Mode
To ensure zero data loss during migration from YAML to database:

1. **Dual-Write Period**:
   - All mapping updates written to both YAML and database
   - Read from database, fallback to YAML if not found
   - Validate consistency between both sources

2. **Validation Steps**:
   ```python
   def validate_migration():
       yaml_mappings = load_all_yaml_mappings()
       db_mappings = query_all_db_mappings()
       
       for yaml_map in yaml_mappings:
           db_map = find_equivalent_db_mapping(yaml_map)
           assert db_map is not None, f"Missing mapping: {yaml_map}"
           assert maps_are_equivalent(yaml_map, db_map), f"Mismatch: {yaml_map}"
   ```

3. **Rollback Capability**:
   - Keep YAML files as backup during Phase 0
   - Database migrations reversible via Alembic
   - Flag to switch back to YAML if issues detected

## Performance Requirements

- **Mapping Lookup**: <100ms for 10,000 mappings (database query)
- **RAG Search**: <500ms for top-10 similar mappings (vector search)
- **Audit Query**: <1s for last 1000 changes per tenant
- **Materialized View Refresh**: <5s for full refresh

## Security & Compliance

1. **Multi-Tenant Isolation**: All queries filtered by `tenant_id`
2. **Audit Trail**: Complete history for GDPR/SOC2 compliance
3. **Access Control**: User-based permissions via `created_by`/`updated_by`
4. **Data Retention**: Configurable retention policies for audit logs

## Next Steps (Phase 0 Implementation)

1. ✅ Design schema (this document)
2. [ ] Create Alembic migration scripts
3. [ ] Implement data access layer (repository pattern)
4. [ ] Build migration script (YAML → Database)
5. [ ] Implement dual-write mode
6. [ ] Add RAG embedding generation
7. [ ] Create materialized views
8. [ ] Add validation framework
9. [ ] Test with existing 191 field mappings
10. [ ] Validate zero data loss and performance targets
