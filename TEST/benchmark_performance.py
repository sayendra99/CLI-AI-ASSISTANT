#!/usr/bin/env python3
"""
Performance Benchmark Suite for Rocket CLI
Measures startup time, memory usage, command execution, and caching effectiveness
"""

import time
import sys
import os
import psutil
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict
import statistics

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class BenchmarkResult:
    """Store benchmark metrics"""
    test_name: str
    execution_time_ms: float
    memory_usage_mb: float
    cpu_percent: float
    iterations: int
    avg_time_ms: float
    median_time_ms: float
    std_dev_ms: float


class PerformanceBenchmark:
    """Comprehensive performance testing for Rocket CLI"""
    
    def __init__(self, iterations: int = 10):
        self.iterations = iterations
        self.results: List[BenchmarkResult] = []
        self.process = psutil.Process()
        
    def measure_memory(self) -> float:
        """Get current memory usage in MB"""
        return self.process.memory_info().rss / 1024 / 1024
    
    def measure_cpu(self) -> float:
        """Get current CPU usage percentage"""
        return self.process.cpu_percent(interval=0.1)
    
    def benchmark_startup_time(self) -> BenchmarkResult:
        """Measure CLI cold start time"""
        print("🚀 Benchmarking startup time...")
        times = []
        
        for i in range(self.iterations):
            start_time = time.perf_counter()
            
            # Measure import time
            start_mem = self.measure_memory()
            
            # Simulate CLI startup
            proc = subprocess.run(
                [sys.executable, "rocket-cli.py", "--help"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            end_time = time.perf_counter()
            end_mem = self.measure_memory()
            
            execution_ms = (end_time - start_time) * 1000
            times.append(execution_ms)
            
            print(f"  Iteration {i+1}/{self.iterations}: {execution_ms:.2f}ms")
        
        result = BenchmarkResult(
            test_name="CLI Startup Time",
            execution_time_ms=sum(times),
            memory_usage_mb=end_mem - start_mem,
            cpu_percent=self.measure_cpu(),
            iterations=self.iterations,
            avg_time_ms=statistics.mean(times),
            median_time_ms=statistics.median(times),
            std_dev_ms=statistics.stdev(times) if len(times) > 1 else 0
        )
        
        self.results.append(result)
        return result
    
    def benchmark_module_imports(self) -> BenchmarkResult:
        """Measure module import overhead"""
        print("\n📦 Benchmarking module imports...")
        times = []
        
        modules = [
            'Rocket.CLI.Main',
            'Rocket.LLM.Client',
            'Rocket.AGENT.Executor',
            'Rocket.GIT.manager',
            'Rocket.TOOLS.registry',
        ]
        
        for i in range(self.iterations):
            start_time = time.perf_counter()
            start_mem = self.measure_memory()
            
            # Clear module cache to simulate cold import
            for module_name in list(sys.modules.keys()):
                if module_name.startswith('Rocket.'):
                    del sys.modules[module_name]
            
            # Import all modules
            for module_name in modules:
                try:
                    __import__(module_name)
                except Exception as e:
                    print(f"  Warning: Could not import {module_name}: {e}")
            
            end_time = time.perf_counter()
            end_mem = self.measure_memory()
            
            execution_ms = (end_time - start_time) * 1000
            times.append(execution_ms)
            
            print(f"  Iteration {i+1}/{self.iterations}: {execution_ms:.2f}ms")
        
        result = BenchmarkResult(
            test_name="Module Import Time",
            execution_time_ms=sum(times),
            memory_usage_mb=end_mem - start_mem,
            cpu_percent=self.measure_cpu(),
            iterations=self.iterations,
            avg_time_ms=statistics.mean(times),
            median_time_ms=statistics.median(times),
            std_dev_ms=statistics.stdev(times) if len(times) > 1 else 0
        )
        
        self.results.append(result)
        return result
    
    def benchmark_lru_cache_effectiveness(self) -> BenchmarkResult:
        """Test LRU cache performance improvement"""
        print("\n💾 Benchmarking LRU cache effectiveness...")
        from functools import lru_cache
        
        # Function without cache
        def fibonacci_no_cache(n: int) -> int:
            if n < 2:
                return n
            return fibonacci_no_cache(n-1) + fibonacci_no_cache(n-2)
        
        # Function with cache
        @lru_cache(maxsize=128)
        def fibonacci_cached(n: int) -> int:
            if n < 2:
                return n
            return fibonacci_cached(n-1) + fibonacci_cached(n-2)
        
        # Benchmark without cache
        start = time.perf_counter()
        for _ in range(self.iterations):
            fibonacci_no_cache(20)
        no_cache_time = (time.perf_counter() - start) * 1000
        
        # Benchmark with cache
        start = time.perf_counter()
        for _ in range(self.iterations):
            fibonacci_cached(20)
        cached_time = (time.perf_counter() - start) * 1000
        
        speedup = no_cache_time / cached_time
        print(f"  Without cache: {no_cache_time:.2f}ms")
        print(f"  With cache: {cached_time:.2f}ms")
        print(f"  Speedup: {speedup:.1f}x faster")
        
        result = BenchmarkResult(
            test_name="LRU Cache Effectiveness",
            execution_time_ms=cached_time,
            memory_usage_mb=self.measure_memory(),
            cpu_percent=self.measure_cpu(),
            iterations=self.iterations,
            avg_time_ms=cached_time / self.iterations,
            median_time_ms=cached_time / self.iterations,
            std_dev_ms=0
        )
        
        self.results.append(result)
        return result
    
    def benchmark_data_structure_performance(self) -> BenchmarkResult:
        """Compare list vs set lookup performance"""
        print("\n🔍 Benchmarking data structure performance...")
        
        # Create test data
        items_list = list(range(1000))
        items_set = set(range(1000))
        lookups = [100, 500, 999, 1001]
        
        # Benchmark list lookup
        start = time.perf_counter()
        for _ in range(self.iterations * 100):
            for item in lookups:
                _ = item in items_list
        list_time = (time.perf_counter() - start) * 1000
        
        # Benchmark set lookup
        start = time.perf_counter()
        for _ in range(self.iterations * 100):
            for item in lookups:
                _ = item in items_set
        set_time = (time.perf_counter() - start) * 1000
        
        speedup = list_time / set_time
        print(f"  List lookup: {list_time:.2f}ms")
        print(f"  Set lookup: {set_time:.2f}ms")
        print(f"  Speedup: {speedup:.1f}x faster")
        
        result = BenchmarkResult(
            test_name="Data Structure Performance (Set vs List)",
            execution_time_ms=set_time,
            memory_usage_mb=self.measure_memory(),
            cpu_percent=self.measure_cpu(),
            iterations=self.iterations * 100,
            avg_time_ms=set_time / (self.iterations * 100),
            median_time_ms=set_time / (self.iterations * 100),
            std_dev_ms=0
        )
        
        self.results.append(result)
        return result
    
    def benchmark_file_io(self) -> BenchmarkResult:
        """Test buffered vs unbuffered file I/O"""
        print("\n📄 Benchmarking file I/O performance...")
        
        # Create test file
        test_file = Path("temp_benchmark_file.txt")
        test_content = "x" * 1024 * 1024  # 1MB of data
        test_file.write_text(test_content)
        
        try:
            # Benchmark unbuffered read
            unbuffered_times = []
            for _ in range(self.iterations):
                start = time.perf_counter()
                with open(test_file, 'r') as f:
                    _ = f.read()
                unbuffered_times.append((time.perf_counter() - start) * 1000)
            
            # Benchmark buffered read
            buffered_times = []
            for _ in range(self.iterations):
                start = time.perf_counter()
                with open(test_file, 'r', buffering=8192) as f:
                    _ = f.read()
                buffered_times.append((time.perf_counter() - start) * 1000)
            
            unbuffered_avg = statistics.mean(unbuffered_times)
            buffered_avg = statistics.mean(buffered_times)
            speedup = unbuffered_avg / buffered_avg
            
            print(f"  Unbuffered: {unbuffered_avg:.2f}ms")
            print(f"  Buffered: {buffered_avg:.2f}ms")
            print(f"  Speedup: {speedup:.1f}x faster")
            
        finally:
            test_file.unlink()
        
        result = BenchmarkResult(
            test_name="File I/O Performance",
            execution_time_ms=buffered_avg,
            memory_usage_mb=self.measure_memory(),
            cpu_percent=self.measure_cpu(),
            iterations=self.iterations,
            avg_time_ms=buffered_avg,
            median_time_ms=statistics.median(buffered_times),
            std_dev_ms=statistics.stdev(buffered_times) if len(buffered_times) > 1 else 0
        )
        
        self.results.append(result)
        return result
    
    def generate_report(self) -> Dict:
        """Generate comprehensive performance report"""
        print("\n" + "="*60)
        print("📊 PERFORMANCE BENCHMARK REPORT")
        print("="*60 + "\n")
        
        for result in self.results:
            print(f"Test: {result.test_name}")
            print(f"  Average Time: {result.avg_time_ms:.2f}ms")
            print(f"  Median Time: {result.median_time_ms:.2f}ms")
            print(f"  Std Deviation: {result.std_dev_ms:.2f}ms")
            print(f"  Memory Usage: {result.memory_usage_mb:.2f}MB")
            print(f"  CPU Usage: {result.cpu_percent:.1f}%")
            print(f"  Iterations: {result.iterations}")
            print()
        
        # Save to JSON
        report = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'system_info': {
                'cpu_count': psutil.cpu_count(),
                'total_memory_mb': psutil.virtual_memory().total / 1024 / 1024,
                'python_version': sys.version
            },
            'results': [asdict(r) for r in self.results]
        }
        
        report_file = Path("benchmark_results.json")
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"✅ Report saved to: {report_file}")
        return report
    
    def run_all_benchmarks(self):
        """Execute all performance benchmarks"""
        print("🎯 Starting Performance Benchmark Suite\n")
        
        try:
            self.benchmark_startup_time()
        except Exception as e:
            print(f"  ⚠️ Startup benchmark failed: {e}")
        
        try:
            self.benchmark_module_imports()
        except Exception as e:
            print(f"  ⚠️ Import benchmark failed: {e}")
        
        self.benchmark_lru_cache_effectiveness()
        self.benchmark_data_structure_performance()
        self.benchmark_file_io()
        
        return self.generate_report()


if __name__ == '__main__':
    benchmark = PerformanceBenchmark(iterations=10)
    benchmark.run_all_benchmarks()
