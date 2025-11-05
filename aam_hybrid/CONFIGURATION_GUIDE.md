# AAM Configuration Guide

## Required Configuration

The AAM Orchestrator **will not start** without these required credentials. You'll see a clear error message at startup listing any missing values.

### 1. Airbyte Credentials (REQUIRED)

These are all **mandatory** for AAM to function:

| Variable | Source | How to Get |
|----------|--------|------------|
| `AIRBYTE_CLIENT_ID` | abctl credentials | Run `abctl local credentials` |
| `AIRBYTE_CLIENT_SECRET` | abctl credentials | Run `abctl local credentials` |
| `AIRBYTE_WORKSPACE_ID` | Airbyte UI | See instructions below |
| `AIRBYTE_DESTINATION_ID` | Airbyte UI | See instructions below |

#### Getting Workspace and Destination IDs

**Option 1: Via Airbyte UI (Easiest)**

1. Open `http://localhost:8000` and log in
2. Navigate to **Connections** → **Destinations**
3. Create or select a destination (PostgreSQL, BigQuery, etc.)
4. The URL will show the ID: `localhost:8000/workspaces/{WORKSPACE_ID}/destinations/{DESTINATION_ID}`

**Option 2: Via API**

```bash
# Get access token
TOKEN=$(curl -s -X POST http://localhost:8000/api/public/v1/applications/token \
  -H "Content-Type: application/json" \
  -d "{\"client_id\":\"$AIRBYTE_CLIENT_ID\",\"client_secret\":\"$AIRBYTE_CLIENT_SECRET\"}" \
  | jq -r '.access_token')

# List workspaces
curl http://localhost:8000/api/public/v1/workspaces \
  -H "Authorization: Bearer $TOKEN" | jq '.workspaces[0].workspaceId'

# List destinations
curl http://localhost:8000/api/public/v1/destinations \
  -H "Authorization: Bearer $TOKEN" | jq '.destinations[0].destinationId'
```

---

### 2. Salesforce OAuth Credentials (OPTIONAL)

Required only if you plan to onboard Salesforce connections. The Auth Broker will fail with a clear error if these are missing when attempting Salesforce onboarding.

| Variable | Description |
|----------|-------------|
| `SALESFORCE_CLIENT_ID` | OAuth Connected App Consumer Key |
| `SALESFORCE_CLIENT_SECRET` | OAuth Connected App Consumer Secret |
| `SALESFORCE_REFRESH_TOKEN` | OAuth refresh token (never expires) |

#### How to Get Salesforce OAuth Tokens

**Step 1: Create a Connected App**

1. Log into Salesforce
2. Go to **Setup** → **App Manager**
3. Click **New Connected App**
4. Fill in:
   - **Connected App Name**: "AAM Hybrid"
   - **API Name**: `AAM_Hybrid`
   - **Contact Email**: your email
5. Enable **OAuth Settings**:
   - **Callback URL**: `https://login.salesforce.com/services/oauth2/success`
   - **Selected OAuth Scopes**:
     - `Full access (full)`
     - `Perform requests at any time (refresh_token, offline_access)`
     - `Access and manage your data (api)`
6. Save and wait 2-10 minutes for propagation
7. Click **Manage Consumer Details** to see:
   - **Consumer Key** → `SALESFORCE_CLIENT_ID`
   - **Consumer Secret** → `SALESFORCE_CLIENT_SECRET`

**Step 2: Get Refresh Token**

Use OAuth 2.0 Web Server Flow:

```bash
# 1. Construct authorization URL (replace CLIENT_ID with your Consumer Key)
https://login.salesforce.com/services/oauth2/authorize?response_type=code&client_id=YOUR_CLIENT_ID&redirect_uri=https://login.salesforce.com/services/oauth2/success

# 2. Visit URL in browser, log in, approve
# 3. You'll be redirected to: https://login.salesforce.com/services/oauth2/success?code=AUTHORIZATION_CODE
# 4. Copy the AUTHORIZATION_CODE from URL

# 5. Exchange code for tokens
curl -X POST https://login.salesforce.com/services/oauth2/token \
  -d "grant_type=authorization_code" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "redirect_uri=https://login.salesforce.com/services/oauth2/success" \
  -d "code=AUTHORIZATION_CODE"

# Response includes:
# - access_token (expires in 2 hours)
# - refresh_token (never expires) ← SAVE THIS
# - instance_url
# - id, etc.
```

Save the `refresh_token` to `SALESFORCE_REFRESH_TOKEN` environment variable.

**Step 3: Verify**

```bash
# Test token validity
curl -X POST https://login.salesforce.com/services/oauth2/token \
  -d "grant_type=refresh_token" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "refresh_token=YOUR_REFRESH_TOKEN"

# Should return a new access_token
```

---

### 3. Database & Redis

| Variable | Default | Notes |
|----------|---------|-------|
| `SUPABASE_DB_URL` | Local PostgreSQL | Use Replit PostgreSQL or local |
| `REDIS_URL` | `redis://localhost:6379` | Use Replit Redis or local |

---

## Validation

The Orchestrator validates all required configuration on startup. If any are missing, you'll see:

```
❌ CRITICAL: Missing required Airbyte credentials: AIRBYTE_CLIENT_ID, AIRBYTE_WORKSPACE_ID

These are REQUIRED for AAM to function. Please:
1. Run: abctl local credentials
2. Set AIRBYTE_CLIENT_ID and AIRBYTE_CLIENT_SECRET from the output
3. Get AIRBYTE_WORKSPACE_ID and AIRBYTE_DESTINATION_ID from Airbyte UI
4. Update your .env file or docker-compose environment variables
```

Optional credentials generate warnings:

```
⚠️  WARNING: Missing optional credentials: SALESFORCE_CLIENT_ID (Salesforce onboarding will fail)
Some features may not work. Check .env.example for setup instructions.
```

---

## Environment File Example

```env
# .env file for AAM Hybrid

# Airbyte (REQUIRED)
AIRBYTE_API_URL=http://localhost:8000/api/public/v1
AIRBYTE_CLIENT_ID=abc123...
AIRBYTE_CLIENT_SECRET=xyz789...
AIRBYTE_WORKSPACE_ID=a1b2c3d4-e5f6-7890-abcd-ef1234567890
AIRBYTE_DESTINATION_ID=b2c3d4e5-f6a7-8901-bcde-f2345678901a

# Database
SUPABASE_DB_URL=postgresql://user:pass@localhost:5432/aam_registry

# Redis
REDIS_URL=redis://localhost:6379

# Salesforce (Optional - only for Salesforce connections)
SALESFORCE_CLIENT_ID=3MVG9...
SALESFORCE_CLIENT_SECRET=ABC123...
SALESFORCE_REFRESH_TOKEN=5Aep861...

# Security
SECRET_KEY=change-this-to-a-secure-random-string-min-32-characters
```

---

## Troubleshooting

### "Missing required Airbyte credentials"

**Solution:** Follow steps in error message. Run `abctl local credentials` and update `.env`.

### "Missing required Salesforce credentials"

**Cause:** Attempted to onboard Salesforce connection without OAuth tokens.

**Solution:** Either:
1. Configure Salesforce OAuth tokens (see above)
2. Onboard a different source type that doesn't require OAuth

### "Failed to retrieve credentials: 404"

**Cause:** Auth Broker couldn't find credentials for the requested source type.

**Solution:** Verify `credential_id` parameter matches a configured source (e.g., `salesforce-prod`).

### "Airbyte API 401 Unauthorized"

**Cause:** Invalid or expired Airbyte credentials.

**Solution:**
```bash
abctl local credentials  # Get fresh credentials
# Update AIRBYTE_CLIENT_ID and AIRBYTE_CLIENT_SECRET in .env
docker-compose restart orchestrator
```

---

## Security Best Practices

### Development
- Use `.env` file (gitignored by default)
- Never commit credentials to version control

### Production
- Use **HashiCorp Vault**, **AWS Secrets Manager**, or **Azure Key Vault**
- Rotate credentials regularly
- Use service accounts with minimum required permissions
- Enable audit logging for all credential access

---

## Next Steps

1. ✅ Configure all required credentials
2. ✅ Validate with `docker-compose up orchestrator` (check logs)
3. ✅ Test health endpoint: `curl http://localhost:8001/health`
4. ✅ Onboard first connection: See [README.md](./README.md) for examples
