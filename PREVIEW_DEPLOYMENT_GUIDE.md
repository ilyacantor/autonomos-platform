# 🎬 Preview Deployment Guide for AutonomOS

## Overview

Preview deployments allow you to test changes in a production-like environment before merging to main. This guide covers setting up and using preview deployments on Render.

## What are Preview Deployments?

Preview deployments are temporary, isolated instances of your application that:
- Deploy automatically when you open a pull request or push to a feature branch
- Have their own database and Redis instance
- Expire after 7 days of inactivity (configurable)
- Allow testing features without affecting production

## Architecture

```
Production Environment
├── autonomos-platform (main branch)
├── autonomos-db (production database)
└── Redis via REDIS_URL env var

Preview Environment
├── autonomos-platform-preview (feature branches)
├── autonomos-db-preview (isolated preview database)
└── autonomos-redis-preview (isolated preview Redis)
```

## Setup on Render

### 1. Initial Configuration

The `render.yaml` file already contains the preview configuration. To enable previews:

1. **Push to main branch first** (if not already done)
   ```bash
   git checkout main
   git push origin main
   ```

2. **Connect your repository to Render**
   - Go to https://dashboard.render.com
   - Click "New +" → "Blueprint"
   - Select your repository
   - Render will detect `render.yaml` and create all services

3. **Configure environment variables**
   - Go to your production service settings
   - Add required environment variables:
     - `REDIS_URL` - External Redis (e.g., Upstash)
     - `GEMINI_API_KEY` - Your Gemini API key
     - `PINECONE_API_KEY` - Your Pinecone API key
     - `SECRET_KEY` - Generate with `openssl rand -hex 32`
     - `API_KEY` - Generate with `openssl rand -hex 32`

### 2. Enable Preview Deployments

1. **Go to your web service** on Render dashboard
2. Click "Settings" → "Preview Environments"
3. **Enable "Create previews automatically for pull requests"**
4. Set preview expiration (default: 7 days)
5. Click "Save Changes"

### 3. Configure Preview Environment Variables

Preview deployments inherit most environment variables from production, but some are auto-generated:

**Auto-configured by Render:**
- `DATABASE_URL` - From `autonomos-db-preview`
- `REDIS_URL` - From `autonomos-redis-preview`
- `SECRET_KEY` - Auto-generated unique key
- `API_KEY` - Auto-generated unique key
- `ALLOWED_WEB_ORIGIN` - Auto-set to preview URL
- `ENVIRONMENT=preview` - Identifies this as preview

**Must be set manually (shared with production):**
- `GEMINI_API_KEY`
- `PINECONE_API_KEY`
- `SLACK_WEBHOOK_URL` (optional)

## Using Preview Deployments

### Creating a Preview

1. **Create a feature branch**
   ```bash
   git checkout -b feature/my-new-feature
   ```

2. **Make your changes and commit**
   ```bash
   git add .
   git commit -m "Add my new feature"
   ```

3. **Push to remote**
   ```bash
   git push -u origin feature/my-new-feature
   ```

4. **Open a Pull Request on GitHub**
   - Render will automatically detect the PR
   - A preview deployment will be created
   - You'll receive a comment with the preview URL

5. **Access your preview**
   - URL format: `https://autonomos-platform-preview-pr-XXX.onrender.com`
   - Check the PR comments for the exact URL

### Testing in Preview

1. **Register a new user** in the preview environment
   - Preview has its own isolated database
   - Data won't affect production

2. **Test your changes thoroughly**
   - Click through all features
   - Test AAM monitoring dashboard
   - Test DCL connections
   - Verify database migrations work

3. **Check logs** if issues arise
   - Go to Render dashboard
   - Select the preview service
   - Click "Logs" tab

### Updating a Preview

When you push new commits to your branch:
```bash
git add .
git commit -m "Fix bug in feature"
git push
```

Render automatically redeploys the preview with your changes.

### Deleting a Preview

Previews are automatically deleted when:
- The pull request is merged
- The pull request is closed
- 7 days pass without activity (configurable)

To manually delete:
1. Go to Render dashboard
2. Find the preview service
3. Click "Delete Service"

## Preview vs Production Differences

| Feature | Production | Preview |
|---------|-----------|---------|
| **Branch** | `main` | Any feature branch |
| **Database** | `autonomos-db` | `autonomos-db-preview` |
| **Redis** | External (Upstash) | `autonomos-redis-preview` |
| **URL** | `autonomos-platform.onrender.com` | `autonomos-platform-preview-pr-XX.onrender.com` |
| **Auto-deploy** | ✅ Yes (on main push) | ✅ Yes (on branch push) |
| **Lifespan** | Permanent | 7 days after last activity |
| **Environment** | `ENVIRONMENT=production` | `ENVIRONMENT=preview` |
| **Secrets** | Manually set | Auto-generated or inherited |

## Best Practices

### 1. Test Before Merging
- Always create a preview for significant changes
- Test all features that might be affected
- Check for database migration issues

### 2. Use Preview for Collaboration
- Share the preview URL with teammates for review
- Test API endpoints with real data
- Verify frontend/backend integration

### 3. Monitor Resource Usage
- Preview deployments use resources
- Delete unused previews manually if needed
- Set reasonable expiration times

### 4. Keep Secrets Secure
- Preview environments use the same API keys as production
- Don't commit sensitive data to feature branches
- Be cautious with third-party API calls from previews

### 5. Database Migrations
- Preview deployments run migrations automatically
- Test migration scripts in preview first
- Check `alembic` logs in Render dashboard

## Troubleshooting

### Preview Deployment Fails

**Symptom:** Build fails or service won't start

**Solutions:**
1. Check build logs in Render dashboard
2. Verify `requirements.txt` is up to date
3. Ensure all migrations are committed
4. Check for syntax errors in code

### Database Connection Errors

**Symptom:** `relation "users" does not exist` or similar

**Solutions:**
1. Verify `DATABASE_URL` is set correctly
2. Check migration logs: `alembic current`
3. Manually run migrations if needed:
   ```bash
   alembic upgrade head
   ```

### Redis Connection Errors

**Symptom:** `Error connecting to Redis`

**Solutions:**
1. Verify `REDIS_URL` is configured in `render.yaml`
2. Check that `autonomos-redis-preview` service is running
3. Check Redis logs in Render dashboard

### Preview URL Not Working

**Symptom:** 404 or service not found

**Solutions:**
1. Wait 3-5 minutes for initial deployment
2. Check service status in Render dashboard
3. Verify the service didn't fail to start (check logs)

### Environment Variables Not Set

**Symptom:** Missing API keys or config errors

**Solutions:**
1. Check "Environment" tab in Render service settings
2. Ensure variables are set to `sync: false` for shared secrets
3. Add missing variables manually

## Cost Considerations

Preview deployments incur costs:
- **Starter plan**: ~$7/month per preview service
- **Preview database**: ~$7/month per database
- **Preview Redis**: ~$10/month per Redis instance

To minimize costs:
- Set short expiration times (1-3 days)
- Delete previews after testing
- Use previews only for significant features

## Advanced Configuration

### Custom Preview Branch Pattern

To limit previews to specific branches, modify `render.yaml`:

```yaml
- type: web
  name: autonomos-platform-preview
  previewsEnabled: true
  previewsExpireAfterDays: 7
  # Only create previews for branches matching pattern
  branch: feature/*
```

### Different Plan for Previews

To use a smaller/larger plan for previews:

```yaml
- type: web
  name: autonomos-platform-preview
  plan: free  # or starter, standard, pro
```

### Custom Build Commands for Previews

```yaml
- type: web
  name: autonomos-platform-preview
  buildCommand: |
    pip install -r requirements.txt
    # Run preview-specific setup
    python scripts/setup_preview.py
```

## Monitoring Previews

### Check Preview Status

```bash
# Using Render API
curl -H "Authorization: Bearer $RENDER_API_KEY" \
  https://api.render.com/v1/services?name=autonomos-platform-preview
```

### View Preview Logs

1. Go to Render dashboard
2. Select preview service
3. Click "Logs" tab
4. Filter by time range or search for errors

### Preview Metrics

Track preview performance:
- Response times
- Error rates
- Database query performance
- Redis cache hit rates

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Preview Deployment

on:
  pull_request:
    branches: [ main ]

jobs:
  test-preview:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Wait for Render Preview
        run: |
          # Wait for preview deployment
          sleep 180
      - name: Test Preview Deployment
        run: |
          # Run smoke tests against preview URL
          python scripts/smoke_test.py --url $PREVIEW_URL
```

## FAQ

### Q: Can I have multiple preview deployments?
**A:** Yes! Each PR/branch gets its own preview deployment.

### Q: Do previews share the production database?
**A:** No, previews use an isolated `autonomos-db-preview` database.

### Q: Can I connect previews to external services?
**A:** Yes, but be careful with production APIs. Use test/sandbox endpoints when possible.

### Q: How do I access preview logs?
**A:** Via Render dashboard → Select preview service → Logs tab.

### Q: Can I SSH into a preview deployment?
**A:** Render doesn't support SSH, but you can use the web shell in the dashboard.

### Q: Do preview migrations affect production?
**A:** No, preview migrations only affect the preview database.

## Support

For issues with preview deployments:

1. **Check Render Status**: https://status.render.com
2. **Render Docs**: https://render.com/docs/preview-environments
3. **GitHub Issues**: Open an issue in the repository
4. **Render Support**: support@render.com

---

**Last Updated:** November 2025
**Maintainer:** AutonomOS Team
