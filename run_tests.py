import pytest
import sys
import os

def main():
    print("🚀 Running all tests...")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    test_dir = os.path.join(base_dir, "tests")
    
    sys.path.insert(0, base_dir)
    
    # Run pytest
    # -v: verbose
    # -s: show stdout/stderr
    # --asyncio-mode=auto: handle async tests automatically
    args = [
        "-v", 
        "--asyncio-mode=auto",
        test_dir
    ]
    
    retcode = pytest.main(args)
    
    if retcode == 0:
        print("\n✅ All tests passed!")
    else:
        print(f"\n❌ Tests failed with exit code: {retcode}")
    
    sys.exit(retcode)

if __name__ == "__main__":
    main()
