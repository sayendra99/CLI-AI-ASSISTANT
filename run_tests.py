#!/usr/bin/env python
"""
Rocket LLM Module - Test Runner Script

Comprehensive test execution script with multiple options:
- Run all tests
- Run specific test categories
- Generate coverage reports
- Run with detailed output

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --unit             # Run only unit tests
    python run_tests.py --coverage         # Run with coverage report
    python run_tests.py --async            # Run async tests
    python run_tests.py --verbose          # Verbose output
"""

import sys
import subprocess
import argparse
from pathlib import Path


class TestRunner:
    """Manage test execution and reporting."""
    
    def __init__(self):
        self.test_dir = Path(__file__).parent / "TEST"
        self.project_root = Path(__file__).parent
    
    def run_all_tests(self, verbose=False):
        """Run all tests."""
        print("\n" + "="*70)
        print("🚀 Running ALL Rocket LLM Module Tests")
        print("="*70 + "\n")
        
        cmd = [
            "pytest",
            str(self.test_dir),
            "-v" if verbose else "",
            "--tb=short",
        ]
        cmd = [c for c in cmd if c]  # Remove empty strings
        
        return subprocess.run(cmd).returncode
    
    def run_unit_tests(self, verbose=False):
        """Run only unit tests."""
        print("\n" + "="*70)
        print("🧪 Running Unit Tests")
        print("="*70 + "\n")
        
        cmd = [
            "pytest",
            str(self.test_dir / "test_llm.py"),
            "-v" if verbose else "",
            "-m", "not asyncio",
            "--tb=short",
        ]
        cmd = [c for c in cmd if c]
        
        return subprocess.run(cmd).returncode
    
    def run_async_tests(self, verbose=False):
        """Run only async tests."""
        print("\n" + "="*70)
        print("⚡ Running Async Tests")
        print("="*70 + "\n")
        
        cmd = [
            "pytest",
            str(self.test_dir / "test_llm_async.py"),
            "-v" if verbose else "",
            "-m", "asyncio",
            "--tb=short",
        ]
        cmd = [c for c in cmd if c]
        
        return subprocess.run(cmd).returncode
    
    def run_with_coverage(self):
        """Run tests with coverage report."""
        print("\n" + "="*70)
        print("📊 Running Tests with Coverage Report")
        print("="*70 + "\n")
        
        cmd = [
            "pytest",
            str(self.test_dir),
            "--cov=Rocket.LLM",
            "--cov-report=html",
            "--cov-report=term",
            "-v",
        ]
        
        result = subprocess.run(cmd)
        
        print("\n" + "="*70)
        print("✅ Coverage report generated in htmlcov/index.html")
        print("="*70 + "\n")
        
        return result.returncode
    
    def run_specific_test(self, test_name, verbose=False):
        """Run a specific test."""
        print(f"\n{'='*70}")
        print(f"🔍 Running Specific Test: {test_name}")
        print("="*70 + "\n")
        
        cmd = [
            "pytest",
            f"{self.test_dir}::{test_name}",
            "-v" if verbose else "",
            "--tb=short",
        ]
        cmd = [c for c in cmd if c]
        
        return subprocess.run(cmd).returncode
    
    def list_tests(self):
        """List all available tests."""
        print("\n" + "="*70)
        print("📋 Available Tests")
        print("="*70 + "\n")
        
        cmd = ["pytest", str(self.test_dir), "--collect-only", "-q"]
        
        return subprocess.run(cmd).returncode


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Rocket LLM Module Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                    # Run all tests
  python run_tests.py --unit             # Unit tests only
  python run_tests.py --async            # Async tests only
  python run_tests.py --coverage         # With coverage report
  python run_tests.py --verbose          # Verbose output
  python run_tests.py --list             # List all tests
        """
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all tests (default)"
    )
    parser.add_argument(
        "--unit",
        action="store_true",
        help="Run only unit tests"
    )
    parser.add_argument(
        "--async",
        action="store_true",
        help="Run only async tests"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run tests with coverage report"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available tests"
    )
    parser.add_argument(
        "--test",
        type=str,
        help="Run a specific test by name"
    )
    
    args = parser.parse_args()
    runner = TestRunner()
    
    try:
        if args.list:
            exit_code = runner.list_tests()
        elif args.coverage:
            exit_code = runner.run_with_coverage()
        elif args.unit:
            exit_code = runner.run_unit_tests(args.verbose)
        elif args.async:
            exit_code = runner.run_async_tests(args.verbose)
        elif args.test:
            exit_code = runner.run_specific_test(args.test, args.verbose)
        else:
            # Default: run all tests
            exit_code = runner.run_all_tests(args.verbose)
        
        if exit_code == 0:
            print("\n" + "="*70)
            print("✅ All tests passed! 🎉")
            print("="*70 + "\n")
        else:
            print("\n" + "="*70)
            print("❌ Some tests failed. Please review the output above.")
            print("="*70 + "\n")
        
        sys.exit(exit_code)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Test run interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
