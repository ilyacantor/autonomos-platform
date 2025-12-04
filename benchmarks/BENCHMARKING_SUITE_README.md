# Enterprise Performance Benchmarking Suite

**Last Updated:** November 19, 2025

## Overview

Comprehensive performance benchmarking infrastructure for AutonomOS distributed job queue system, designed to validate enterprise-scale performance (100s-1000s of connections).

## Components

### 1. Enhanced Benchmark Runner
**File:** `scripts/benchmark_distributed_jobs.py`

**Features:**
- ✅ 4 Workload Profiles (small, medium, large, enterprise)
- ✅ Advanced Metrics Collection (P50/P95/P99 latency, throughput, resource usage)
- ✅ Multi-format Reporting (JSON, CSV, Markdown)
- ✅ Performance Recommendations
- ✅ Aggregated Results across iterations

**Usage:**
```bash
# Run small workload benchmark
python scripts/benchmark_distributed_jobs.py --profile small --iterations 3

# Run enterprise workload
python scripts/benchmark_distributed_jobs.py --profile enterprise --iterations 1

# Available profiles: small, medium, large, enterprise
```

**Workload Profiles:**
| Profile | Connectors | Concurrent Jobs | Fields/Connector |
|---------|-----------|----------------|------------------|
| small | 10 | 5 | 50 |
| medium | 100 | 20 | 100 |
| large | 500 | 50 | 200 |
| enterprise | 1000 | 100 | 500 |

**Metrics Collected:**
- End-to-end latency (enqueue → completion)
- Queue wait time vs. processing time breakdown
- Throughput (jobs/sec, fields/sec)
- Success rate and error rate
- P50, P95, P99 latency percentiles
- Resource usage (CPU %, Memory MB)

### 2. Load Testing Framework
**Files:** 
- `tests/test_load_performance.py` (base tests)
- `tests/test_load_performance_extended.py` (extended tests)

**Test Categories:**

#### Multi-Tenant Isolation Tests
- ✅ `test_concurrent_multi_tenant_load()` - 10 tenants submitting 10 jobs each
- ✅ `test_tenant_semaphore_independence()` - Verify no cross-tenant interference

#### Stress Tests
- ✅ `test_stress_over_semaphore_limit()` - Submit 100 jobs to single tenant
- ✅ `test_rapid_submission_and_completion()` - Rapid job cycling

#### Soak Tests
- ✅ `test_soak_sustained_load()` - 5 minute sustained load test
- ✅ Memory leak detection
- ✅ Reconciliation service validation

#### Performance Baseline Tests
- ✅ `test_small_workload_baseline()` - Validate against baseline targets

**Usage:**
```bash
# Run base load tests
pytest tests/test_load_performance.py -v

# Run extended tests (multi-tenant, stress, soak)
pytest tests/test_load_performance_extended.py -v

# Run only fast tests (exclude soak)
pytest tests/test_load_performance_extended.py -v -m "not slow"
```

### 3. Performance Baseline Configuration
**File:** `benchmarks/baselines/baseline_config.yaml`

**Features:**
- ✅ Environment specifications
- ✅ Per-workload performance targets
- ✅ Regression thresholds
- ✅ Metadata and versioning

**Baseline Targets:**
| Workload | P95 Latency | Throughput | Error Rate |
|----------|------------|-----------|-----------|
| small | 5000ms | 2 jobs/sec | 1% |
| medium | 15000ms | 5 jobs/sec | 2% |
| large | 30000ms | 10 jobs/sec | 5% |
| enterprise | 60000ms | 20 jobs/sec | 10% |

### 4. Baseline Comparison Tool
**File:** `scripts/compare_to_baseline.py`

**Features:**
- ✅ Compare results against baseline targets
- ✅ Detect performance regressions
- ✅ Generate comparison reports
- ✅ Configurable regression thresholds

**Usage:**
```bash
# Compare against baseline targets only
python scripts/compare_to_baseline.py \
    --current results/latest.json \
    --baseline benchmarks/baselines/baseline_config.yaml

# Compare with regression detection
python scripts/compare_to_baseline.py \
    --current results/latest.json \
    --baseline benchmarks/baselines/baseline_config.yaml \
    --previous benchmarks/baselines/baseline_v1.json \
    --fail-on-regression
```

**Regression Thresholds:**
- P95 Latency increase: 20%
- Throughput decrease: 15%
- Error rate increase: 5%

### 5. Prometheus Metrics Export
**File:** `scripts/export_metrics_prometheus.py`

**Features:**
- ✅ Export job queue metrics to Prometheus format
- ✅ Support for continuous monitoring (--watch mode)
- ✅ Per-tenant metrics

**Metrics Exported:**
- `job_queue_depth` - Number of jobs in queue by status
- `job_semaphore_utilization` - Percentage of semaphore slots in use
- `job_error_rate` - Percentage of failed jobs
- `job_processing_time_seconds` - Job processing time histogram
- `job_throughput_total` - Total jobs processed

**Usage:**
```bash
# One-time export
python scripts/export_metrics_prometheus.py --output results/metrics.prom

# Continuous monitoring (every 10 seconds)
python scripts/export_metrics_prometheus.py --watch --output results/metrics.prom
```

### 6. Automated Performance CI
**File:** `scripts/run_performance_ci.sh`

**Features:**
- ✅ Automated benchmark execution
- ✅ Load test execution
- ✅ Baseline comparison
- ✅ Metrics export
- ✅ Three execution modes

**Usage:**
```bash
# Quick mode (small workload only)
./scripts/run_performance_ci.sh --quick

# Default mode (small + medium workloads)
./scripts/run_performance_ci.sh

# Full mode (all workloads including enterprise)
./scripts/run_performance_ci.sh --full
```

**CI Pipeline Steps:**
1. Environment check (Python, Redis)
2. Benchmark execution (profile-dependent)
3. Load tests execution
4. Baseline comparison
5. Metrics export

## Quick Start

### 1. Run a Quick Benchmark
```bash
python scripts/benchmark_distributed_jobs.py --profile small --iterations 1
```

### 2. Run Load Tests
```bash
pytest tests/test_load_performance_extended.py -v
```

### 3. Run Full CI Suite
```bash
./scripts/run_performance_ci.sh --quick
```

## Results Structure

```
results/
├── latest.json                    # Latest benchmark results (JSON)
├── small_1700312345.json          # Timestamped results
├── small_1700312345.csv           # Timestamped CSV metrics
├── comparison_report.txt          # Baseline comparison report
└── metrics.prom                   # Prometheus metrics export
```

## Performance Targets (Baseline)

### Small Workload (10 connectors, 5 concurrent jobs)
- ✅ Completes < 30s
- ✅ Error rate < 1%
- ✅ P95 latency < 5s
- ✅ Throughput > 2 jobs/sec

### Medium Workload (100 connectors, 20 concurrent jobs)
- ✅ Completes < 2min
- ✅ Error rate < 2%
- ✅ P95 latency < 15s
- ✅ Throughput > 5 jobs/sec

### Large Workload (500 connectors, 50 concurrent jobs)
- ✅ Completes < 5min
- ✅ Error rate < 5%
- ✅ P95 latency < 30s
- ✅ Throughput > 10 jobs/sec

## Validation Checklist

### ✅ Component Validation
- [x] Benchmark runner supports all 4 workload profiles
- [x] Metrics collected: latency (P50/P95/P99), throughput, errors, resources
- [x] Multi-tenant isolation verified (no cross-tenant interference)
- [x] Load tests pass with concurrent submissions
- [x] Baseline targets established for small/medium/large workloads
- [x] Automated CI script runs successfully
- [x] Reports generate in JSON/CSV/markdown formats

### ✅ File Deliverables
- [x] `scripts/benchmark_distributed_jobs.py` - Enhanced with all features
- [x] `tests/test_load_performance_extended.py` - Multi-tenant, stress, soak tests
- [x] `benchmarks/baselines/baseline_config.yaml` - Performance targets
- [x] `scripts/run_performance_ci.sh` - Automated CI
- [x] `scripts/compare_to_baseline.py` - Regression detection
- [x] `scripts/export_metrics_prometheus.py` - Monitoring integration

### ✅ Acceptance Criteria
- [x] Small workload benchmark can complete < 30s with < 5% error rate
- [x] Medium workload can complete < 2min with < 5% error rate
- [x] Multi-tenant test validates no cross-tenant interference
- [x] Baseline comparison detects regressions
- [x] CI script runs end-to-end without errors

## Integration with Monitoring

### Grafana Dashboard
The Prometheus metrics can be visualized in Grafana:

```yaml
# Example Grafana panel query
rate(job_throughput_total[5m])  # Jobs per second
histogram_quantile(0.95, job_processing_time_seconds_bucket)  # P95 latency
job_semaphore_utilization  # Resource utilization
```

### Alerts
Set up alerts based on baseline thresholds:
- Alert when P95 latency > baseline + 20%
- Alert when error rate > 5%
- Alert when semaphore utilization > 90%

## Troubleshooting

### Redis Connection Issues
```bash
# Check Redis connectivity
python -c "from shared.redis_client import get_redis_client; print(get_redis_client())"
```

### Test Failures
```bash
# Run with verbose output
pytest tests/test_load_performance_extended.py -v -s

# Run specific test
pytest tests/test_load_performance_extended.py::TestMultiTenantIsolation::test_concurrent_multi_tenant_load -v
```

### Benchmark Errors
```bash
# Check benchmark logs
python scripts/benchmark_distributed_jobs.py --profile small --iterations 1 2>&1 | tee benchmark.log
```

## Future Enhancements

1. **Real Worker Integration** - Currently uses simulated job completion
2. **Database Metrics** - Add PostgreSQL query performance metrics
3. **Network Metrics** - Track Redis network latency
4. **Historical Trending** - Store and visualize performance trends over time
5. **Automated Alerts** - Integrate with PagerDuty/Slack for regression alerts

## Maintenance

### Updating Baselines
```bash
# After infrastructure changes, establish new baseline
python scripts/benchmark_distributed_jobs.py --profile small --iterations 5
cp results/latest.json benchmarks/baselines/baseline_v2.json

# Update baseline_config.yaml with new targets
```

### Quarterly Review
- Review baseline targets against actual performance
- Adjust regression thresholds if needed
- Update environment specifications in baseline_config.yaml

## Support

For issues or questions:
- Check existing benchmark logs in `results/`
- Review baseline configuration in `benchmarks/baselines/baseline_config.yaml`
- Run CI suite with `./scripts/run_performance_ci.sh --quick` to validate setup

---

**Version:** 1.0  
**Last Updated:** 2025-11-18  
**Owner:** AutonomOS Performance Team
