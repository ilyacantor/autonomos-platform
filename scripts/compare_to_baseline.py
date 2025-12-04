"""
Baseline Comparison and Regression Detection

Compares current benchmark results against established baselines
and detects performance regressions.
"""

import json
import yaml
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime


class BaselineComparator:
    """Compare benchmark results against baseline targets"""
    
    def __init__(self, baseline_config_path: str):
        """Initialize with baseline configuration"""
        with open(baseline_config_path, 'r') as f:
            self.baseline_config = yaml.safe_load(f)
        
        self.targets = self.baseline_config['targets']
        self.regression_thresholds = self.baseline_config['regression_thresholds']
    
    def load_results(self, results_path: str) -> Dict:
        """Load benchmark results from JSON file"""
        with open(results_path, 'r') as f:
            return json.load(f)
    
    def compare_to_targets(self, results: Dict) -> Tuple[bool, List[str]]:
        """Compare results against baseline targets"""
        workload_profile = results['metadata']['workload_profile']
        
        if workload_profile not in self.targets:
            return False, [f"❌ Unknown workload profile: {workload_profile}"]
        
        targets = self.targets[workload_profile]
        violations = []
        warnings = []
        
        exec_data = results['execution']
        perf_data = results['performance']
        resources = results['resources']
        
        if exec_data['error_rate_percent'] > targets['max_error_rate_percent']:
            violations.append(
                f"❌ Error Rate: {exec_data['error_rate_percent']:.2f}% > "
                f"{targets['max_error_rate_percent']}% target"
            )
        
        p95_latency = perf_data['latency']['p95']
        if p95_latency > targets['max_latency_p95_ms']:
            violations.append(
                f"❌ P95 Latency: {p95_latency:.0f}ms > "
                f"{targets['max_latency_p95_ms']}ms target"
            )
        
        p50_latency = perf_data['latency']['p50']
        if p50_latency > targets['max_latency_p50_ms']:
            warnings.append(
                f"⚠️  P50 Latency: {p50_latency:.0f}ms > "
                f"{targets['max_latency_p50_ms']}ms target"
            )
        
        p99_latency = perf_data['latency']['p99']
        if p99_latency > targets['max_latency_p99_ms']:
            warnings.append(
                f"⚠️  P99 Latency: {p99_latency:.0f}ms > "
                f"{targets['max_latency_p99_ms']}ms target"
            )
        
        throughput_jobs = perf_data['throughput']['jobs_per_sec']
        if throughput_jobs < targets['min_throughput_jobs_per_sec']:
            violations.append(
                f"❌ Throughput: {throughput_jobs:.2f} jobs/sec < "
                f"{targets['min_throughput_jobs_per_sec']} jobs/sec target"
            )
        
        duration = exec_data['duration_seconds']
        if duration > targets['max_duration_seconds']:
            warnings.append(
                f"⚠️  Duration: {duration:.1f}s > "
                f"{targets['max_duration_seconds']}s target"
            )
        
        cpu_max = resources['cpu_percent_max']
        if cpu_max > targets['max_cpu_percent']:
            warnings.append(
                f"⚠️  CPU Max: {cpu_max:.1f}% > "
                f"{targets['max_cpu_percent']}% target"
            )
        
        memory_max = resources['memory_mb_max']
        if memory_max > targets['max_memory_mb']:
            warnings.append(
                f"⚠️  Memory Max: {memory_max:.0f}MB > "
                f"{targets['max_memory_mb']}MB target"
            )
        
        passed = len(violations) == 0
        messages = violations + warnings
        
        return passed, messages
    
    def compare_to_previous(
        self,
        current: Dict,
        previous: Dict
    ) -> Tuple[bool, List[str]]:
        """Compare current results to previous run for regressions"""
        
        if current['metadata']['workload_profile'] != previous['metadata']['workload_profile']:
            return True, ["⚠️  Cannot compare different workload profiles"]
        
        regressions = []
        improvements = []
        
        current_perf = current['performance']
        previous_perf = previous['performance']
        
        p95_current = current_perf['latency']['p95']
        p95_previous = previous_perf['latency']['p95']
        p95_change_pct = ((p95_current - p95_previous) / p95_previous * 100) if p95_previous > 0 else 0
        
        threshold = self.regression_thresholds['latency_p95_increase_percent']
        if p95_change_pct > threshold:
            regressions.append(
                f"❌ P95 Latency Regression: +{p95_change_pct:.1f}% "
                f"({p95_previous:.0f}ms → {p95_current:.0f}ms)"
            )
        elif p95_change_pct < -10:
            improvements.append(
                f"✅ P95 Latency Improved: {p95_change_pct:.1f}% "
                f"({p95_previous:.0f}ms → {p95_current:.0f}ms)"
            )
        
        throughput_current = current_perf['throughput']['jobs_per_sec']
        throughput_previous = previous_perf['throughput']['jobs_per_sec']
        throughput_change_pct = ((throughput_current - throughput_previous) / throughput_previous * 100) if throughput_previous > 0 else 0
        
        threshold = self.regression_thresholds['throughput_decrease_percent']
        if throughput_change_pct < -threshold:
            regressions.append(
                f"❌ Throughput Regression: {throughput_change_pct:.1f}% "
                f"({throughput_previous:.2f} → {throughput_current:.2f} jobs/sec)"
            )
        elif throughput_change_pct > 10:
            improvements.append(
                f"✅ Throughput Improved: +{throughput_change_pct:.1f}% "
                f"({throughput_previous:.2f} → {throughput_current:.2f} jobs/sec)"
            )
        
        error_current = current['execution']['error_rate_percent']
        error_previous = previous['execution']['error_rate_percent']
        error_change = error_current - error_previous
        
        threshold = self.regression_thresholds['error_rate_increase_percent']
        if error_change > threshold:
            regressions.append(
                f"❌ Error Rate Regression: +{error_change:.1f}% "
                f"({error_previous:.1f}% → {error_current:.1f}%)"
            )
        elif error_change < -1:
            improvements.append(
                f"✅ Error Rate Improved: {error_change:.1f}% "
                f"({error_previous:.1f}% → {error_current:.1f}%)"
            )
        
        passed = len(regressions) == 0
        messages = regressions + improvements
        
        return passed, messages
    
    def generate_report(
        self,
        current_results: Dict,
        baseline_comparison: Tuple[bool, List[str]],
        previous_results: Dict = None
    ) -> str:
        """Generate comparison report"""
        report = []
        report.append("\n" + "="*80)
        report.append("BASELINE COMPARISON REPORT")
        report.append("="*80)
        
        report.append(f"\n**Current Results:**")
        report.append(f"  - Workload: {current_results['metadata']['workload_profile']}")
        report.append(f"  - Timestamp: {current_results['metadata']['timestamp']}")
        
        baseline_passed, baseline_messages = baseline_comparison
        
        report.append(f"\n**Baseline Target Compliance:**")
        report.append(f"  Status: {'✅ PASSED' if baseline_passed else '❌ FAILED'}")
        
        if baseline_messages:
            report.append("\n  Details:")
            for msg in baseline_messages:
                report.append(f"    {msg}")
        
        if previous_results:
            regression_passed, regression_messages = self.compare_to_previous(
                current_results,
                previous_results
            )
            
            report.append(f"\n**Regression Analysis:**")
            report.append(f"  Previous Run: {previous_results['metadata']['timestamp']}")
            report.append(f"  Status: {'✅ NO REGRESSIONS' if regression_passed else '❌ REGRESSION DETECTED'}")
            
            if regression_messages:
                report.append("\n  Details:")
                for msg in regression_messages:
                    report.append(f"    {msg}")
        
        exec_data = current_results['execution']
        perf_data = current_results['performance']
        
        report.append(f"\n**Current Metrics:**")
        report.append(f"  - Success Rate: {exec_data['success_rate_percent']:.1f}%")
        report.append(f"  - Error Rate: {exec_data['error_rate_percent']:.1f}%")
        report.append(f"  - P50 Latency: {perf_data['latency']['p50']:.0f}ms")
        report.append(f"  - P95 Latency: {perf_data['latency']['p95']:.0f}ms")
        report.append(f"  - P99 Latency: {perf_data['latency']['p99']:.0f}ms")
        report.append(f"  - Throughput: {perf_data['throughput']['jobs_per_sec']:.2f} jobs/sec")
        
        report.append("\n" + "="*80 + "\n")
        
        return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(
        description="Compare benchmark results to baseline and detect regressions"
    )
    parser.add_argument(
        "--current",
        required=True,
        help="Path to current results JSON file"
    )
    parser.add_argument(
        "--baseline",
        default="benchmarks/baselines/baseline_config.yaml",
        help="Path to baseline configuration YAML file"
    )
    parser.add_argument(
        "--previous",
        help="Path to previous results JSON file for regression detection"
    )
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="Exit with error code if regressions detected"
    )
    parser.add_argument(
        "--output",
        help="Path to save comparison report"
    )
    
    args = parser.parse_args()
    
    comparator = BaselineComparator(args.baseline)
    
    current_results = comparator.load_results(args.current)
    
    baseline_passed, baseline_messages = comparator.compare_to_targets(current_results)
    
    previous_results = None
    regression_passed = True
    
    if args.previous and Path(args.previous).exists():
        previous_results = comparator.load_results(args.previous)
        regression_passed, _ = comparator.compare_to_previous(
            current_results,
            previous_results
        )
    
    report = comparator.generate_report(
        current_results,
        (baseline_passed, baseline_messages),
        previous_results
    )
    
    print(report)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        print(f"\nReport saved to: {args.output}")
    
    if args.fail_on_regression:
        if not baseline_passed:
            print("\n❌ Baseline targets not met. Exiting with error.")
            sys.exit(1)
        
        if not regression_passed:
            print("\n❌ Performance regression detected. Exiting with error.")
            sys.exit(1)
    
    if baseline_passed and regression_passed:
        print("\n✅ All checks passed!")
        sys.exit(0)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
