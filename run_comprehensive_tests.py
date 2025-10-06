#!/usr/bin/env python3
"""
Comprehensive test runner for the Bank Policy Comparator.
Runs all test suites and generates a detailed report.
"""

import sys
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def run_test_suite():
    """Run the comprehensive test suite."""
    
    print("🏦 Bank Policy Comparator - Comprehensive Test Suite")
    print("=" * 60)
    print(f"📅 Test Run Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🐍 Python Version: {sys.version}")
    print(f"📁 Working Directory: {os.getcwd()}")
    print("=" * 60)
    
    # Test suites to run
    test_suites = [
        {
            'name': 'Document Processing Pipeline',
            'file': 'tests/test_document_processing_pipeline.py',
            'description': 'Tests document upload, storage, and processing workflow'
        },
        {
            'name': 'Fact Extraction Accuracy',
            'file': 'tests/test_fact_extraction_accuracy.py',
            'description': 'Tests accuracy and reliability of fact extraction'
        },
        {
            'name': 'Comparison Logic',
            'file': 'tests/test_comparison_logic.py',
            'description': 'Tests multi-document comparison algorithms'
        },
        {
            'name': 'Normalization Functions',
            'file': 'tests/test_normalization_functions.py',
            'description': 'Tests fact normalization and standardization'
        },
        {
            'name': 'Export Functionality',
            'file': 'tests/test_export_functionality.py',
            'description': 'Tests CSV and JSON export generation'
        }
    ]
    
    results = []
    total_start_time = time.time()
    
    for i, suite in enumerate(test_suites, 1):
        print(f"\n📋 Running Test Suite {i}/{len(test_suites)}: {suite['name']}")
        print(f"📄 Description: {suite['description']}")
        print(f"📂 File: {suite['file']}")
        print("-" * 40)
        
        # Check if test file exists
        if not os.path.exists(suite['file']):
            print(f"❌ Test file not found: {suite['file']}")
            results.append({
                'name': suite['name'],
                'status': 'MISSING',
                'duration': 0,
                'details': f"Test file {suite['file']} not found"
            })
            continue
        
        # Run the test suite
        start_time = time.time()
        try:
            # Run pytest with verbose output
            result = subprocess.run([
                sys.executable, '-m', 'pytest', 
                suite['file'], 
                '-v',  # verbose
                '--tb=short',  # short traceback format
                '--no-header',  # no pytest header
                '--quiet'  # reduce output
            ], capture_output=True, text=True, timeout=300)  # 5 minute timeout
            
            duration = time.time() - start_time
            
            if result.returncode == 0:
                print(f"✅ PASSED - {duration:.2f}s")
                status = 'PASSED'
                details = f"All tests passed in {duration:.2f}s"
            else:
                print(f"❌ FAILED - {duration:.2f}s")
                status = 'FAILED'
                details = f"Tests failed after {duration:.2f}s"
                if result.stdout:
                    print("📤 STDOUT:")
                    print(result.stdout[:500] + "..." if len(result.stdout) > 500 else result.stdout)
                if result.stderr:
                    print("📤 STDERR:")
                    print(result.stderr[:500] + "..." if len(result.stderr) > 500 else result.stderr)
            
            results.append({
                'name': suite['name'],
                'status': status,
                'duration': duration,
                'details': details,
                'stdout': result.stdout,
                'stderr': result.stderr
            })
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            print(f"⏰ TIMEOUT - {duration:.2f}s")
            results.append({
                'name': suite['name'],
                'status': 'TIMEOUT',
                'duration': duration,
                'details': f"Test suite timed out after {duration:.2f}s"
            })
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"💥 ERROR - {str(e)}")
            results.append({
                'name': suite['name'],
                'status': 'ERROR',
                'duration': duration,
                'details': f"Error running tests: {str(e)}"
            })
    
    total_duration = time.time() - total_start_time
    
    # Generate summary report
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY REPORT")
    print("=" * 60)
    
    passed_count = len([r for r in results if r['status'] == 'PASSED'])
    failed_count = len([r for r in results if r['status'] == 'FAILED'])
    error_count = len([r for r in results if r['status'] in ['ERROR', 'TIMEOUT', 'MISSING']])
    total_count = len(results)
    
    print(f"📈 Total Test Suites: {total_count}")
    print(f"✅ Passed: {passed_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"💥 Errors: {error_count}")
    print(f"⏱️  Total Duration: {total_duration:.2f}s")
    print(f"📊 Success Rate: {(passed_count/total_count)*100:.1f}%")
    
    print("\n📋 Detailed Results:")
    for result in results:
        status_icon = {
            'PASSED': '✅',
            'FAILED': '❌',
            'ERROR': '💥',
            'TIMEOUT': '⏰',
            'MISSING': '❓'
        }.get(result['status'], '❓')
        
        print(f"  {status_icon} {result['name']}: {result['status']} ({result['duration']:.2f}s)")
        if result['status'] != 'PASSED':
            print(f"     └─ {result['details']}")
    
    # Generate recommendations
    print("\n🎯 RECOMMENDATIONS:")
    if failed_count > 0:
        print("  • Review failed test cases and fix underlying issues")
        print("  • Check test data and mock configurations")
        print("  • Verify all dependencies are properly installed")
    
    if error_count > 0:
        print("  • Check for missing test files or import errors")
        print("  • Verify Python path and module imports")
        print("  • Review test environment setup")
    
    if passed_count == total_count:
        print("  🎉 All tests passed! Consider adding more edge cases")
        print("  • Add performance benchmarks")
        print("  • Increase test coverage for error conditions")
        print("  • Add integration tests with real documents")
    
    # Save detailed report
    save_test_report(results, total_duration)
    
    return passed_count == total_count

def save_test_report(results, total_duration):
    """Save detailed test report to file."""
    
    report_dir = "test_reports"
    os.makedirs(report_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"{report_dir}/test_report_{timestamp}.txt"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("Bank Policy Comparator - Test Report\n")
        f.write("=" * 50 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Duration: {total_duration:.2f}s\n")
        f.write(f"Python Version: {sys.version}\n")
        f.write("\n")
        
        for result in results:
            f.write(f"Test Suite: {result['name']}\n")
            f.write(f"Status: {result['status']}\n")
            f.write(f"Duration: {result['duration']:.2f}s\n")
            f.write(f"Details: {result['details']}\n")
            
            if result.get('stdout'):
                f.write("STDOUT:\n")
                f.write(result['stdout'])
                f.write("\n")
            
            if result.get('stderr'):
                f.write("STDERR:\n")
                f.write(result['stderr'])
                f.write("\n")
            
            f.write("-" * 30 + "\n")
    
    print(f"\n📄 Detailed report saved: {report_file}")

def check_dependencies():
    """Check if required dependencies are installed."""
    
    print("🔍 Checking Dependencies...")
    
    required_packages = [
        'pytest',
        'fastapi',
        'streamlit',
        'pandas',
        'pydantic'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} - MISSING")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("Install with: pip install " + " ".join(missing_packages))
        return False
    
    print("✅ All dependencies available")
    return True

def main():
    """Main function."""
    
    # Check dependencies first
    if not check_dependencies():
        print("\n❌ Cannot run tests due to missing dependencies")
        return False
    
    # Run the test suite
    success = run_test_suite()
    
    if success:
        print("\n🎉 All tests completed successfully!")
        return True
    else:
        print("\n❌ Some tests failed. Please review the results above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)