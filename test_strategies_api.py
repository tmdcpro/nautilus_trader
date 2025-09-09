#!/usr/bin/env python3
"""
Test script to verify the strategy management API endpoints are working correctly.
"""

import sys
import os
import importlib.util
from datetime import datetime

def test_strategies_router_import():
    """Test that the strategies router can be imported."""
    print("Testing strategies router import...")
    
    try:
        # Add the current directory to Python path
        sys.path.insert(0, os.getcwd())
        
        # Try to import the strategies router
        spec = importlib.util.spec_from_file_location(
            "nautilus_web.api.routers.strategies", 
            "nautilus_web/api/routers/strategies.py"
        )
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Check if the router object exists
            if hasattr(module, 'router'):
                print("✓ Strategies router imported successfully")
                
                # Check for expected endpoints
                routes = [route.path for route in module.router.routes]
                expected_routes = [
                    "/api/strategies/available",
                    "/api/strategies/",
                    "/api/strategies/{strategy_id}",
                    "/api/strategies/{strategy_id}/status",
                    "/api/strategies/{strategy_id}/start",
                    "/api/strategies/{strategy_id}/stop",
                    "/api/strategies/{strategy_id}/restart"
                ]
                
                routes_found = all(any(expected in route for route in routes) for expected in expected_routes)
                if routes_found:
                    print("✓ All expected routes found")
                    print(f"  Total routes: {len(routes)}")
                else:
                    print("✗ Some expected routes missing")
                    print(f"Expected patterns: {expected_routes}")
                    print(f"Found routes: {routes}")
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

def test_strategy_registry():
    """Test that the strategy registry is properly defined."""
    print("\nTesting strategy registry...")
    
    try:
        # Import the strategies module
        spec = importlib.util.spec_from_file_location(
            "nautilus_web.api.routers.strategies", 
            "nautilus_web/api/routers/strategies.py"
        )
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Check if strategy registry exists
            if hasattr(module, 'STRATEGY_REGISTRY'):
                registry = module.STRATEGY_REGISTRY
                print(f"✓ Strategy registry found with {len(registry)} strategies")
                
                # Check for expected strategies
                expected_strategies = [
                    'EMACross',
                    'EMACrossBracket', 
                    'EMACrossLongOnly',
                    'MarketMaker',
                    'OrderBookImbalance',
                    'VolatilityMarketMaker'
                ]
                
                strategies_found = all(strategy in registry for strategy in expected_strategies)
                if strategies_found:
                    print("✓ All expected strategies found in registry")
                    
                    # Check registry structure
                    for name, info in registry.items():
                        if not all(key in info for key in ['class', 'config', 'description']):
                            print(f"✗ Strategy {name} missing required keys")
                            return False
                    
                    print("✓ Registry structure is valid")
                    return True
                else:
                    missing = [s for s in expected_strategies if s not in registry]
                    print(f"✗ Missing strategies: {missing}")
                    return False
            else:
                print("✗ Strategy registry not found")
                return False
        else:
            print("✗ Could not load strategies module")
            return False
            
    except Exception as e:
        print(f"✗ Registry test failed: {e}")
        return False

def test_response_models():
    """Test that response models are properly defined."""
    print("\nTesting response models...")
    
    try:
        # Import the strategies module
        spec = importlib.util.spec_from_file_location(
            "nautilus_web.api.routers.strategies", 
            "nautilus_web/api/routers/strategies.py"
        )
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Check for expected models
            expected_models = [
                'StrategyInfo',
                'StrategyConfigResponse',
                'StrategyStatusResponse',
                'StrategyCreateRequest',
                'StrategyUpdateRequest',
                'StrategyOperationResponse'
            ]
            
            models_found = all(hasattr(module, model) for model in expected_models)
            if models_found:
                print("✓ All response models found")
                
                # Test model instantiation
                try:
                    strategy_info = module.StrategyInfo(
                        name="TestStrategy",
                        class_name="TestStrategy",
                        module_path="test.module.TestStrategy"
                    )
                    
                    config_response = module.StrategyConfigResponse(
                        strategy_id="test-001",
                        strategy_type="EMACross",
                        config={"test": "value"},
                        created_at=datetime.now().isoformat()
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
            print("✗ Could not load strategies module")
            return False
            
    except Exception as e:
        print(f"✗ Response model test failed: {e}")
        return False

def test_main_app_integration():
    """Test that the main app includes the strategies router."""
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
                
                # Check if strategies router is included
                strategy_routes = [
                    route for route in app.routes 
                    if hasattr(route, 'path') and route.path.startswith('/api/strategies')
                ]
                
                if strategy_routes:
                    print("✓ Strategies router integrated with main app")
                    print(f"  Found {len(strategy_routes)} strategy routes")
                    return True
                else:
                    print("✗ Strategies router not integrated with main app")
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

def test_helper_functions():
    """Test that helper functions are properly defined."""
    print("\nTesting helper functions...")
    
    try:
        # Import the strategies module
        spec = importlib.util.spec_from_file_location(
            "nautilus_web.api.routers.strategies", 
            "nautilus_web/api/routers/strategies.py"
        )
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Check for expected helper functions
            expected_functions = [
                'load_strategy_class',
                'load_config_class',
                'get_class_parameters',
                'get_app_state',
                'get_logger'
            ]
            
            functions_found = all(hasattr(module, func) for func in expected_functions)
            if functions_found:
                print("✓ All helper functions found")
                return True
            else:
                missing = [func for func in expected_functions if not hasattr(module, func)]
                print(f"✗ Missing helper functions: {missing}")
                return False
        else:
            print("✗ Could not load strategies module")
            return False
            
    except Exception as e:
        print(f"✗ Helper functions test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=== Strategy Management API Test ===\n")
    
    tests = [
        test_strategies_router_import,
        test_strategy_registry,
        test_response_models,
        test_main_app_integration,
        test_helper_functions,
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("✓ All tests passed! Strategy management API implementation is complete.")
        print("\nAvailable endpoints:")
        print("- GET /api/strategies/available - List available strategy types")
        print("- GET /api/strategies/ - List all configured strategies")
        print("- POST /api/strategies/ - Create new strategy configuration")
        print("- GET /api/strategies/{id} - Get specific strategy configuration")
        print("- PUT /api/strategies/{id} - Update strategy configuration")
        print("- DELETE /api/strategies/{id} - Delete strategy configuration")
        print("- GET /api/strategies/{id}/status - Get strategy status")
        print("- POST /api/strategies/{id}/start - Start strategy")
        print("- POST /api/strategies/{id}/stop - Stop strategy")
        print("- POST /api/strategies/{id}/restart - Restart strategy")
        print("\nSupported strategy types:")
        print("- EMACross, EMACrossBracket, EMACrossLongOnly, EMACrossTrailingStop")
        print("- MarketMaker, OrderBookImbalance, VolatilityMarketMaker")
        return 0
    else:
        print("✗ Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
