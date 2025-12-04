# AutonomOS Security Documentation

## Overview

AutonomOS is designed with security-first principles for enterprise data orchestration. This document outlines the security architecture, implemented controls, and compliance roadmap.

## Security Architecture

### Multi-Tenant Isolation

AutonomOS enforces data isolation between tenants through multiple layers when authentication is enabled:

| Layer | Mechanism | Implementation |
|-------|-----------|----------------|
| **Authentication** | JWT Bearer tokens | HS256-signed tokens with user_id claim |
| **Authorization** | Tenant-scoped queries | Database queries filtered by `tenant_id` |
| **Data Storage** | UUID-based tenancy | Each tenant has unique UUID (`tenant_id`) |
| **API Gateway** | Middleware validation | Requests validated before reaching handlers |

**Important:** When `DCL_AUTH_ENABLED=false` (development mode), tenant isolation is bypassed and a default tenant context is used. This mode is intended only for local development and testing.

### Authentication System

**JWT Token Structure:**
```json
{
  "user_id": "<uuid>",
  "exp": "<expiration_timestamp>"
}
```

Note: The core authentication system issues tokens with `user_id`. The gateway middleware (`app/gateway/middleware/auth.py`) extracts additional claims (`tenant_id`, `agent_id`, `scopes`) when present, setting them on `request.state` for downstream handlers.

**Password Security:**
- Primary algorithm: **Argon2** (OWASP recommended, memory-hard)
- Fallback: bcrypt (for legacy compatibility)
- Implementation: `passlib.CryptContext` with automatic algorithm selection

**Token Lifecycle:**
- Access tokens expire after 30 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
- Tokens validated on every protected request
- Invalid/expired tokens return HTTP 401

### Transport Security

**Redis Connections:**
- Protocol: TLS enabled when using `rediss://` URLs
- Certificate validation: Enabled with system CA bundle (`/etc/ssl/certs/ca-certificates.crt`)
- Production: Uses Upstash Redis with TLS by default
- Development: May use non-TLS connections (warnings logged)

**Configuration Requirement:** To ensure TLS is used, deploy with `REDIS_URL` using the `rediss://` scheme.

**API Transport:**
- HTTPS enforced in production
- HSTS headers recommended for browser clients

### API Security Controls

**Rate Limiting:**
- Implementation: SlowAPI (Python limits library)
- Scope: Per-endpoint, configurable limits
- Response: HTTP 429 with `Retry-After` header
- Test mode: Automatically disabled during automated testing

**Input Validation:**
- Framework: Pydantic models on all endpoints
- Type enforcement: Strict type checking
- Schema validation: Required fields, format constraints

**SQL Injection Prevention:**
- ORM: SQLAlchemy (no raw SQL queries)
- Parameterized queries: All user inputs escaped
- Identifier validation: SQL identifiers sanitized before use

### Data Protection

**Credential Handling:**
- API responses: Sensitive fields replaced with `***REDACTED***`
- Secrets: Environment variables only, never in codebase
- Connector configs: Passwords, tokens, API keys sanitized in responses

**Schema Integrity:**
- Fingerprinting: SHA-256 hash of schema structure
- Drift detection: Automatic comparison against baseline
- Change tracking: All schema modifications logged

### Audit & Compliance

**HITL Audit Records:**
- Database schema: PostgreSQL `hitl_repair_audit` table is defined
- Planned tracking: Decision, reviewer, timestamp, metadata
- Current status: Schema and CRUD utilities ready; workflow integration in progress
- Note: General API request logging handled separately (see Request Logging below)

**Request Logging:**
- Audit middleware: Available but currently disabled pending performance optimization
- When enabled: Captures request/response metadata (body hashes, not content)
- Current state: General request audit and HITL logging both pending integration

## Implemented Security Controls (Phase 0)

| Control | Status | Details |
|---------|--------|---------|
| JWT Authentication | ✅ Implemented | HS256 with user_id claim |
| Argon2 Password Hashing | ✅ Implemented | OWASP-recommended algorithm |
| TLS for Redis | ⚙️ Configurable | Requires rediss:// URL configuration |
| Multi-Tenant Isolation | ✅ Implemented | Requires auth enabled (`DCL_AUTH_ENABLED=true`) |
| API Rate Limiting | ✅ Implemented | SlowAPI with configurable limits |
| Input Validation | ✅ Implemented | Pydantic on all endpoints |
| Credential Sanitization | ✅ Implemented | REDACTED in API responses |
| HITL Audit Logging | 🔄 In Progress | Schema ready; integration pending |
| Request Audit Middleware | ⏸️ Disabled | Available but paused for optimization |
| SQL Injection Prevention | ✅ Implemented | SQLAlchemy ORM |
| Schema Fingerprinting | ✅ Implemented | SHA-256 drift detection |

## Security Roadmap

### Phase 1: Enterprise Readiness (Target: 0-6 Months)
- [ ] SOC 2 Type I Certification
- [ ] 3rd-Party Penetration Testing
- [ ] Single Sign-On (SSO) - Okta, Azure AD
- [ ] Private Connectivity (AWS PrivateLink)
- [ ] Public Trust Portal & Incident Response Plan

### Phase 2: Continuous Compliance (Target: 6-18 Months)
- [ ] SOC 2 Type II + ISO 27001
- [ ] Bring Your Own Key (BYOK)
- [ ] Customer-Managed RBAC
- [ ] Regional Data Residency Controls
- [ ] AI-Driven Threat Detection

## Security Configuration

### Environment Variables

| Variable | Purpose | Required | Notes |
|----------|---------|----------|-------|
| `SECRET_KEY` | JWT signing key | Yes | Must be cryptographically strong |
| `JWT_SECRET_KEY` | Gateway JWT key | No | Falls back to SECRET_KEY |
| `ENCRYPTION_KEY` | Credential encryption | **Recommended** | Has insecure default - **MUST override in production** |
| `DCL_AUTH_ENABLED` | Enable/disable auth | No | Default: true |
| `REDIS_URL` | Redis connection | Yes | Use `rediss://` for TLS |

**Security Warning:** `ENCRYPTION_KEY` has a fallback default value for development convenience. **Production deployments MUST set a unique, cryptographically strong value** or credentials stored by the DCL engine will use a static key.

### Development Mode

When `DCL_AUTH_ENABLED=false`:
- Authentication bypassed for local development
- MockUser object provides default tenant context
- **WARNING:** Never use in production

## Vulnerability Reporting

If you discover a security vulnerability, please report it responsibly:

1. **Do not** create public GitHub issues for security vulnerabilities
2. Email security concerns to the development team
3. Include detailed reproduction steps
4. Allow reasonable time for remediation before disclosure

## Security Contacts

For security-related inquiries:
- Review this documentation first
- Check the FAQ in the Help section
- Contact the platform team for specific concerns

---

*Last Updated: November 2024*
*Document Version: 1.0*
