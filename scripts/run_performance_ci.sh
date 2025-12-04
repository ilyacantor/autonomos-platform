#!/bin/bash
# Performance CI Suite - Automated benchmarking and regression detection
#
# Usage:
#   ./scripts/run_performance_ci.sh [--quick] [--full]
#
# Options:
#   --quick   Run only small workload tests (fast)
#   --full    Run all workload profiles including enterprise (slow)
#   (default) Run small and medium workloads

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  PERFORMANCE CI SUITE"
echo "  Started: $(date)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

MODE="${1:---default}"

mkdir -p results
mkdir -p benchmarks/baselines

BASELINE_CONFIG="benchmarks/baselines/baseline_config.yaml"
if [ ! -f "$BASELINE_CONFIG" ]; then
    echo "⚠️  Baseline configuration not found: $BASELINE_CONFIG"
    echo "   Creating default baseline configuration..."
    python -c "
import yaml
baseline = {
    'environment': {
        'system': 'CI Environment',
        'description': 'Auto-generated baseline'
    },
    'targets': {
        'small_workload': {
            'max_latency_p95_ms': 5000,
            'min_throughput_jobs_per_sec': 2,
            'max_error_rate_percent': 5
        },
        'medium_workload': {
            'max_latency_p95_ms': 15000,
            'min_throughput_jobs_per_sec': 5,
            'max_error_rate_percent': 5
        }
    },
    'regression_thresholds': {
        'latency_p95_increase_percent': 20,
        'throughput_decrease_percent': 15,
        'error_rate_increase_percent': 5
    }
}
with open('$BASELINE_CONFIG', 'w') as f:
    yaml.dump(baseline, f)
    "
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  STEP 1: ENVIRONMENT CHECK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if ! python --version &> /dev/null; then
    echo "❌ Python not found"
    exit 1
fi

if ! python -c "from shared.redis_client import get_redis_client; assert get_redis_client() is not None" 2>/dev/null; then
    echo "❌ Redis connection failed"
    exit 1
fi

echo "✅ Environment check passed"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  STEP 2: BENCHMARK EXECUTION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$MODE" == "--quick" ]; then
    echo "Running QUICK mode (small workload only)"
    
    echo ""
    echo "→ Running small workload benchmark (3 iterations)..."
    python scripts/benchmark_distributed_jobs.py --profile small --iterations 3 --output results
    
elif [ "$MODE" == "--full" ]; then
    echo "Running FULL mode (all workloads)"
    
    echo ""
    echo "→ Running small workload benchmark (3 iterations)..."
    python scripts/benchmark_distributed_jobs.py --profile small --iterations 3 --output results
    
    echo ""
    echo "→ Running medium workload benchmark (2 iterations)..."
    python scripts/benchmark_distributed_jobs.py --profile medium --iterations 2 --output results
    
    echo ""
    echo "→ Running large workload benchmark (1 iteration)..."
    python scripts/benchmark_distributed_jobs.py --profile large --iterations 1 --output results
    
else
    echo "Running DEFAULT mode (small + medium workloads)"
    
    echo ""
    echo "→ Running small workload benchmark (3 iterations)..."
    python scripts/benchmark_distributed_jobs.py --profile small --iterations 3 --output results
    
    echo ""
    echo "→ Running medium workload benchmark (2 iterations)..."
    python scripts/benchmark_distributed_jobs.py --profile medium --iterations 2 --output results
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  STEP 3: LOAD TESTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo ""
echo "→ Running load performance tests..."
pytest tests/test_load_performance.py -v --tb=short -m "not slow" || {
    echo "⚠️  Some load tests failed (non-blocking)"
}

if [ "$MODE" == "--full" ]; then
    echo ""
    echo "→ Running extended load tests (including multi-tenant and stress tests)..."
    pytest tests/test_load_performance_extended.py -v --tb=short || {
        echo "⚠️  Some extended tests failed (non-blocking)"
    }
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  STEP 4: BASELINE COMPARISON"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

LATEST_RESULT="results/latest.json"

if [ -f "$LATEST_RESULT" ]; then
    echo ""
    echo "→ Comparing against baseline targets..."
    
    PREVIOUS_BASELINE="benchmarks/baselines/baseline_v1.json"
    
    if [ -f "$PREVIOUS_BASELINE" ]; then
        python scripts/compare_to_baseline.py \
            --current "$LATEST_RESULT" \
            --baseline "$BASELINE_CONFIG" \
            --previous "$PREVIOUS_BASELINE" \
            --fail-on-regression \
            --output "results/comparison_report.txt" || {
            echo ""
            echo "❌ PERFORMANCE REGRESSION DETECTED"
            echo "   Review: results/comparison_report.txt"
            exit 1
        }
    else
        python scripts/compare_to_baseline.py \
            --current "$LATEST_RESULT" \
            --baseline "$BASELINE_CONFIG" \
            --output "results/comparison_report.txt" || {
            echo ""
            echo "⚠️  Baseline targets not met (no previous baseline for comparison)"
        }
        
        cp "$LATEST_RESULT" "$PREVIOUS_BASELINE"
        echo "   Saved current results as new baseline: $PREVIOUS_BASELINE"
    fi
else
    echo "⚠️  No benchmark results found to compare"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  STEP 5: METRICS EXPORT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo ""
echo "→ Exporting Prometheus metrics..."
python scripts/export_metrics_prometheus.py --output results/metrics.prom || {
    echo "⚠️  Metrics export failed (non-blocking)"
}

if [ -f "results/metrics.prom" ]; then
    echo "   Metrics saved to: results/metrics.prom"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ PERFORMANCE CI COMPLETE"
echo "  Finished: $(date)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo ""
echo "📊 Results Summary:"
echo "   - Benchmark results: results/"
echo "   - Comparison report: results/comparison_report.txt"
echo "   - Prometheus metrics: results/metrics.prom"
echo ""
