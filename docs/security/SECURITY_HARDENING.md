# AutonomOS Platform - Security Hardening Guide

**Version:** 1.0  
**Last Updated:** November 19, 2025  
**Classification:** Internal - Security Sensitive

---

## Table of Contents

1. [Authentication Best Practices](#authentication-best-practices)
2. [API Key Rotation](#api-key-rotation)
3. [Secret Management](#secret-management)
4. [Network Security](#network-security)
5. [Database Security](#database-security)
6. [Redis Security](#redis-security)
7. [Rate Limiting](#rate-limiting)
8. [Input Validation](#input-validation)
9. [Audit Logging](#audit-logging)
10. [Compliance](#compliance)

---

## Authentication Best Practices

### JWT Token Security

**Configuration:**

```python
# app/security.py

# 1. Use strong secret key (32+ bytes)
SECRET_KEY = os.getenv("JWT_SECRET_KEY")  # Generated with: openssl rand -hex 32

# 2. Use HS256 algorithm (symmetric, secure for server-to-server)
ALGORITHM = "HS256"

# 3. Set appropriate expiration (30 minutes recommended)
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 4. Include necessary claims only
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    
    to_encode.update({
        "exp": expire,       # Expiration time
        "iat": datetime.utcnow(),  # Issued at
        "nbf": datetime.utcnow()   # Not before
    })
    
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

**Security Checklist:**

- ✅ Use strong secret key (32+ random bytes)
- ✅ Set short token expiration (30 minutes)
- ✅ Validate token on every request
- ✅ Store tokens in httpOnly cookies (for web apps)
- ✅ Never log tokens or secrets
- ✅ Rotate JWT secret key quarterly
- ❌ Never send tokens in URL parameters
- ❌ Never store tokens in localStorage (XSS risk)

---

### Password Security

**Hashing with Argon2:**

```python
from passlib.context import CryptContext

# Use Argon2 (winner of Password Hashing Competition)
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__memory_cost=65536,    # 64 MB
    argon2__time_cost=3,          # 3 iterations
    argon2__parallelism=4         # 4 threads
)

# Hash password
hashed = pwd_context.hash("user_password")

# Verify password
is_valid = pwd_context.verify("user_password", hashed)
```

**Password Policy:**

```python
import re

def validate_password(password: str) -> bool:
    """
    Enforce strong password policy:
    - Minimum 12 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 number
    - At least 1 special character
    """
    if len(password) < 12:
        return False
    
    if not re.search(r"[A-Z]", password):
        return False
    
    if not re.search(r"[a-z]", password):
        return False
    
    if not re.search(r"\d", password):
        return False
    
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False
    
    return True
```

**Security Checklist:**

- ✅ Use Argon2 for password hashing
- ✅ Enforce strong password policy (12+ chars, mixed case, numbers, symbols)
- ✅ Implement account lockout after 5 failed attempts
- ✅ Require password change on first login
- ✅ Never store plaintext passwords
- ✅ Never send passwords via email
- ❌ Never use MD5, SHA-1, or unsalted hashes

---

## API Key Rotation

### Rotation Strategy

**Frequency:**
- **Production:** Every 90 days
- **Staging:** Every 180 days
- **Development:** Annually

**Process:**

```bash
# 1. Generate new key
NEW_JWT_SECRET=$(openssl rand -hex 32)

# 2. Deploy new key alongside old key (dual-key mode)
# Update .env:
JWT_SECRET_KEY=$NEW_JWT_SECRET
JWT_SECRET_KEY_OLD=$OLD_JWT_SECRET

# 3. Update token verification to accept both keys
```

**Dual-Key Verification:**

```python
def decode_access_token(token: str) -> dict:
    """Verify token with current or old secret (during rotation)."""
    try:
        # Try current secret
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        # Try old secret (if in rotation window)
        if settings.JWT_SECRET_KEY_OLD:
            try:
                return jwt.decode(token, settings.JWT_SECRET_KEY_OLD, algorithms=[ALGORITHM])
            except JWTError:
                raise HTTPException(status_code=401, detail="Invalid token")
        raise HTTPException(status_code=401, detail="Invalid token")
```

**Rotation Timeline:**

```
Day 0:  Deploy new key alongside old key
Day 1:  Monitor for errors (both keys active)
Day 7:  Remove old key (only new key active)
```

---

### External API Key Rotation

**Salesforce, Google, etc.:**

1. **Generate new key in provider console**
2. **Update environment variable**
3. **Restart application**
4. **Revoke old key in provider console**

**Automation Script:**

```bash
#!/bin/bash
# scripts/rotate_api_keys.sh

# Rotate Salesforce credentials
echo "Rotating Salesforce API key..."
NEW_SALESFORCE_KEY=$(vault read -field=client_secret secret/salesforce/new)
sed -i "s/SALESFORCE_CLIENT_SECRET=.*/SALESFORCE_CLIENT_SECRET=$NEW_SALESFORCE_KEY/" .env

# Restart application
sudo systemctl restart autonomos

# Verify new key works
curl -X GET http://localhost:5000/api/v1/aam/monitoring/connectors \
  -H "Authorization: Bearer $TOKEN"

if [ $? -eq 0 ]; then
  echo "✅ New key verified, revoking old key in Salesforce console"
else
  echo "❌ New key failed, rolling back"
  exit 1
fi
```

---

## Secret Management

### Environment Variable Storage

**DO:**
- ✅ Use `.env` files for local development
- ✅ Use secret management services (Replit Secrets, AWS Secrets Manager, HashiCorp Vault)
- ✅ Encrypt `.env` files at rest (if stored)
- ✅ Restrict `.env` file permissions (chmod 600)

**DON'T:**
- ❌ Commit `.env` files to Git (use `.gitignore`)
- ❌ Log secret values
- ❌ Send secrets via email or Slack
- ❌ Hardcode secrets in code

**Example `.gitignore`:**

```
.env
.env.local
.env.production
*.pem
*.key
certs/
```

---

### Using HashiCorp Vault (Recommended)

**Setup:**

```bash
# Start Vault server
vault server -dev

# Set Vault address
export VAULT_ADDR='http://127.0.0.1:8200'

# Store secrets
vault kv put secret/autonomos \
  jwt_secret_key="abc123..." \
  database_url="postgresql://..." \
  redis_url="rediss://..."
```

**Integration:**

```python
import hvac

client = hvac.Client(url='http://127.0.0.1:8200')
client.token = os.getenv('VAULT_TOKEN')

# Read secrets
secrets = client.secrets.kv.v2.read_secret_version(path='autonomos')

settings.JWT_SECRET_KEY = secrets['data']['data']['jwt_secret_key']
settings.DATABASE_URL = secrets['data']['data']['database_url']
```

---

## Network Security

### TLS/SSL Configuration

**Nginx:**

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # Strong SSL protocols
    ssl_protocols TLSv1.2 TLSv1.3;
    
    # Strong ciphers
    ssl_ciphers 'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers on;

    # HSTS (force HTTPS)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # CSP (Content Security Policy)
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;
}
```

**Test SSL Configuration:**

```bash
# Test with SSL Labs
https://www.ssllabs.com/ssltest/analyze.html?d=your-domain.com

# Expected grade: A+
```

---

### Firewall Configuration

**UFW (Ubuntu):**

```bash
# Enable UFW
sudo ufw enable

# Allow SSH (port 22)
sudo ufw allow 22/tcp

# Allow HTTP (port 80)
sudo ufw allow 80/tcp

# Allow HTTPS (port 443)
sudo ufw allow 443/tcp

# Deny all other inbound
sudo ufw default deny incoming

# Allow all outbound
sudo ufw default allow outgoing

# Verify rules
sudo ufw status verbose
```

**AWS Security Groups:**

| Type | Protocol | Port | Source | Description |
|------|----------|------|--------|-------------|
| SSH | TCP | 22 | Your IP only | Admin access |
| HTTP | TCP | 80 | 0.0.0.0/0 | Public web |
| HTTPS | TCP | 443 | 0.0.0.0/0 | Public web (SSL) |
| PostgreSQL | TCP | 5432 | VPC only | Database (internal) |
| Redis | TCP | 6379 | VPC only | Cache (internal) |

---

## Database Security

### Connection Encryption

**PostgreSQL SSL:**

```python
# Require SSL for database connections
DATABASE_URL = "postgresql://user:pass@host:5432/db?sslmode=require"

# Verify certificate (production)
DATABASE_URL = "postgresql://user:pass@host:5432/db?sslmode=verify-full&sslrootcert=/path/to/ca.pem"
```

**Supabase:**

```bash
# Supabase enforces SSL by default
SUPABASE_DB_URL=postgresql://postgres.xxxxxxxxxxxx:password@aws-0-us-west-1.pooler.supabase.com:6543/postgres
# Note: Uses port 6543 (connection pooling with SSL)
```

---

### User Permissions

**Principle of Least Privilege:**

```sql
-- Create application user (not superuser)
CREATE USER autonomos_app WITH PASSWORD 'secure_password';

-- Grant only necessary permissions
GRANT CONNECT ON DATABASE autonomos TO autonomos_app;
GRANT USAGE ON SCHEMA public TO autonomos_app;

-- Grant table permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO autonomos_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO autonomos_app;

-- Revoke superuser permissions
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
```

**Read-Only User (for analytics):**

```sql
CREATE USER autonomos_readonly WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE autonomos TO autonomos_readonly;
GRANT USAGE ON SCHEMA public TO autonomos_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO autonomos_readonly;
```

---

### Row-Level Security (RLS)

**Enable RLS for multi-tenant isolation:**

```sql
-- Enable RLS on tenant-scoped tables
ALTER TABLE canonical_streams ENABLE ROW LEVEL SECURITY;

-- Create policy: Users can only see their own tenant's data
CREATE POLICY tenant_isolation ON canonical_streams
  USING (tenant_id = current_setting('app.tenant_id')::uuid);

-- Set tenant_id in application session
-- In Python:
db.execute("SET app.tenant_id = :tenant_id", {"tenant_id": str(user.tenant_id)})
```

---

## Redis Security

### Authentication

**Enable password authentication:**

```bash
# In redis.conf
requirepass your_very_strong_password_here

# Restart Redis
sudo systemctl restart redis
```

**Connection string:**

```bash
REDIS_URL=redis://:your_very_strong_password_here@localhost:6379
```

---

### TLS/SSL for Redis

**Upstash (managed Redis with TLS):**

```bash
# Upstash provides TLS by default
REDIS_URL=rediss://default:password@us1-modern-wombat-12345.upstash.io:6379

# Download CA certificate
curl -o certs/redis_ca.pem https://console.upstash.com/static/trust/redis_ca.pem
```

**Self-hosted Redis with TLS:**

```bash
# In redis.conf
port 0
tls-port 6379
tls-cert-file /path/to/redis.crt
tls-key-file /path/to/redis.key
tls-ca-cert-file /path/to/ca.pem
tls-auth-clients no  # Optional client cert verification
```

---

### Key Namespacing

**Enforce tenant isolation:**

```python
# Always prefix keys with tenant_id
def get_job_key(tenant_id: str, job_id: str) -> str:
    return f"job:state:tenant:{tenant_id}:job:{job_id}"

# Never use global keys
# Bad:  redis_client.set("job:123", data)
# Good: redis_client.set(get_job_key(tenant_id, "123"), data)
```

---

## Rate Limiting

### Per-Tenant Rate Limiting

**Implementation:**

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/v1/dcl/views/accounts")
@limiter.limit("60/minute")  # 60 requests per minute
def get_accounts(request: Request, current_user: User = Depends(get_current_user)):
    # Rate limited by IP + tenant_id
    return db.query(MaterializedAccount).filter_by(tenant_id=current_user.tenant_id).all()
```

**Advanced Rate Limiting (Redis-based):**

```python
import time
from shared.redis_client import get_redis_client

def check_rate_limit(tenant_id: str, max_requests: int = 60, window_seconds: int = 60) -> bool:
    """
    Token bucket rate limiter.
    
    Args:
        tenant_id: Tenant identifier
        max_requests: Maximum requests allowed in window
        window_seconds: Time window in seconds
    
    Returns:
        True if request allowed, False if rate limit exceeded
    """
    redis_client = get_redis_client()
    key = f"rate_limit:tenant:{tenant_id}"
    
    # Get current count
    current = redis_client.get(key)
    
    if current is None:
        # First request in window
        redis_client.setex(key, window_seconds, 1)
        return True
    
    if int(current) < max_requests:
        # Increment and allow
        redis_client.incr(key)
        return True
    
    # Rate limit exceeded
    return False

# Usage in endpoint
if not check_rate_limit(current_user.tenant_id, max_requests=60, window_seconds=60):
    raise HTTPException(status_code=429, detail="Rate limit exceeded")
```

**Rate Limit Headers:**

```python
@app.middleware("http")
async def add_rate_limit_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Add rate limit headers
    response.headers["X-RateLimit-Limit"] = "60"
    response.headers["X-RateLimit-Remaining"] = "42"
    response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)
    
    return response
```

---

## Input Validation

### Pydantic Schemas

**Always validate input with Pydantic:**

```python
from pydantic import BaseModel, validator, EmailStr, constr
from typing import Optional
import re

class UserRegister(BaseModel):
    email: EmailStr  # Automatic email validation
    password: constr(min_length=12)  # Minimum 12 characters
    name: constr(max_length=255)
    
    @validator('password')
    def validate_password(cls, v):
        """Enforce strong password policy."""
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain uppercase letter")
        
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain lowercase letter")
        
        if not re.search(r"\d", v):
            raise ValueError("Password must contain number")
        
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain special character")
        
        return v
    
    @validator('name')
    def validate_name(cls, v):
        """Prevent XSS via name field."""
        if re.search(r"[<>]", v):
            raise ValueError("Name cannot contain < or >")
        
        return v
```

---

### SQL Injection Prevention

**Always use parameterized queries:**

```python
# ✅ SAFE: Parameterized query
tenant_id = "550e8400-e29b-41d4-a716-446655440000"
users = db.query(User).filter(User.tenant_id == tenant_id).all()

# ❌ UNSAFE: String concatenation (SQL injection risk)
query = f"SELECT * FROM users WHERE tenant_id = '{tenant_id}'"
db.execute(query)
```

**Use ORM (SQLAlchemy):**

```python
# SQLAlchemy automatically parameterizes queries
# No SQL injection risk
db.query(User).filter(
    User.email == user_input_email,
    User.tenant_id == tenant_id
).first()
```

---

### XSS Prevention

**Sanitize output in frontend:**

```tsx
// React automatically escapes HTML by default
<div>{userInput}</div>  // ✅ Safe

// Use dangerouslySetInnerHTML ONLY with sanitized HTML
import DOMPurify from 'dompurify';

<div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(userInput) }} />
```

**Content Security Policy (CSP):**

```nginx
# In Nginx config
add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';" always;
```

---

## Audit Logging

### Log All Mutating Operations

**Implementation:**

```python
from app.models import ApiJournal

@app.middleware("http")
async def audit_log_middleware(request: Request, call_next):
    """Log all API requests to audit table."""
    start_time = time.time()
    
    response = await call_next(request)
    
    # Only log mutating operations (POST, PUT, DELETE)
    if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Get current user (if authenticated)
        user = getattr(request.state, "user", None)
        
        # Log to database
        db = SessionLocal()
        try:
            audit_log = ApiJournal(
                tenant_id=user.tenant_id if user else None,
                agent_id=str(user.id) if user else None,
                route=request.url.path,
                method=request.method,
                status=response.status_code,
                latency_ms=duration_ms,
                trace_id=request.headers.get("X-Trace-ID"),
                body_sha256=hashlib.sha256(await request.body()).hexdigest()
            )
            db.add(audit_log)
            db.commit()
        finally:
            db.close()
    
    return response
```

**Audit Log Retention:**

- **Production:** 1 year
- **Staging:** 90 days
- **Development:** 30 days

**Compliance:**

- ✅ Log all authentication attempts (success/failure)
- ✅ Log all data mutations (create, update, delete)
- ✅ Log all permission changes
- ✅ Include timestamp, user ID, tenant ID, IP address
- ❌ Never log passwords or secrets
- ❌ Never log personally identifiable information (PII) in plaintext

---

## Compliance

### GDPR (General Data Protection Regulation)

**Requirements:**

1. **Right to Access:** Users can request all data stored about them
2. **Right to Erasure:** Users can request deletion of their data
3. **Data Portability:** Users can export their data in machine-readable format
4. **Consent:** Explicit consent required for data processing

**Implementation:**

```python
# Right to access (data export)
@app.get("/api/v1/users/me/data-export")
def export_user_data(current_user: User = Depends(get_current_user)):
    """Export all user data (GDPR compliance)."""
    export = {
        "user": current_user.__dict__,
        "canonical_events": [e.__dict__ for e in db.query(CanonicalStream).filter_by(tenant_id=current_user.tenant_id).all()],
        "mapping_registry": [m.__dict__ for m in db.query(MappingRegistry).filter_by(tenant_id=current_user.tenant_id).all()],
    }
    
    return export

# Right to erasure (data deletion)
@app.delete("/api/v1/users/me")
def delete_user_account(current_user: User = Depends(get_current_user)):
    """Delete user account and all associated data (GDPR compliance)."""
    # See Operational Procedures for complete tenant offboarding process
    # ...
```

---

### SOC 2 (Service Organization Control)

**Key Controls:**

1. **Access Control:** Multi-factor authentication (MFA)
2. **Encryption:** Data encrypted at rest and in transit
3. **Monitoring:** Continuous security monitoring and alerting
4. **Incident Response:** Documented incident response plan
5. **Audit Logging:** Complete audit trail of all system access

**Checklist:**

- ✅ TLS 1.2+ for all external communications
- ✅ AES-256 encryption for data at rest
- ✅ MFA for admin access
- ✅ Role-based access control (RBAC)
- ✅ Automated vulnerability scanning
- ✅ Annual penetration testing
- ✅ Incident response plan documented
- ✅ Business continuity / disaster recovery plan

---

## Security Incident Response

**Process:**

1. **Detection:** Alerting system triggers (unauthorized access, data breach, etc.)
2. **Containment:** Isolate affected systems, revoke compromised credentials
3. **Eradication:** Remove malicious code, patch vulnerabilities
4. **Recovery:** Restore systems from backups, verify integrity
5. **Lessons Learned:** Postmortem, update security controls

**Contacts:**

- **Security Team:** security@autonomos.dev
- **On-Call:** +1-555-0100 (PagerDuty)
- **Legal:** legal@autonomos.dev

---

## Security Checklist

### Production Deployment

- [ ] All secrets stored in environment variables (not code)
- [ ] TLS/SSL enabled for all external connections
- [ ] Database connections encrypted (SSL)
- [ ] Redis password authentication enabled
- [ ] JWT secret key is strong (32+ bytes) and rotated quarterly
- [ ] Rate limiting enabled (60 req/min per tenant)
- [ ] Input validation with Pydantic schemas
- [ ] SQL injection prevention (ORM only, no raw queries)
- [ ] XSS prevention (CSP headers, sanitized output)
- [ ] Audit logging enabled (all mutations logged)
- [ ] Firewall configured (only ports 80, 443, 22 open)
- [ ] Security headers configured (HSTS, CSP, X-Frame-Options)
- [ ] Vulnerability scanning automated (weekly)
- [ ] Backup and disaster recovery plan tested
- [ ] Incident response plan documented and reviewed

---

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [CIS Benchmarks](https://www.cisecurity.org/cis-benchmarks/)
- [Deployment Guide](../deployment/DEPLOYMENT_GUIDE.md)
- [Operational Procedures](../operations/OPERATIONAL_PROCEDURES.md)
