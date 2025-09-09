#!/usr/bin/env python3
"""
Simple test script to verify the FastAPI web UI setup is working correctly.
"""

import sys
import os
import importlib.util

def test_directory_structure():
    """Test that the required directory structure exists."""
    print("Testing directory structure...")
    
    required_dirs = [
        "nautilus_web",
        "nautilus_web/api",
        "nautilus_web/api/routers",
        "nautilus_web/frontend",
        "nautilus_web/static",
        "nautilus_web/database",
    ]
    
    for dir_path in required_dirs:
        if os.path.exists(dir_path):
            print(f"✓ {dir_path} exists")
        else:
            print(f"✗ {dir_path} missing")
            return False
    
    return True

def test_required_files():
    """Test that the required files exist."""
    print("\nTesting required files...")
    
    required_files = [
        "nautilus_web/__init__.py",
        "nautilus_web/api/__init__.py",
        "nautilus_web/api/main.py",
        "nautilus_web/api/models.py",
        "nautilus_web/api/routers/__init__.py",
    ]
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path} exists")
        else:
            print(f"✗ {file_path} missing")
            return False
    
    return True

def test_fastapi_import():
    """Test that the FastAPI application can be imported."""
    print("\nTesting FastAPI application import...")
    
    try:
        # Add the current directory to Python path
        sys.path.insert(0, os.getcwd())
        
        # Try to import the main module
        spec = importlib.util.spec_from_file_location(
            "nautilus_web.api.main", 
            "nautilus_web/api/main.py"
        )
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Check if the app object exists
            if hasattr(module, 'app'):
                print("✓ FastAPI app object found")
                return True
            else:
                print("✗ FastAPI app object not found")
                return False
        else:
            print("✗ Could not load module spec")
            return False
            
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_pyproject_dependencies():
    """Test that pyproject.toml has been updated with web UI dependencies."""
    print("\nTesting pyproject.toml dependencies...")
    
    try:
        with open("pyproject.toml", "r") as f:
            content = f.read()
        
        required_deps = ["fastapi", "uvicorn", "websockets", "jinja2"]
        webui_extra_found = "webui" in content
        
        deps_found = all(dep in content for dep in required_deps)
        
        if deps_found:
            print("✓ Required dependencies found in pyproject.toml")
        else:
            print("✗ Some required dependencies missing")
            
        if webui_extra_found:
            print("✓ webui extra found in pyproject.toml")
        else:
            print("✗ webui extra missing from pyproject.toml")
            
        return deps_found and webui_extra_found
        
    except Exception as e:
        print(f"✗ Error reading pyproject.toml: {e}")
        return False

def main():
    """Run all tests."""
    print("=== Nautilus Trader Web UI Setup Test ===\n")
    
    tests = [
        test_directory_structure,
        test_required_files,
        test_pyproject_dependencies,
        test_fastapi_import,
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("✓ All tests passed! FastAPI web UI backend setup is complete.")
        return 0
    else:
        print("✗ Some tests failed. Please check the setup.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
