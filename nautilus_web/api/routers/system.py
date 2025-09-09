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
System management API endpoints for Nautilus Trader Web UI.

Provides endpoints for system status, health checks, kernel management,
and real-time system metrics.
"""

import asyncio
import platform
import psutil
import time
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel

from nautilus_trader.common import Environment
from nautilus_trader.config import NautilusKernelConfig
from nautilus_trader.system.kernel import NautilusKernel


# Response models
class SystemStatusResponse(BaseModel):
    """System status response model."""
    status: str
    uptime_seconds: float
    kernel_status: Optional[str] = None
    environment: Optional[str] = None
    trader_id: Optional[str] = None
    instance_id: Optional[str] = None
    components: Dict[str, Any] = {}


class SystemMetricsResponse(BaseModel):
    """System metrics response model."""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    disk_usage_percent: float
    platform_info: Dict[str, str]
    process_info: Dict[str, Any]


class KernelConfigRequest(BaseModel):
    """Kernel configuration request model."""
    environment: str = "backtest"
    trader_id: str = "TRADER-001"
    instance_id: Optional[str] = None
    log_level: str = "INFO"


class KernelOperationResponse(BaseModel):
    """Kernel operation response model."""
    success: bool
    message: str
    kernel_status: Optional[str] = None
    timestamp: str


# Create router
router = APIRouter(prefix="/api/system", tags=["system"])

# Global system state
system_start_time = time.time()


def get_app_state(request: Request) -> Dict[str, Any]:
    """Get application state from request."""
    return getattr(request.app.state, "nautilus_state", {})


def get_logger(request: Request):
    """Get logger from request."""
    return getattr(request.app.state, "logger", None)


@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status(request: Request):
    """
    Get comprehensive system status including kernel state.
    """
    app_state = get_app_state(request)
    kernel = app_state.get("nautilus_kernel")
    
    uptime = time.time() - system_start_time
    
    # Determine kernel status
    kernel_status = "not_initialized"
    environment = None
    trader_id = None
    instance_id = None
    components = {}
    
    if kernel:
        kernel_status = "running"
        if hasattr(kernel, '_environment'):
            environment = kernel._environment.value if kernel._environment else None
        if hasattr(kernel, '_trader_id'):
            trader_id = str(kernel._trader_id) if kernel._trader_id else None
        if hasattr(kernel, '_instance_id'):
            instance_id = str(kernel._instance_id) if kernel._instance_id else None
        
        # Get component status
        try:
            components = {
                "data_engine": "active" if hasattr(kernel, '_data_engine') and kernel._data_engine else "inactive",
                "risk_engine": "active" if hasattr(kernel, '_risk_engine') and kernel._risk_engine else "inactive",
                "exec_engine": "active" if hasattr(kernel, '_exec_engine') and kernel._exec_engine else "inactive",
                "portfolio": "active" if hasattr(kernel, '_portfolio') and kernel._portfolio else "inactive",
                "trader": "active" if hasattr(kernel, '_trader') and kernel._trader else "inactive",
            }
        except Exception:
            components = {"error": "Unable to retrieve component status"}
    
    return SystemStatusResponse(
        status="healthy",
        uptime_seconds=uptime,
        kernel_status=kernel_status,
        environment=environment,
        trader_id=trader_id,
        instance_id=instance_id,
        components=components,
    )


@router.get("/metrics", response_model=SystemMetricsResponse)
async def get_system_metrics():
    """
    Get real-time system metrics including CPU, memory, and disk usage.
    """
    # Get system metrics
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Get process info
    process = psutil.Process()
    process_info = {
        "pid": process.pid,
        "cpu_percent": process.cpu_percent(),
        "memory_percent": process.memory_percent(),
        "memory_info_mb": process.memory_info().rss / 1024 / 1024,
        "num_threads": process.num_threads(),
        "create_time": datetime.fromtimestamp(process.create_time()).isoformat(),
    }
    
    # Platform information
    platform_info = {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
    }
    
    return SystemMetricsResponse(
        timestamp=datetime.now().isoformat(),
        cpu_percent=cpu_percent,
        memory_percent=memory.percent,
        memory_used_mb=memory.used / 1024 / 1024,
        memory_total_mb=memory.total / 1024 / 1024,
        disk_usage_percent=disk.percent,
        platform_info=platform_info,
        process_info=process_info,
    )


@router.post("/kernel/initialize", response_model=KernelOperationResponse)
async def initialize_kernel(
    config_request: KernelConfigRequest,
    request: Request,
):
    """
    Initialize the Nautilus kernel with the provided configuration.
    """
    app_state = get_app_state(request)
    logger = get_logger(request)
    
    try:
        # Check if kernel already exists
        if app_state.get("nautilus_kernel"):
            return KernelOperationResponse(
                success=False,
                message="Kernel already initialized. Stop the current kernel first.",
                kernel_status="already_running",
                timestamp=datetime.now().isoformat(),
            )
        
        # Create kernel configuration
        kernel_config = NautilusKernelConfig(
            environment=Environment(config_request.environment),
            trader_id=config_request.trader_id,
            instance_id=config_request.instance_id,
            log_level=config_request.log_level,
        )
        
        # Initialize kernel
        kernel = NautilusKernel(
            name="WebUIKernel",
            config=kernel_config,
        )
        
        # Store kernel in application state
        app_state["nautilus_kernel"] = kernel
        
        if logger:
            logger.info(f"Nautilus kernel initialized with environment: {config_request.environment}")
        
        return KernelOperationResponse(
            success=True,
            message=f"Kernel initialized successfully with environment: {config_request.environment}",
            kernel_status="initialized",
            timestamp=datetime.now().isoformat(),
        )
        
    except Exception as e:
        error_msg = f"Failed to initialize kernel: {str(e)}"
        if logger:
            logger.error(error_msg)
        
        return KernelOperationResponse(
            success=False,
            message=error_msg,
            kernel_status="error",
            timestamp=datetime.now().isoformat(),
        )


@router.post("/kernel/start", response_model=KernelOperationResponse)
async def start_kernel(request: Request):
    """
    Start the Nautilus kernel.
    """
    app_state = get_app_state(request)
    logger = get_logger(request)
    kernel = app_state.get("nautilus_kernel")
    
    if not kernel:
        raise HTTPException(
            status_code=400,
            detail="Kernel not initialized. Initialize kernel first.",
        )
    
    try:
        # Start kernel asynchronously
        await kernel.start_async()
        
        if logger:
            logger.info("Nautilus kernel started successfully")
        
        return KernelOperationResponse(
            success=True,
            message="Kernel started successfully",
            kernel_status="running",
            timestamp=datetime.now().isoformat(),
        )
        
    except Exception as e:
        error_msg = f"Failed to start kernel: {str(e)}"
        if logger:
            logger.error(error_msg)
        
        return KernelOperationResponse(
            success=False,
            message=error_msg,
            kernel_status="error",
            timestamp=datetime.now().isoformat(),
        )


@router.post("/kernel/stop", response_model=KernelOperationResponse)
async def stop_kernel(request: Request):
    """
    Stop the Nautilus kernel.
    """
    app_state = get_app_state(request)
    logger = get_logger(request)
    kernel = app_state.get("nautilus_kernel")
    
    if not kernel:
        raise HTTPException(
            status_code=400,
            detail="Kernel not initialized.",
        )
    
    try:
        # Stop kernel asynchronously
        await kernel.stop_async()
        
        if logger:
            logger.info("Nautilus kernel stopped successfully")
        
        return KernelOperationResponse(
            success=True,
            message="Kernel stopped successfully",
            kernel_status="stopped",
            timestamp=datetime.now().isoformat(),
        )
        
    except Exception as e:
        error_msg = f"Failed to stop kernel: {str(e)}"
        if logger:
            logger.error(error_msg)
        
        return KernelOperationResponse(
            success=False,
            message=error_msg,
            kernel_status="error",
            timestamp=datetime.now().isoformat(),
        )


@router.post("/kernel/restart", response_model=KernelOperationResponse)
async def restart_kernel(request: Request):
    """
    Restart the Nautilus kernel (stop then start).
    """
    app_state = get_app_state(request)
    logger = get_logger(request)
    kernel = app_state.get("nautilus_kernel")
    
    if not kernel:
        raise HTTPException(
            status_code=400,
            detail="Kernel not initialized.",
        )
    
    try:
        # Stop kernel first
        await kernel.stop_async()
        
        # Wait a moment for cleanup
        await asyncio.sleep(1)
        
        # Start kernel again
        await kernel.start_async()
        
        if logger:
            logger.info("Nautilus kernel restarted successfully")
        
        return KernelOperationResponse(
            success=True,
            message="Kernel restarted successfully",
            kernel_status="running",
            timestamp=datetime.now().isoformat(),
        )
        
    except Exception as e:
        error_msg = f"Failed to restart kernel: {str(e)}"
        if logger:
            logger.error(error_msg)
        
        return KernelOperationResponse(
            success=False,
            message=error_msg,
            kernel_status="error",
            timestamp=datetime.now().isoformat(),
        )


@router.delete("/kernel", response_model=KernelOperationResponse)
async def dispose_kernel(request: Request):
    """
    Dispose of the Nautilus kernel and clean up resources.
    """
    app_state = get_app_state(request)
    logger = get_logger(request)
    kernel = app_state.get("nautilus_kernel")
    
    if not kernel:
        return KernelOperationResponse(
            success=True,
            message="No kernel to dispose",
            kernel_status="not_initialized",
            timestamp=datetime.now().isoformat(),
        )
    
    try:
        # Stop kernel if running
        try:
            await kernel.stop_async()
        except Exception:
            pass  # Ignore errors during stop
        
        # Dispose kernel
        kernel.dispose()
        
        # Remove from application state
        app_state["nautilus_kernel"] = None
        
        if logger:
            logger.info("Nautilus kernel disposed successfully")
        
        return KernelOperationResponse(
            success=True,
            message="Kernel disposed successfully",
            kernel_status="disposed",
            timestamp=datetime.now().isoformat(),
        )
        
    except Exception as e:
        error_msg = f"Failed to dispose kernel: {str(e)}"
        if logger:
            logger.error(error_msg)
        
        return KernelOperationResponse(
            success=False,
            message=error_msg,
            kernel_status="error",
            timestamp=datetime.now().isoformat(),
        )


@router.get("/kernel/info")
async def get_kernel_info(request: Request):
    """
    Get detailed information about the current kernel instance.
    """
    app_state = get_app_state(request)
    kernel = app_state.get("nautilus_kernel")
    
    if not kernel:
        raise HTTPException(
            status_code=404,
            detail="Kernel not initialized.",
        )
    
    try:
        info = {
            "environment": kernel._environment.value if hasattr(kernel, '_environment') and kernel._environment else None,
            "trader_id": str(kernel._trader_id) if hasattr(kernel, '_trader_id') and kernel._trader_id else None,
            "instance_id": str(kernel._instance_id) if hasattr(kernel, '_instance_id') and kernel._instance_id else None,
            "loop": str(type(kernel.loop).__name__) if hasattr(kernel, 'loop') and kernel.loop else None,
            "components": {
                "cache": str(type(kernel.cache).__name__) if hasattr(kernel, 'cache') and kernel.cache else None,
                "portfolio": str(type(kernel.portfolio).__name__) if hasattr(kernel, 'portfolio') and kernel.portfolio else None,
                "data_engine": str(type(kernel.data_engine).__name__) if hasattr(kernel, 'data_engine') and kernel.data_engine else None,
                "risk_engine": str(type(kernel.risk_engine).__name__) if hasattr(kernel, 'risk_engine') and kernel.risk_engine else None,
                "exec_engine": str(type(kernel.exec_engine).__name__) if hasattr(kernel, 'exec_engine') and kernel.exec_engine else None,
                "trader": str(type(kernel.trader).__name__) if hasattr(kernel, 'trader') and kernel.trader else None,
            },
            "timestamp": datetime.now().isoformat(),
        }
        
        return info
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get kernel info: {str(e)}",
        )
