import os
import sys
import subprocess

TESTS = [
    "test_schemas.py",
    "test_scoring.py",
]

def run_all():
    print("=" * 65)
    print("           GHOSTNET AI -- BACKEND TEST SUITE RUNNER                  ")
    print("=" * 65)

    cur_dir = os.path.dirname(os.path.abspath(__file__))
    all_passed = True

    for test_file in TESTS:
        test_path = os.path.join(cur_dir, test_file)
        print(f"Running test: {test_file} ...")
        res = subprocess.run([sys.executable, test_path], capture_output=True, text=True)
        if res.returncode == 0:
            print(f"  [PASS] {test_file}")
            if res.stdout.strip():
                for line in res.stdout.strip().split("\n"):
                    print(f"    {line}")
        else:
            print(f"  [FAIL] {test_file}")
            print(res.stderr)
            all_passed = False

    print("=" * 65)
    if all_passed:
        print("ALL BACKEND TESTS PASSED SUCCESSFULLY! (100% GREEN)")
    else:
        print("SOME TESTS FAILED.")
    print("=" * 65)

if __name__ == "__main__":
    run_all()
