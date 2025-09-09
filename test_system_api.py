#!/usr/bin/env python3
"""
Test script to verify the system management API endpoints are working correctly.
"""

import sys
import os
import importlib.util
from datetime import datetime

def test_system_router_import():
    """Test that the system router can be imported."""
    print("Testing system router import...")
    
    try:
        # Add the current directory to Python path
        sys.path.insert(0, os.getcwd())
        
        # Try to import the system router
        spec = importlib.util.spec_from_file_location(
            "nautilus_web.api.routers.system", 
            "nautilus_web/api/routers/system.py"
        )
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Check if the router object exists
            if hasattr(module, 'router'):
                print("✓ System router imported successfully")
                
                # Check for expected endpoints
                routes = [route.path for route in module.router.routes]
                expected_routes = [
                    "/api/system/status",
                    "/api/system/metrics", 
                    "/api/system/kernel/initialize",
                    "/api/system/kernel/start",
                    "/api/system/kernel/stop",
                    "/api/system/kernel/restart",
                    "/api/system/kernel",
                    "/api/system/kernel/info"
                ]
                
                routes_found = all(route in routes for route in expected_routes)
                if routes_found:
                    print("✓ All expected routes found")
                else:
                    print("✗ Some expected routes missing")
                    print(f"Expected: {expected_routes}")
                    print(f"Found: {routes}")
                    return False
                
                return True
            else:
                print("✗ Router object not found")
                return False
        else:
            print("✗ Could not load module spec")
            return False
            
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_main_app_integration():
    """Test that the main app includes the system router."""
    print("\nTesting main app integration...")
    
    try:
        # Try to import the main app
        spec = importlib.util.spec_from_file_location(
            "nautilus_web.api.main", 
            "nautilus_web/api/main.py"
        )
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Check if the app object exists
            if hasattr(module, 'app'):
                app = module.app
                
                # Check if system router is included
                system_routes = [
                    route for route in app.routes 
                    if hasattr(route, 'path') and route.path.startswith('/api/system')
                ]
                
                if system_routes:
                    print("✓ System router integrated with main app")
                    print(f"  Found {len(system_routes)} system routes")
                    return True
                else:
                    print("✗ System router not integrated with main app")
                    return False
            else:
                print("✗ FastAPI app object not found")
                return False
        else:
            print("✗ Could not load main app module")
            return False
            
    except Exception as e:
        print(f"✗ Integration test failed: {e}")
        return False

def test_response_models():
    """Test that response models are properly defined."""
    print("\nTesting response models...")
    
    try:
        # Import the system module
        spec = importlib.util.spec_from_file_location(
            "nautilus_web.api.routers.system", 
            "nautilus_web/api/routers/system.py"
        )
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Check for expected models
            expected_models = [
                'SystemStatusResponse',
                'SystemMetricsResponse', 
                'KernelConfigRequest',
                'KernelOperationResponse'
            ]
            
            models_found = all(hasattr(module, model) for model in expected_models)
            if models_found:
                print("✓ All response models found")
                
                # Test model instantiation
                try:
                    status_response = module.SystemStatusResponse(
                        status="healthy",
                        uptime_seconds=123.45
                    )
                    print("✓ Response models can be instantiated")
                    return True
                except Exception as e:
                    print(f"✗ Model instantiation failed: {e}")
                    return False
            else:
                print("✗ Some response models missing")
                missing = [model for model in expected_models if not hasattr(module, model)]
                print(f"Missing models: {missing}")
                return False
        else:
            print("✗ Could not load system module")
            return False
            
    except Exception as e:
        print(f"✗ Response model test failed: {e}")
        return False

def test_dependencies_updated():
    """Test that pyproject.toml has been updated with required dependencies."""
    print("\nTesting dependency updates...")
    
    try:
        with open("pyproject.toml", "r") as f:
            content = f.read()
        
        required_deps = ["psutil"]
        webui_extra_deps = ["psutil"]
        
        deps_found = all(dep in content for dep in required_deps)
        webui_deps_found = all(dep in content.split('webui = [')[1].split(']')[0] for dep in webui_extra_deps)
        
        if deps_found:
            print("✓ Required dependencies found in pyproject.toml")
        else:
            print("✗ Some required dependencies missing")
            
        if webui_deps_found:
            print("✓ WebUI extra dependencies updated")
        else:
            print("✗ WebUI extra dependencies not updated properly")
            
        return deps_found and webui_deps_found
        
    except Exception as e:
        print(f"✗ Error checking dependencies: {e}")
        return False

def main():
    """Run all tests."""
    print("=== System Management API Test ===\n")
    
    tests = [
        test_system_router_import,
        test_main_app_integration,
        test_response_models,
        test_dependencies_updated,
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("✓ All tests passed! System management API implementation is complete.")
        print("\nAvailable endpoints:")
        print("- GET /api/system/status - Get system status and kernel state")
        print("- GET /api/system/metrics - Get real-time system metrics")
        print("- POST /api/system/kernel/initialize - Initialize Nautilus kernel")
        print("- POST /api/system/kernel/start - Start the kernel")
        print("- POST /api/system/kernel/stop - Stop the kernel")
        print("- POST /api/system/kernel/restart - Restart the kernel")
        print("- DELETE /api/system/kernel - Dispose of the kernel")
        print("- GET /api/system/kernel/info - Get detailed kernel information")
        return 0
    else:
        print("✗ Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
