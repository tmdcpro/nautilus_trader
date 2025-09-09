# -------------------------------------------------------------------------------------------------
#  Copyright (C) 2015-2025 Nautech Systems Pty Ltd. All rights reserved.
#  https://nautechsystems.io
#
#  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
#  You may not use this file except in compliance with the License.
#  You may obtain a copy of the License at https://www.gnu.org/licenses/lgpl-3.0.en.html
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# -------------------------------------------------------------------------------------------------

"""
Strategy management API endpoints for Nautilus Trader Web UI.

Provides CRUD endpoints for strategy configuration and management,
including integration with strategy classes and lifecycle management.
"""

import importlib
import inspect
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field

from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.identifiers import InstrumentId, StrategyId
from nautilus_trader.model.data import BarType
from nautilus_trader.trading.strategy import Strategy


# Response models
class StrategyInfo(BaseModel):
    """Strategy information model."""
    name: str
    class_name: str
    module_path: str
    description: Optional[str] = None
    config_class: Optional[str] = None
    parameters: Dict[str, Any] = {}


class StrategyConfigResponse(BaseModel):
    """Strategy configuration response model."""
    strategy_id: str
    strategy_type: str
    config: Dict[str, Any]
    status: str = "configured"
    created_at: str
    updated_at: Optional[str] = None


class StrategyStatusResponse(BaseModel):
    """Strategy status response model."""
    strategy_id: str
    status: str  # configured, running, stopped, paused, error
    uptime_seconds: Optional[float] = None
    total_orders: Optional[int] = None
    total_fills: Optional[int] = None
    unrealized_pnl: Optional[float] = None
    realized_pnl: Optional[float] = None
    last_update: str


class StrategyCreateRequest(BaseModel):
    """Strategy creation request model."""
    strategy_id: str
    strategy_type: str
    config: Dict[str, Any]


class StrategyUpdateRequest(BaseModel):
    """Strategy update request model."""
    config: Dict[str, Any]


class StrategyOperationResponse(BaseModel):
    """Strategy operation response model."""
    success: bool
    message: str
    strategy_id: str
    status: Optional[str] = None
    timestamp: str


# Create router
router = APIRouter(prefix="/api/strategies", tags=["strategies"])


def get_app_state(request: Request) -> Dict[str, Any]:
    """Get application state from request."""
    return getattr(request.app.state, "nautilus_state", {})


def get_logger(request: Request):
    """Get logger from request."""
    return getattr(request.app.state, "logger", None)


# Strategy registry - maps strategy names to their classes and configs
STRATEGY_REGISTRY = {
    "EMACross": {
        "class": "nautilus_trader.examples.strategies.ema_cross.EMACross",
        "config": "nautilus_trader.examples.strategies.ema_cross.EMACrossConfig",
        "description": "EMA crossover strategy with configurable fast and slow periods",
    },
    "EMACrossBracket": {
        "class": "nautilus_trader.examples.strategies.ema_cross_bracket.EMACrossBracket",
        "config": "nautilus_trader.examples.strategies.ema_cross_bracket.EMACrossBracketConfig",
        "description": "EMA crossover strategy with bracket orders (stop loss and take profit)",
    },
    "EMACrossLongOnly": {
        "class": "nautilus_trader.examples.strategies.ema_cross_long_only.EMACrossLongOnly",
        "config": "nautilus_trader.examples.strategies.ema_cross_long_only.EMACrossLongOnlyConfig",
        "description": "EMA crossover strategy that only takes long positions",
    },
    "EMACrossTrailingStop": {
        "class": "nautilus_trader.examples.strategies.ema_cross_trailing_stop.EMACrossTrailingStop",
        "config": "nautilus_trader.examples.strategies.ema_cross_trailing_stop.EMACrossTrailingStopConfig",
        "description": "EMA crossover strategy with trailing stop loss",
    },
    "MarketMaker": {
        "class": "nautilus_trader.examples.strategies.market_maker.MarketMaker",
        "config": None,  # No config class, uses constructor parameters
        "description": "Basic market making strategy for testing",
    },
    "OrderBookImbalance": {
        "class": "nautilus_trader.examples.strategies.orderbook_imbalance.OrderBookImbalance",
        "config": "nautilus_trader.examples.strategies.orderbook_imbalance.OrderBookImbalanceConfig",
        "description": "Strategy that trades on order book imbalances",
    },
    "VolatilityMarketMaker": {
        "class": "nautilus_trader.examples.strategies.volatility_market_maker.VolatilityMarketMaker",
        "config": "nautilus_trader.examples.strategies.volatility_market_maker.VolatilityMarketMakerConfig",
        "description": "Market maker that adjusts spreads based on volatility",
    },
}


def load_strategy_class(class_path: str):
    """Load a strategy class from its module path."""
    try:
        module_path, class_name = class_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except Exception as e:
        raise ImportError(f"Failed to load strategy class {class_path}: {e}")


def load_config_class(config_path: str):
    """Load a strategy config class from its module path."""
    try:
        module_path, class_name = config_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except Exception as e:
        raise ImportError(f"Failed to load config class {config_path}: {e}")


def get_class_parameters(cls):
    """Get parameters for a class constructor or config class."""
    try:
        if hasattr(cls, '__annotations__'):
            # For config classes with annotations
            return {
                name: {
                    "type": str(annotation),
                    "required": not hasattr(cls, name) or getattr(cls, name) is None,
                    "default": getattr(cls, name, None) if hasattr(cls, name) else None,
                }
                for name, annotation in cls.__annotations__.items()
                if not name.startswith('_')
            }
        else:
            # For regular classes, inspect constructor
            sig = inspect.signature(cls.__init__)
            params = {}
            for name, param in sig.parameters.items():
                if name == 'self':
                    continue
                params[name] = {
                    "type": str(param.annotation) if param.annotation != inspect.Parameter.empty else "Any",
                    "required": param.default == inspect.Parameter.empty,
                    "default": param.default if param.default != inspect.Parameter.empty else None,
                }
            return params
    except Exception:
        return {}


@router.get("/available", response_model=List[StrategyInfo])
async def get_available_strategies():
    """
    Get list of available strategy types with their configuration parameters.
    """
    strategies = []
    
    for name, info in STRATEGY_REGISTRY.items():
        try:
            # Load strategy class to get parameters
            strategy_class = load_strategy_class(info["class"])
            parameters = {}
            
            if info["config"]:
                # Load config class parameters
                config_class = load_config_class(info["config"])
                parameters = get_class_parameters(config_class)
            else:
                # Get constructor parameters
                parameters = get_class_parameters(strategy_class)
            
            strategies.append(StrategyInfo(
                name=name,
                class_name=info["class"].split(".")[-1],
                module_path=info["class"],
                description=info["description"],
                config_class=info["config"],
                parameters=parameters,
            ))
            
        except Exception as e:
            # Skip strategies that can't be loaded
            continue
    
    return strategies


@router.get("/", response_model=List[StrategyConfigResponse])
async def list_strategies(request: Request):
    """
    List all configured strategies.
    """
    app_state = get_app_state(request)
    strategies = app_state.get("strategies", {})
    
    return [
        StrategyConfigResponse(
            strategy_id=strategy_id,
            strategy_type=config["strategy_type"],
            config=config["config"],
            status=config.get("status", "configured"),
            created_at=config["created_at"],
            updated_at=config.get("updated_at"),
        )
        for strategy_id, config in strategies.items()
    ]


@router.get("/{strategy_id}", response_model=StrategyConfigResponse)
async def get_strategy(strategy_id: str, request: Request):
    """
    Get a specific strategy configuration.
    """
    app_state = get_app_state(request)
    strategies = app_state.get("strategies", {})
    
    if strategy_id not in strategies:
        raise HTTPException(
            status_code=404,
            detail=f"Strategy '{strategy_id}' not found",
        )
    
    config = strategies[strategy_id]
    return StrategyConfigResponse(
        strategy_id=strategy_id,
        strategy_type=config["strategy_type"],
        config=config["config"],
        status=config.get("status", "configured"),
        created_at=config["created_at"],
        updated_at=config.get("updated_at"),
    )


@router.post("/", response_model=StrategyConfigResponse)
async def create_strategy(
    strategy_request: StrategyCreateRequest,
    request: Request,
):
    """
    Create a new strategy configuration.
    """
    app_state = get_app_state(request)
    logger = get_logger(request)
    
    # Initialize strategies dict if not exists
    if "strategies" not in app_state:
        app_state["strategies"] = {}
    
    strategies = app_state["strategies"]
    
    # Check if strategy already exists
    if strategy_request.strategy_id in strategies:
        raise HTTPException(
            status_code=400,
            detail=f"Strategy '{strategy_request.strategy_id}' already exists",
        )
    
    # Validate strategy type
    if strategy_request.strategy_type not in STRATEGY_REGISTRY:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown strategy type '{strategy_request.strategy_type}'. Available types: {list(STRATEGY_REGISTRY.keys())}",
        )
    
    try:
        # Validate configuration by attempting to create config object
        strategy_info = STRATEGY_REGISTRY[strategy_request.strategy_type]
        
        if strategy_info["config"]:
            config_class = load_config_class(strategy_info["config"])
            # Try to create config instance to validate parameters
            config_instance = config_class(**strategy_request.config)
        
        # Store strategy configuration
        now = datetime.now().isoformat()
        strategies[strategy_request.strategy_id] = {
            "strategy_type": strategy_request.strategy_type,
            "config": strategy_request.config,
            "status": "configured",
            "created_at": now,
            "updated_at": now,
        }
        
        if logger:
            logger.info(f"Created strategy configuration: {strategy_request.strategy_id}")
        
        return StrategyConfigResponse(
            strategy_id=strategy_request.strategy_id,
            strategy_type=strategy_request.strategy_type,
            config=strategy_request.config,
            status="configured",
            created_at=now,
            updated_at=now,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid strategy configuration: {str(e)}",
        )


@router.put("/{strategy_id}", response_model=StrategyConfigResponse)
async def update_strategy(
    strategy_id: str,
    strategy_request: StrategyUpdateRequest,
    request: Request,
):
    """
    Update an existing strategy configuration.
    """
    app_state = get_app_state(request)
    logger = get_logger(request)
    strategies = app_state.get("strategies", {})
    
    if strategy_id not in strategies:
        raise HTTPException(
            status_code=404,
            detail=f"Strategy '{strategy_id}' not found",
        )
    
    try:
        # Get existing strategy
        existing_strategy = strategies[strategy_id]
        strategy_type = existing_strategy["strategy_type"]
        
        # Validate new configuration
        strategy_info = STRATEGY_REGISTRY[strategy_type]
        
        if strategy_info["config"]:
            config_class = load_config_class(strategy_info["config"])
            # Try to create config instance to validate parameters
            config_instance = config_class(**strategy_request.config)
        
        # Update strategy configuration
        now = datetime.now().isoformat()
        strategies[strategy_id].update({
            "config": strategy_request.config,
            "updated_at": now,
        })
        
        if logger:
            logger.info(f"Updated strategy configuration: {strategy_id}")
        
        return StrategyConfigResponse(
            strategy_id=strategy_id,
            strategy_type=strategy_type,
            config=strategy_request.config,
            status=existing_strategy.get("status", "configured"),
            created_at=existing_strategy["created_at"],
            updated_at=now,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid strategy configuration: {str(e)}",
        )


@router.delete("/{strategy_id}")
async def delete_strategy(strategy_id: str, request: Request):
    """
    Delete a strategy configuration.
    """
    app_state = get_app_state(request)
    logger = get_logger(request)
    strategies = app_state.get("strategies", {})
    
    if strategy_id not in strategies:
        raise HTTPException(
            status_code=404,
            detail=f"Strategy '{strategy_id}' not found",
        )
    
    # Check if strategy is running
    strategy = strategies[strategy_id]
    if strategy.get("status") == "running":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete running strategy '{strategy_id}'. Stop it first.",
        )
    
    # Delete strategy
    del strategies[strategy_id]
    
    if logger:
        logger.info(f"Deleted strategy configuration: {strategy_id}")
    
    return {"message": f"Strategy '{strategy_id}' deleted successfully"}


@router.get("/{strategy_id}/status", response_model=StrategyStatusResponse)
async def get_strategy_status(strategy_id: str, request: Request):
    """
    Get real-time status of a strategy.
    """
    app_state = get_app_state(request)
    strategies = app_state.get("strategies", {})
    
    if strategy_id not in strategies:
        raise HTTPException(
            status_code=404,
            detail=f"Strategy '{strategy_id}' not found",
        )
    
    strategy_config = strategies[strategy_id]
    
    # Get strategy instance from kernel if running
    kernel = app_state.get("nautilus_kernel")
    strategy_instance = None
    
    if kernel and hasattr(kernel, 'trader'):
        try:
            # Try to get strategy from trader
            trader = kernel.trader
            strategy_instance = trader.strategy(StrategyId(strategy_id))
        except Exception:
            pass
    
    # Build status response
    status = strategy_config.get("status", "configured")
    
    if strategy_instance:
        # Get real-time metrics from strategy instance
        return StrategyStatusResponse(
            strategy_id=strategy_id,
            status="running" if strategy_instance.is_running else "stopped",
            uptime_seconds=None,  # Would need to track start time
            total_orders=len(strategy_instance.cache.orders()),
            total_fills=len(strategy_instance.cache.order_fills()),
            unrealized_pnl=float(strategy_instance.portfolio.unrealized_pnl().as_double()) if strategy_instance.portfolio.unrealized_pnl() else None,
            realized_pnl=float(strategy_instance.portfolio.realized_pnl().as_double()) if strategy_instance.portfolio.realized_pnl() else None,
            last_update=datetime.now().isoformat(),
        )
    else:
        # Return basic status
        return StrategyStatusResponse(
            strategy_id=strategy_id,
            status=status,
            last_update=datetime.now().isoformat(),
        )


@router.post("/{strategy_id}/start", response_model=StrategyOperationResponse)
async def start_strategy(strategy_id: str, request: Request):
    """
    Start a configured strategy.
    """
    app_state = get_app_state(request)
    logger = get_logger(request)
    strategies = app_state.get("strategies", {})
    
    if strategy_id not in strategies:
        raise HTTPException(
            status_code=404,
            detail=f"Strategy '{strategy_id}' not found",
        )
    
    kernel = app_state.get("nautilus_kernel")
    if not kernel:
        raise HTTPException(
            status_code=400,
            detail="Nautilus kernel not initialized. Initialize kernel first.",
        )
    
    try:
        strategy_config = strategies[strategy_id]
        strategy_type = strategy_config["strategy_type"]
        config = strategy_config["config"]
        
        # Load strategy class
        strategy_info = STRATEGY_REGISTRY[strategy_type]
        strategy_class = load_strategy_class(strategy_info["class"])
        
        # Create strategy instance
        if strategy_info["config"]:
            # Use config class
            config_class = load_config_class(strategy_info["config"])
            config_instance = config_class(**config)
            strategy_instance = strategy_class(config=config_instance)
        else:
            # Use constructor parameters directly
            strategy_instance = strategy_class(**config)
        
        # Add strategy to trader
        kernel.trader.add_strategy(strategy_instance)
        
        # Start strategy
        kernel.trader.start_strategy(StrategyId(strategy_id))
        
        # Update status
        strategies[strategy_id]["status"] = "running"
        
        if logger:
            logger.info(f"Started strategy: {strategy_id}")
        
        return StrategyOperationResponse(
            success=True,
            message=f"Strategy '{strategy_id}' started successfully",
            strategy_id=strategy_id,
            status="running",
            timestamp=datetime.now().isoformat(),
        )
        
    except Exception as e:
        error_msg = f"Failed to start strategy '{strategy_id}': {str(e)}"
        if logger:
            logger.error(error_msg)
        
        return StrategyOperationResponse(
            success=False,
            message=error_msg,
            strategy_id=strategy_id,
            status="error",
            timestamp=datetime.now().isoformat(),
        )


@router.post("/{strategy_id}/stop", response_model=StrategyOperationResponse)
async def stop_strategy(strategy_id: str, request: Request):
    """
    Stop a running strategy.
    """
    app_state = get_app_state(request)
    logger = get_logger(request)
    strategies = app_state.get("strategies", {})
    
    if strategy_id not in strategies:
        raise HTTPException(
            status_code=404,
            detail=f"Strategy '{strategy_id}' not found",
        )
    
    kernel = app_state.get("nautilus_kernel")
    if not kernel:
        raise HTTPException(
            status_code=400,
            detail="Nautilus kernel not initialized.",
        )
    
    try:
        # Stop strategy
        kernel.trader.stop_strategy(StrategyId(strategy_id))
        
        # Update status
        strategies[strategy_id]["status"] = "stopped"
        
        if logger:
            logger.info(f"Stopped strategy: {strategy_id}")
        
        return StrategyOperationResponse(
            success=True,
            message=f"Strategy '{strategy_id}' stopped successfully",
            strategy_id=strategy_id,
            status="stopped",
            timestamp=datetime.now().isoformat(),
        )
        
    except Exception as e:
        error_msg = f"Failed to stop strategy '{strategy_id}': {str(e)}"
        if logger:
            logger.error(error_msg)
        
        return StrategyOperationResponse(
            success=False,
            message=error_msg,
            strategy_id=strategy_id,
            status="error",
            timestamp=datetime.now().isoformat(),
        )


@router.post("/{strategy_id}/restart", response_model=StrategyOperationResponse)
async def restart_strategy(strategy_id: str, request: Request):
    """
    Restart a strategy (stop then start).
    """
    app_state = get_app_state(request)
    logger = get_logger(request)
    
    try:
        # Stop strategy first
        stop_response = await stop_strategy(strategy_id, request)
        if not stop_response.success:
            return stop_response
        
        # Start strategy again
        start_response = await start_strategy(strategy_id, request)
        
        if start_response.success:
            if logger:
                logger.info(f"Restarted strategy: {strategy_id}")
            
            return StrategyOperationResponse(
                success=True,
                message=f"Strategy '{strategy_id}' restarted successfully",
                strategy_id=strategy_id,
                status="running",
                timestamp=datetime.now().isoformat(),
            )
        else:
            return start_response
            
    except Exception as e:
        error_msg = f"Failed to restart strategy '{strategy_id}': {str(e)}"
        if logger:
            logger.error(error_msg)
        
        return StrategyOperationResponse(
            success=False,
            message=error_msg,
            strategy_id=strategy_id,
            status="error",
            timestamp=datetime.now().isoformat(),
        )
