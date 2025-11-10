# Why GPU/CUDA Support Was Installed

## Root Cause Analysis

### The Dependency Chain

```
requirements.txt
  └── sentence-transformers==3.3.1
        └── torch (unspecified version)
              └── DEFAULT PyPI torch = CUDA-enabled (2.9.0)
                    └── 15+ nvidia-* packages (4.3GB)
```

### What Happened

1. **requirements.txt** specified `sentence-transformers==3.3.1`
2. **sentence-transformers** requires `torch` (no version specified)
3. When pip installs `torch` without explicit instructions, it pulls from **PyPI's default**
4. **PyPI's default torch package** is the **CUDA-enabled version** (for GPU acceleration)
5. This triggered installation of **15 NVIDIA CUDA packages** totaling **4.3GB**

### Torch Dependencies (from pip show)

```
Name: torch
Version: 2.9.0
Requires: 
  - nvidia-cublas-cu12
  - nvidia-cuda-cupti-cu12
  - nvidia-cuda-nvrtc-cu12
  - nvidia-cuda-runtime-cu12
  - nvidia-cudnn-cu12
  - nvidia-cufft-cu12
  - nvidia-cufile-cu12
  - nvidia-curand-cu12
  - nvidia-cusolver-cu12
  - nvidia-cusparse-cu12
  - nvidia-cusparselt-cu12
  - nvidia-nccl-cu12
  - nvidia-nvjitlink-cu12
  - nvidia-nvshmem-cu12
  - nvidia-nvtx-cu12
Required-by: sentence-transformers
```

## Who Needed Torch?

### ✅ Legitimate Requirement
- **sentence-transformers** → Requires torch for neural network inference

### ❌ No GPU Requirements
- **presidio-analyzer** → Only needs: phonenumbers, pyyaml, regex, spacy, tldextract
- **presidio-anonymizer** → Only needs: azure-core, pycryptodome
- **All other packages** → No ML/GPU dependencies

## Why No One Noticed

1. **Implicit dependency**: No explicit `torch` in requirements.txt
2. **PyPI default behavior**: pip automatically chooses CUDA version
3. **Works locally**: CUDA libraries work on CPU (just larger)
4. **Silent installation**: No warning about GPU packages on CPU-only machines
5. **Local development**: .pythonlibs directory hidden, size not immediately visible

## The Fix

### Before (Automatic GPU Installation)
```txt
# requirements.txt
sentence-transformers==3.3.1  # Pulls torch with CUDA (6GB)
```

### After (Explicit CPU-Only)
```txt
# requirements-cpu.txt (install FIRST)
--extra-index-url https://download.pytorch.org/whl/cpu
torch==2.9.0+cpu
torchvision==0.20.0+cpu
torchaudio==2.9.0+cpu

# requirements.txt (install SECOND)
sentence-transformers==3.3.1  # Now uses pre-installed CPU torch
```

## PyTorch Distribution Strategy

PyTorch maintains separate builds:

| Distribution | Size | Use Case | PyPI URL |
|--------------|------|----------|----------|
| CUDA 12.8 (default) | ~6GB | GPU training/inference | `pip install torch` |
| CUDA 11.8 | ~6GB | Older GPUs | Special URL |
| CPU-only | ~1GB | CPU inference | `https://download.pytorch.org/whl/cpu` |
| ROCm (AMD GPU) | ~6GB | AMD GPUs | Special URL |

**PyPI's default = CUDA 12.8** (assumes most users have GPUs)

## Impact

### Storage Breakdown
- PyTorch CUDA: 1.7GB
- NVIDIA packages: 4.3GB
- **Total GPU overhead**: 6.0GB
- **CPU-only version**: 1.0GB
- **Savings**: 5.0GB (83% reduction)

### Why CPU-Only Works for AutonomOS

1. **Inference-only workload**: No model training, just running pre-trained models
2. **Low request volume**: NLP Gateway and AAM intelligence don't need GPU speed
3. **Acceptable latency**: CPU inference is fast enough (<100ms for embeddings)
4. **Cost savings**: No GPU hardware needed in deployment

## Lessons Learned

### ⚠️ PyPI Default Behavior
- pip always installs CUDA torch unless told otherwise
- `pip install torch` ≠ CPU-only
- Must use `--extra-index-url https://download.pytorch.org/whl/cpu`

### ✅ Best Practices
1. **Always specify torch source** for CPU deployments
2. **Install torch BEFORE** ML libraries (sentence-transformers, transformers, etc.)
3. **Use requirements-cpu.txt** as a separate step
4. **Check installed packages**: `pip list | grep nvidia` should be empty
5. **Monitor .pythonlibs size** during development

## Verification

To confirm CPU-only installation:

```bash
# Should show NO nvidia packages
pip list | grep nvidia

# Should show CPU version
pip show torch | grep Version
# Output: Version: 2.9.0+cpu

# Should work without errors
python -c "from sentence_transformers import SentenceTransformer; print('OK')"
```

## Alternative Solutions (Not Implemented)

1. **ONNX Runtime** (~300MB lighter)
   - Convert models to ONNX format
   - Use onnxruntime instead of PyTorch
   - More complex setup

2. **Lighter embedding models**
   - Switch to smaller models (MiniLM-L3 vs L6)
   - Marginal savings (~20MB)

3. **Separate NLP service**
   - Move sentence-transformers to dedicated microservice
   - Adds deployment complexity

## Summary

**Nobody explicitly requested GPU support** - it was installed automatically because:
- sentence-transformers requires torch
- PyPI's default torch includes CUDA
- No one specified CPU-only installation

**The fix is simple**: Install CPU-only torch first, then everything else uses that version.
