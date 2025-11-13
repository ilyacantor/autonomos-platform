# ✅ Deployment Checklist - Image Size Optimizations

## Pre-Deployment Verification

### 1. Configuration Files in Place
- [x] `.dockerignore` - Excludes 11.6GB of unnecessary files
- [x] `requirements-cpu.txt` - CPU-only PyTorch installation
- [x] `requirements.txt` - Reorganized, no duplicates
- [x] `install-dependencies.sh` - Automated Python installation
- [x] `build.sh` - Updated to use install-dependencies.sh
- [x] `.replit` - Deployment config points to build.sh

### 2. Build Process Verification

The deployment will execute:
```bash
bash build.sh
```

Which runs:
1. ✅ `bash install-dependencies.sh` - Installs CPU-only PyTorch first
2. ✅ Frontend build with optimization
3. ✅ Cache cleanup

### 3. Expected Exclusions (.dockerignore)

The following will be **excluded** from deployment image:

**Python (7.4GB excluded):**
- `.pythonlibs/` - Local Python environment
- `.cache/` - Pip cache (4.1GB)
- `.local/` - Local binaries
- `__pycache__/`, `*.pyc` files

**Git (135MB excluded):**
- `.git/` directory
- `.gitignore`, `.gitattributes`

**Node (159MB excluded):**
- `node_modules/` - Will be rebuilt
- `frontend/node_modules/`

**Development files:**
- `tests/`, `*.test.js`, `*.spec.ts`
- Documentation (all `.md` files except README)
- `docs/`, `attached_assets/`, `mock_sources/`, `seeds/`

### 4. Expected Image Size

| Component | Size | Notes |
|-----------|------|-------|
| Base Python + FastAPI | ~200MB | Core dependencies |
| PyTorch CPU-only | ~1.0GB | AI/ML inference |
| Other Python packages | ~300MB | Database, Redis, etc. |
| Frontend build | ~2MB | Optimized static assets |
| **TOTAL** | **~1.5GB** | ✅ Well under 8GB limit |

### 5. Installation Order (Critical)

```bash
# 1. CPU-only PyTorch FIRST (prevents CUDA)
pip install --no-cache-dir -r requirements-cpu.txt

# 2. Other dependencies (use CPU torch)
pip install --no-cache-dir -r requirements.txt

# 3. Clean cache
rm -rf ~/.cache/pip
```

This order is **critical** - installing sentence-transformers before torch will pull CUDA (6GB).

### 6. Verification Commands

After deployment, verify:

```bash
# Should show NO nvidia packages
pip list | grep nvidia
# Expected: (empty)

# Should show CPU version
pip show torch | grep Version
# Expected: Version: 2.9.0+cpu

# Check image size (if accessible)
du -sh /
# Expected: <2GB
```

## What Changed from Failed Deployment

### Before (>8GB - FAILED)
```bash
# build.sh
npm install          # Only built frontend
# No Python optimization
# PyTorch installed with CUDA (6GB)
# No .dockerignore (included everything)
```

### After (1.5GB - SHOULD PASS)
```bash
# build.sh
bash install-dependencies.sh  # CPU-only PyTorch
npm ci                        # Optimized frontend
# Cleanup caches
# .dockerignore excludes 11.6GB
```

## Deployment Command

The deployment will automatically run:
```bash
bash build.sh  # Configured in .replit [deployment] section
```

## Troubleshooting

### If deployment still fails with size error:

1. **Check logs for "nvidia" packages:**
   - If present: Installation order was wrong
   - Fix: Ensure requirements-cpu.txt installed FIRST

2. **Check what's included in image:**
   - Verify .dockerignore is being used
   - Check if .pythonlibs or .cache are included

3. **Verify build.sh executed:**
   - Look for "Step 1/3: Installing Python dependencies" in logs
   - Should see "No GPU packages found" confirmation

4. **Manual verification after deployment:**
   ```bash
   pip list | wc -l        # Should be ~30-40 packages
   pip list | grep nvidia  # Should be empty
   du -sh .pythonlibs      # Should be ~1.5GB, not 7GB
   ```

## Success Criteria

✅ Deployment image size: **<2GB** (target: 1.5GB)  
✅ No NVIDIA/CUDA packages installed  
✅ All AI/ML features work (NLP Gateway, AAM intelligence)  
✅ Frontend loads correctly  
✅ Database migrations run successfully  

## Post-Deployment Testing

Once deployed, test:
1. NLP Gateway responds correctly
2. AAM intelligence endpoints work
3. Sentence embeddings generate (CPU inference)
4. Frontend loads and functions
5. Check response times (CPU should be <100ms for embeddings)

## Notes

- **CPU inference is sufficient** for AutonomOS workload
- No GPU needed for inference-only operations
- If performance issues arise, consider ONNX optimization
- Image size reduction: 8GB → 1.5GB (81% reduction)
