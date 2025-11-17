"""
Phase 0 Baseline Benchmark Script
Measures current system performance to establish baseline metrics

Metrics Tracked:
1. Mapping lookup latency (YAML file reads)
2. Mapping application time (field transformation)
3. Total field mappings count
4. Estimated onboarding time per connector
5. Memory usage for mapping cache
"""
import time
import sys
import json
import psutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.aam.canonical.mapping_registry import MappingRegistry


class Phase0Benchmark:
    """Benchmark current AAM mapping system"""
    
    def __init__(self):
        self.results = {
            'timestamp': datetime.utcnow().isoformat(),
            'phase': 'Phase 0 - Baseline',
            'metrics': {}
        }
        self.registry: MappingRegistry | None = None
    
    def run_all_benchmarks(self):
        """Run all benchmark tests"""
        print("=" * 80)
        print("PHASE 0 BASELINE BENCHMARK")
        print("=" * 80)
        print()
        
        self.benchmark_registry_initialization()
        self.benchmark_mapping_lookup()
        self.benchmark_mapping_application()
        self.benchmark_memory_usage()
        self.calculate_estimated_costs()
        
        self.print_summary()
        self.save_results()
    
    def benchmark_registry_initialization(self):
        """Measure time to load all YAML mappings into memory"""
        print("📋 Benchmark 1: Registry Initialization")
        print("-" * 80)
        
        start = time.perf_counter()
        self.registry = MappingRegistry()
        duration_ms = (time.perf_counter() - start) * 1000
        
        # Count mappings
        mapping_list = self.registry.list_mappings()
        total_fields = sum([m['field_count'] for m in mapping_list])
        
        self.results['metrics']['registry_init'] = {
            'duration_ms': round(duration_ms, 2),
            'total_connectors': len(self.registry._mappings_cache),
            'total_entities': len(mapping_list),
            'total_field_mappings': total_fields
        }
        
        print(f"  ⏱️  Load Time: {duration_ms:.2f}ms")
        print(f"  📦 Connectors: {len(self.registry._mappings_cache)}")
        print(f"  📊 Entities: {len(mapping_list)}")
        print(f"  🔤 Field Mappings: {total_fields}")
        print()
    
    def benchmark_mapping_lookup(self):
        """Measure mapping lookup latency"""
        print("🔍 Benchmark 2: Mapping Lookup Latency")
        print("-" * 80)
        
        test_cases = [
            ('salesforce', 'opportunity'),
            ('hubspot', 'account'),
            ('mongodb', 'opportunity'),
            ('filesource', 'contact')
        ]
        
        lookup_times = []
        
        for system, entity in test_cases:
            start = time.perf_counter()
            assert self.registry is not None
            mapping = self.registry.get_mapping(system, entity)
            duration_us = (time.perf_counter() - start) * 1_000_000
            lookup_times.append(duration_us)
            
            field_count = len(mapping.get('fields', {})) if mapping else 0
            print(f"  {system:15s} / {entity:12s}: {duration_us:8.2f}µs ({field_count} fields)")
        
        avg_lookup = sum(lookup_times) / len(lookup_times)
        
        self.results['metrics']['mapping_lookup'] = {
            'avg_latency_us': round(avg_lookup, 2),
            'min_latency_us': round(min(lookup_times), 2),
            'max_latency_us': round(max(lookup_times), 2),
            'samples': len(test_cases)
        }
        
        print(f"\n  📊 Average Lookup: {avg_lookup:.2f}µs")
        print()
    
    def benchmark_mapping_application(self):
        """Measure time to apply mapping transformations"""
        print("🔄 Benchmark 3: Mapping Application (Field Transformation)")
        print("-" * 80)
        
        # Test with realistic data
        test_data = {
            'salesforce': {
                'entity': 'opportunity',
                'row': {
                    'Id': 'opp_12345',
                    'AccountId': 'acc_67890',
                    'Name': 'Enterprise Deal Q1',
                    'StageName': 'Qualification',
                    'Amount': 150000.00,
                    'CloseDate': '2025-03-31',
                    'OwnerId': 'user_999',
                    'Probability': 25.0,
                    'LastModifiedDate': '2025-01-15T10:30:00Z'
                }
            },
            'hubspot': {
                'entity': 'account',
                'row': {
                    'hs_object_id': '123456',
                    'company_name': 'Acme Corp',
                    'company_type': 'Enterprise',
                    'hs_industry': 'Technology',
                    'owner_email': 'sales@example.com',
                    'lifecycle_stage': 'customer',
                    'createdate': '2024-01-15T00:00:00Z',
                    'hs_lastmodifieddate': '2025-01-17T12:00:00Z'
                }
            }
        }
        
        application_times = []
        
        for system, config in test_data.items():
            start = time.perf_counter()
            assert self.registry is not None
            canonical_data, unknown_fields = self.registry.apply_mapping(
                system, config['entity'], config['row']
            )
            duration_us = (time.perf_counter() - start) * 1_000_000
            application_times.append(duration_us)
            
            mapped_count = len([k for k in canonical_data.keys() if k != 'extras'])
            unknown_count = len(unknown_fields)
            
            print(f"  {system:15s}: {duration_us:8.2f}µs")
            print(f"    → Mapped: {mapped_count} fields, Unknown: {unknown_count} fields")
        
        avg_application = sum(application_times) / len(application_times)
        
        self.results['metrics']['mapping_application'] = {
            'avg_latency_us': round(avg_application, 2),
            'samples': len(test_data)
        }
        
        print(f"\n  📊 Average Application: {avg_application:.2f}µs")
        print()
    
    def benchmark_memory_usage(self):
        """Measure memory footprint of mapping cache"""
        print("💾 Benchmark 4: Memory Usage")
        print("-" * 80)
        
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        
        assert self.registry is not None
        self.results['metrics']['memory'] = {
            'rss_mb': round(memory_mb, 2),
            'cache_size_kb': round(
                sys.getsizeof(self.registry._mappings_cache) / 1024, 2
            )
        }
        
        print(f"  Process RSS: {memory_mb:.2f} MB")
        print(f"  Cache Size: {self.results['metrics']['memory']['cache_size_kb']:.2f} KB")
        print()
    
    def calculate_estimated_costs(self):
        """Calculate estimated onboarding costs and time"""
        print("💰 Benchmark 5: Estimated Costs & Time")
        print("-" * 80)
        
        # Current assumptions based on YAML approach
        # (These will be validated against actual AAM connector runs)
        
        avg_fields_per_connector = 191 / 8  # ~24 fields
        
        # File-based approach: no LLM needed, mappings are manual
        # Time is dominated by manual mapping creation
        manual_time_per_field_minutes = 2  # Conservative estimate
        
        # Estimated time to onboard 1 connector (manual YAML creation)
        time_per_connector_hours = (avg_fields_per_connector * manual_time_per_field_minutes) / 60
        
        # For 10 connectors
        time_for_10_connectors = time_per_connector_hours * 10
        
        # No LLM costs in current YAML approach
        llm_cost_per_connector = 0.00
        
        self.results['metrics']['estimated_costs'] = {
            'avg_fields_per_connector': round(avg_fields_per_connector, 1),
            'manual_time_per_field_minutes': manual_time_per_field_minutes,
            'time_per_connector_hours': round(time_per_connector_hours, 2),
            'time_for_10_connectors_hours': round(time_for_10_connectors, 2),
            'llm_cost_per_connector_usd': llm_cost_per_connector,
            'llm_cost_for_10_connectors_usd': llm_cost_per_connector * 10
        }
        
        print(f"  Fields/Connector (avg): {avg_fields_per_connector:.1f}")
        print(f"  Manual Time/Field: {manual_time_per_field_minutes} minutes")
        print(f"  Time/Connector: {time_per_connector_hours:.2f} hours")
        print(f"  Time for 10 Connectors: {time_for_10_connectors:.2f} hours (~{time_for_10_connectors/8:.1f} days)")
        print(f"  LLM Cost/Connector: ${llm_cost_per_connector:.2f} (manual YAML, no LLM)")
        print()
    
    def print_summary(self):
        """Print benchmark summary"""
        print("=" * 80)
        print("BASELINE SUMMARY")
        print("=" * 80)
        print()
        print("📊 Current State:")
        print(f"  • {self.results['metrics']['registry_init']['total_connectors']} connectors")
        print(f"  • {self.results['metrics']['registry_init']['total_field_mappings']} field mappings")
        print(f"  • {self.results['metrics']['registry_init']['duration_ms']:.2f}ms initialization time")
        print()
        print("⚡ Performance:")
        print(f"  • Mapping lookup: {self.results['metrics']['mapping_lookup']['avg_latency_us']:.2f}µs avg")
        print(f"  • Mapping application: {self.results['metrics']['mapping_application']['avg_latency_us']:.2f}µs avg")
        print()
        print("📈 Scaling Estimates:")
        est = self.results['metrics']['estimated_costs']
        print(f"  • Time to onboard 1 connector: ~{est['time_per_connector_hours']:.1f} hours (manual YAML)")
        print(f"  • Time to onboard 10 connectors: ~{est['time_for_10_connectors_hours']:.1f} hours")
        print(f"  • LLM cost: $0.00 (manual approach, no AI)")
        print()
        print("🎯 Phase 0 Goals:")
        print("  • Reduce onboarding time by 10x (AI-assisted mapping)")
        print("  • Enable RAG for 85%+ mapping proposals")
        print("  • Sub-100ms mapping lookup latency (database)")
        print("  • Zero manual YAML editing")
        print()
    
    def save_results(self):
        """Save benchmark results to JSON"""
        output_file = Path('scripts/phase0_baseline_results.json')
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"💾 Results saved to: {output_file}")
        print()


if __name__ == '__main__':
    benchmark = Phase0Benchmark()
    benchmark.run_all_benchmarks()
