# AutonomOS Documentation Index

**Last Updated:** December 2, 2025  
**Status:** Phase 4 Complete - Live Flow Monitoring Operational

This index provides a comprehensive guide to all AutonomOS platform documentation, organized by category for easy navigation.

---

## 🚀 Quick Start

| Document | Description | Path |
|----------|-------------|------|
| **Main README** | Platform overview, quick start, features | [`README.md`](./README.md) |
| **Project State** | Current status, user preferences, architecture summary | [`replit.md`](./replit.md) |
| **Security Overview** | Security architecture, controls, compliance roadmap | [`SECURITY.md`](./SECURITY.md) |
| **DCL Removal Assessment** | Impact analysis for DCL decommission (no action taken) | [`DCL_REMOVAL_ASSESSMENT.md`](./DCL_REMOVAL_ASSESSMENT.md) |
| **Archive Log** | History of archived documentation | [`ARCHIVE_LOG.md`](./ARCHIVE_LOG.md) |

---

## 📐 Architecture Documentation

### Core Architecture
| Document | Description | Path |
|----------|-------------|------|
| **Architecture Overview** | High-level system architecture, components, data flow | [`docs/architecture/ARCHITECTURE_OVERVIEW.md`](./docs/architecture/ARCHITECTURE_OVERVIEW.md) |
| **AAM + DCL Architecture** | Comprehensive architecture for Adaptive API Mesh and DCL | [`docs/AAM_DCL_ARCHITECTURE_OVERVIEW.md`](./docs/AAM_DCL_ARCHITECTURE_OVERVIEW.md) |

### Component Documentation
| Component | Description | Path |
|-----------|-------------|------|
| **AAM Hybrid** | Adaptive API Mesh implementation and configuration | [`aam_hybrid/README.md`](./aam_hybrid/README.md) |
| **AAM Full Context** | Complete AAM system documentation | [`aam_hybrid/AAM_FULL_CONTEXT.md`](./aam_hybrid/AAM_FULL_CONTEXT.md) |
| **DCL Engine** | Data Connection Layer engine documentation | [`app/dcl_engine/README.md`](./app/dcl_engine/README.md) |
| **Frontend** | React/TypeScript frontend documentation | [`frontend/README.md`](./frontend/README.md) |
| **NLP Gateway** | Natural language processing service | [`services/nlp-gateway/README.md`](./services/nlp-gateway/README.md) |

---

## 📖 Developer Guides

| Document | Description | Path |
|----------|-------------|------|
| **Developer Guide** | Setup, development workflow, testing | [`docs/development/DEVELOPER_GUIDE.md`](./docs/development/DEVELOPER_GUIDE.md) |
| **API Reference** | Complete API endpoint documentation | [`docs/api/API_REFERENCE.md`](./docs/api/API_REFERENCE.md) |
| **NLP Quick Reference** | NLP Gateway API quick reference | [`services/nlp-gateway/QUICK_REFERENCE.md`](./services/nlp-gateway/QUICK_REFERENCE.md) |
| **NLP How-To** | Step-by-step NLP integration guide | [`services/nlp-gateway/HOW_TO_USE.md`](./services/nlp-gateway/HOW_TO_USE.md) |

---

## 📊 Examples & Usage Guides

| Document | Description | Path |
|----------|-------------|------|
| **AAM Auto-Discovery** | Examples of AAM automatic connector discovery | [`docs/examples/AAM_AUTO_DISCOVERY_EXAMPLES.md`](./docs/examples/AAM_AUTO_DISCOVERY_EXAMPLES.md) |
| **AAM Canonical Transformations** | Canonical event transformation examples | [`docs/examples/AAM_CANONICAL_TRANSFORMATION_EXAMPLES.md`](./docs/examples/AAM_CANONICAL_TRANSFORMATION_EXAMPLES.md) |
| **AAM Dashboard Guide** | AAM monitoring dashboard usage | [`docs/examples/AAM_DASHBOARD_GUIDE.md`](./docs/examples/AAM_DASHBOARD_GUIDE.md) |
| **DCL Ontology Examples** | DCL ontology engine usage examples | [`docs/examples/DCL_ONTOLOGY_ENGINE_EXAMPLES.md`](./docs/examples/DCL_ONTOLOGY_ENGINE_EXAMPLES.md) |
| **DCL Usage Guide** | Step-by-step DCL usage guide | [`docs/examples/DCL_USAGE_GUIDE.md`](./docs/examples/DCL_USAGE_GUIDE.md) |
| **Color Palette** | UI color scheme, navigation, and design guidelines | [`color_palette.md`](./color_palette.md) |

---

## 🔧 Operations & Deployment

### Operations
| Document | Description | Path |
|----------|-------------|------|
| **Observability Runbook** | Monitoring, alerting, troubleshooting | [`docs/operations/OBSERVABILITY_RUNBOOK.md`](./docs/operations/OBSERVABILITY_RUNBOOK.md) |
| **Operational Procedures** | Day-to-day operational tasks | [`docs/operations/OPERATIONAL_PROCEDURES.md`](./docs/operations/OPERATIONAL_PROCEDURES.md) |

### Deployment
| Document | Description | Path |
|----------|-------------|------|
| **Deployment Guide** | Production deployment procedures | [`docs/deployment/DEPLOYMENT_GUIDE.md`](./docs/deployment/DEPLOYMENT_GUIDE.md) |

### Performance & Security
| Document | Description | Path |
|----------|-------------|------|
| **Performance Tuning** | Performance optimization guide | [`docs/performance/PERFORMANCE_TUNING.md`](./docs/performance/PERFORMANCE_TUNING.md) |
| **Security Hardening** | Security best practices and hardening | [`docs/security/SECURITY_HARDENING.md`](./docs/security/SECURITY_HARDENING.md) |

---

## 🧪 Testing & Benchmarking

| Document | Description | Path |
|----------|-------------|------|
| **Multi-Tenant Stress Tests** | Multi-tenant isolation stress testing suite | [`tests/MULTI_TENANT_STRESS_TEST_SUITE.md`](./tests/MULTI_TENANT_STRESS_TEST_SUITE.md) |
| **Benchmarking Suite** | Performance benchmarking documentation | [`benchmarks/BENCHMARKING_SUITE_README.md`](./benchmarks/BENCHMARKING_SUITE_README.md) |

---

## 🛠️ Scripts & Utilities

| Document | Description | Path |
|----------|-------------|------|
| **Functional Probe** | System health check utilities | [`scripts/FUNCTIONAL_PROBE_README.md`](./scripts/FUNCTIONAL_PROBE_README.md) |
| **Quickstart Script** | Quick setup and initialization | [`scripts/QUICKSTART.md`](./scripts/QUICKSTART.md) |

---

## 📦 Archived Documentation

Historical documentation has been moved to `docs/archive/` for reference:

### Categories in Archive
- **Planning & Remediation** - Old planning documents (REMEDIATION_PLAN.md, PLAN.md, RACI plans)
- **Implementation Summaries** - Completed task summaries and fix reports
- **Migration Guides** - Phase 1 & 2 migration documentation
- **Old Configurations** - Deprecated configuration docs
- **Investigations** - Historical troubleshooting and analysis

> **Note:** For complete list of archived files, see [`ARCHIVE_LOG.md`](./ARCHIVE_LOG.md)

---

## 🎯 Key Features by Documentation

### Real-Time Monitoring
- **Live Flow Monitor**: [`README.md`](./README.md#key-capabilities) - Real-time dashboard at `/flow-monitor`
- **AAM Dashboard**: [`docs/examples/AAM_DASHBOARD_GUIDE.md`](./docs/examples/AAM_DASHBOARD_GUIDE.md)
- **Observability**: [`docs/operations/OBSERVABILITY_RUNBOOK.md`](./docs/operations/OBSERVABILITY_RUNBOOK.md)

### Data Integration
- **AAM Connectors**: [`aam_hybrid/README.md`](./aam_hybrid/README.md)
- **DCL Engine**: [`app/dcl_engine/README.md`](./app/dcl_engine/README.md)
- **Canonical Events**: [`docs/examples/AAM_CANONICAL_TRANSFORMATION_EXAMPLES.md`](./docs/examples/AAM_CANONICAL_TRANSFORMATION_EXAMPLES.md)

### AI & Intelligence
- **NLP Gateway**: [`services/nlp-gateway/README.md`](./services/nlp-gateway/README.md)
- **RAG Intelligence**: [`docs/AAM_DCL_ARCHITECTURE_OVERVIEW.md`](./docs/AAM_DCL_ARCHITECTURE_OVERVIEW.md)
- **Entity Mapping**: [`docs/examples/DCL_ONTOLOGY_EXAMPLES.md`](./docs/examples/DCL_ONTOLOGY_ENGINE_EXAMPLES.md)

### Multi-Tenant Architecture
- **Isolation & Security**: [`docs/architecture/ARCHITECTURE_OVERVIEW.md`](./docs/architecture/ARCHITECTURE_OVERVIEW.md)
- **Stress Testing**: [`tests/MULTI_TENANT_STRESS_TEST_SUITE.md`](./tests/MULTI_TENANT_STRESS_TEST_SUITE.md)

---

## 🔄 Documentation Maintenance

### Update Schedule
- **README.md** - Update after major features
- **replit.md** - Update continuously with project changes
- **Architecture docs** - Update after architectural changes
- **API Reference** - Auto-generated, update with API changes

### Contributing to Documentation
1. Keep examples runtime-verified
2. Include diagrams where helpful
3. Update this index when adding new docs
4. Archive obsolete docs rather than deleting

---

## 📞 Need Help?

- **Setup Issues**: See [`docs/development/DEVELOPER_GUIDE.md`](./docs/development/DEVELOPER_GUIDE.md)
- **Deployment**: See [`docs/deployment/DEPLOYMENT_GUIDE.md`](./docs/deployment/DEPLOYMENT_GUIDE.md)
- **Troubleshooting**: See [`docs/operations/OBSERVABILITY_RUNBOOK.md`](./docs/operations/OBSERVABILITY_RUNBOOK.md)
- **API Questions**: See [`docs/api/API_REFERENCE.md`](./docs/api/API_REFERENCE.md)

---

**Platform Status:** ✅ Phase 4 Complete - Production Ready  
**Total Active Documentation:** 30+ files organized across 6 categories  
**Last Major Update:** Security Documentation & Glossary (December 2, 2025)
