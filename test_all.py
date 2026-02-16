
import subprocess
import os
import sys

def run_test(name, command):
    print(f"Running {name}...")
    try:
        result = subprocess.run(command, capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            print(f"✅ {name} passed.")
            return True, result.stdout
        else:
            print(f"❌ {name} failed.")
            return False, result.stderr + "\n" + result.stdout
    except Exception as e:
        print(f"❌ {name} error: {e}")
        return False, str(e)

def main():
    tests = [
        ("System Unit Tests", "python -m unittest discover tests"),
        ("Environment Setup", "python test_setup.py"),
        ("Signal Detection", "python test_detector.py"),
    ]
    
    all_passed = True
    reports = []
    
    for name, cmd in tests:
        passed, output = run_test(name, cmd)
        if not passed:
            all_passed = False
        reports.append((name, passed, output))
    
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    for name, passed, output in reports:
        status = "PASSED" if passed else "FAILED"
        print(f"{name}: {status}")
    
    if all_passed:
        print("\nAll system tests passed! 🚀")
        sys.exit(0)
    else:
        print("\nSome tests failed. Check the details above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
