# Airbyte OSS Setup with abctl

## Important Note
As of 2024, Airbyte has deprecated Docker Compose in favor of **abctl** (Airbyte's CLI tool). 
This guide explains how to set up Airbyte OSS using the recommended approach.

## Prerequisites
- Docker Desktop (macOS/Windows) or Docker Engine (Linux)
- 4+ CPUs, 8GB+ RAM
- Port 8000 available

## Installation Steps

### 1. Install abctl

**macOS (Homebrew):**
```bash
brew tap airbytehq/tap
brew install abctl
```

**Linux/macOS (curl):**
```bash
curl -LsfS https://get.airbyte.com | bash -
```

**Verify installation:**
```bash
abctl version
```

### 2. Deploy Airbyte OSS

**Basic local install:**
```bash
abctl local install
```

**For remote access (recommended for AAM integration):**
```bash
abctl local install --host localhost --insecure-cookies
```

**Low-resource mode (if you have 2 CPUs):**
```bash
abctl local install --low-resource-mode
```

Installation takes up to 30 minutes. Airbyte will be available at `http://localhost:8000`.

### 3. Get Credentials

```bash
abctl local credentials
```

**Output:**
```json
{
  "email": "[email protected]",
  "password": "random-generated-password",
  "client-id": "your-client-id",
  "client-secret": "your-client-secret"
}
```

**Important:** Save these credentials! You'll need:
- `client-id` and `client-secret` for AAM API authentication
- `email` and `password` for UI access

### 4. Configure AAM Environment

Create a `.env` file in the `aam-hybrid/` directory:

```env
# Airbyte Configuration
AIRBYTE_API_URL=http://localhost:8000/api/public/v1
AIRBYTE_CLIENT_ID=your-client-id-from-abctl
AIRBYTE_CLIENT_SECRET=your-client-secret-from-abctl
AIRBYTE_WORKSPACE_ID=your-workspace-id
AIRBYTE_DESTINATION_ID=your-destination-id

# Database (use Replit's PostgreSQL or local)
SUPABASE_DB_URL=postgresql://user:password@host:port/database

# Redis (use Replit's Redis or local)
REDIS_URL=redis://localhost:6379

# Salesforce Credentials (for testing)
SALESFORCE_CLIENT_ID=your-salesforce-client-id
SALESFORCE_CLIENT_SECRET=your-salesforce-client-secret

# Security
SECRET_KEY=your-secret-key-change-in-production
```

### 5. Get Workspace and Destination IDs

**Using the Airbyte UI:**
1. Log in to `http://localhost:8000` with the credentials from step 3
2. Create a workspace if needed
3. Create a destination (e.g., PostgreSQL, BigQuery, or any warehouse)
4. Note the IDs from the URLs

**Using the API:**

**Get access token:**
```bash
curl -X POST http://localhost:8000/api/public/v1/applications/token \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET"
  }'
```

**List workspaces:**
```bash
curl -X GET http://localhost:8000/api/public/v1/workspaces \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**List destinations:**
```bash
curl -X GET http://localhost:8000/api/public/v1/destinations \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 6. Verify AAM Connection

Test the Airbyte client:
```bash
cd aam-hybrid
python -c "
from shared.airbyte_client import airbyte_client
import asyncio

async def test():
    token = await airbyte_client._ensure_token()
    print(f'Token obtained: {airbyte_client.access_token[:20]}...')

asyncio.run(test())
"
```

## Managing Airbyte

**Check status:**
```bash
abctl local status
```

**View logs:**
```bash
kubectl logs -n airbyte-abctl deployment/airbyte-abctl-server
```

**Restart:**
```bash
abctl local restart
```

**Upgrade Airbyte:**
```bash
abctl local install
```

**Uninstall:**
```bash
abctl local uninstall --persisted  # Removes data too
```

## Next Steps

1. ✅ Airbyte OSS is running
2. ✅ Credentials obtained
3. ✅ Environment configured
4. → Start AAM services: `docker-compose up -d`
5. → Test connection onboarding endpoint
6. → Monitor drift repair agent

## Troubleshooting

**Port 8000 already in use:**
```bash
abctl local install --port 9000
```

**Low memory:**
```bash
abctl local install --low-resource-mode
```

**Connection refused:**
- Verify Docker is running: `docker ps`
- Check Airbyte status: `abctl local status`
- Wait for all pods to be ready (up to 30 minutes)

**API authentication failed:**
- Regenerate credentials: `abctl local credentials`
- Update `.env` with new client_id and client_secret

## Resources

- **Official Airbyte Docs**: https://docs.airbyte.com/using-airbyte/getting-started/oss-quickstart
- **API Reference**: https://reference.airbyte.com/
- **abctl Documentation**: https://docs.airbyte.com/platform/deploying-airbyte/abctl
