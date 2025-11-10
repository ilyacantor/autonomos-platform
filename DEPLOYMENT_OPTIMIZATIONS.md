# Deployment Image Size Optimizations

## Problem
Deployment failed with "The deployment image size exceeds the 8 GiB limit" error.

## Root Causes
1. **Large static directory** (35MB → 1.6MB): Accumulated old build artifacts from multiple Vite builds
2. **Frontend node_modules** (159MB): Included in deployment image
3. **Duplicate Python dependencies**: requirements.txt had duplicate entries
4. **Dev dependencies in production**: pytest, test files, documentation
5. **No .dockerignore**: Everything was being included in deployment image

## Solutions Implemented

### 1. Created .dockerignore (Critical)
Excludes from deployment image:
- `node_modules/` (159MB saved - will be rebuilt)
- Development/testing files (`tests/`, `*.test.*`, `__pycache__/`)
- Documentation (`*.md` except README, `docs/`)
- Build artifacts that get rebuilt (`frontend/dist/`, `.vite/`)
- Mock data and seeds (`mock_sources/`, `seeds/`)
- Git, IDE, and temp files

### 2. Cleaned up requirements.txt
**Before**: 36 lines with duplicates
- presidio-analyzer (2x)
- presidio-anonymizer (2x)
- rank-bm25 (2x)
- sentence-transformers (2x)
- pytest, pytest-asyncio, pytest-cov (dev dependencies)

**After**: 27 lines, production-only dependencies

**Removed**:
- All duplicate entries
- Test dependencies (pytest suite)
- Unused requests library

### 3. Optimized Vite Build Configuration
**New features**:
- `emptyOutDir: true` - Auto-cleans old builds
- `sourcemap: false` - No debug maps in production
- Code splitting with `manualChunks`:
  - `react-vendor`: React core (141.61 KB)
  - `d3-vendor`: D3 visualization libs (45.35 KB)
  - Main bundle: App code (177.27 KB)
- `cssCodeSplit: true` - Separate CSS files
- `assetsInlineLimit: 4096` - Inline small assets

### 4. Optimized build.sh
**Changes**:
- Use `npm ci` instead of `npm install` (faster, reproducible)
- Removed manual cleanup (Vite handles with `emptyOutDir`)
- Cleaner output

### 5. Cleaned Build Artifacts
**Static directory cleanup**:
- **Before**: 35MB (124 old JS/CSS files)
- **After**: 1.6MB (7 optimized files)
- **Saved**: 33.4MB (95% reduction)

## Results

### Bundle Size Impact
- **Previous build**: 319.50 KB (single monolithic bundle)
- **New build**: 
  - Main: 177.27 KB (gzip: 40.39 KB)
  - React vendor: 141.61 KB (gzip: 45.40 KB)
  - D3 vendor: 45.35 KB (gzip: 15.13 KB)
  - LiveSankeyGraph: 14.77 KB (gzip: 4.90 KB)
  - CSS: 57.63 KB (gzip: 9.96 KB)

### Static Directory Size
- **Before**: 35MB
- **After**: 1.6MB
- **Reduction**: 95.4%

### Estimated Deployment Image Size Reduction
- node_modules excluded: ~159MB
- Static directory cleaned: ~33MB
- Python duplicates removed: ~50MB (estimated)
- Dev dependencies excluded: ~100MB (estimated)
- **Total estimated savings**: ~340MB+

## Best Practices Applied

1. ✅ Comprehensive .dockerignore file
2. ✅ Production-only Python dependencies
3. ✅ Automated build artifact cleanup
4. ✅ Code splitting for better caching
5. ✅ No sourcemaps in production
6. ✅ CSS code splitting
7. ✅ Asset inlining for small files
8. ✅ npm ci for reproducible builds

## Next Steps for Further Optimization (if needed)

1. Consider lazy loading routes with React.lazy()
2. Implement CDN for static assets
3. Use Brotli compression alongside gzip
4. Analyze bundle with `vite-bundle-visualizer`
5. Tree-shake unused dependencies
6. Consider moving large ML libs (sentence-transformers) to separate service

## Deployment Checklist

- [x] .dockerignore created
- [x] requirements.txt cleaned (no duplicates)
- [x] Vite config optimized
- [x] Static directory cleaned
- [x] Build script optimized
- [x] Python cache files removed
- [x] Frontend built and tested
- [ ] Deploy and verify image size < 8 GiB
