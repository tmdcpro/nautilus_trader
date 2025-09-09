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
FastAPI application for Nautilus Trader Web UI.

Provides REST API endpoints and WebSocket connections for managing
trading strategies, backtesting, live trading, and system monitoring.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from nautilus_trader.common.component import Logger


# Global application state
app_state = {
    "nautilus_kernel": None,
    "trading_nodes": {},
    "backtest_engines": {},
    "websocket_connections": set(),
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    """
    # Startup
    logger = Logger(name="NautilusWebAPI")
    logger.info("Starting Nautilus Trader Web API")
    
    # Initialize application state
    app.state.nautilus_state = app_state
    app.state.logger = logger
    
    yield
    
    # Shutdown
    logger.info("Shutting down Nautilus Trader Web API")
    
    # Clean up resources
    if app_state["nautilus_kernel"]:
        try:
            await app_state["nautilus_kernel"].stop()
        except Exception as e:
            logger.error(f"Error stopping Nautilus kernel: {e}")
    
    # Close WebSocket connections
    for ws in app_state["websocket_connections"].copy():
        try:
            await ws.close()
        except Exception as e:
            logger.error(f"Error closing WebSocket connection: {e}")


# Create FastAPI application
app = FastAPI(
    title="Nautilus Trader Web API",
    description="REST API and WebSocket interface for Nautilus Trader",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions with consistent error format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "type": "HTTPException",
            }
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions with logging."""
    logger = getattr(request.app.state, "logger", None)
    if logger:
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "type": "InternalServerError",
            }
        },
    )


# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "nautilus-trader-web-api",
        "version": "1.0.0",
    }


# Root endpoint
@app.get("/api")
async def root():
    """Root API endpoint with basic information."""
    return {
        "name": "Nautilus Trader Web API",
        "version": "1.0.0",
        "description": "REST API and WebSocket interface for Nautilus Trader",
        "endpoints": {
            "health": "/api/health",
            "docs": "/api/docs",
            "websocket": "/api/ws",
        },
    }


# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a specific WebSocket connection."""
        try:
            await websocket.send_text(message)
        except Exception:
            self.disconnect(websocket)
    
    async def broadcast(self, message: str):
        """Broadcast a message to all connected WebSocket clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)


# Initialize connection manager
manager = ConnectionManager()


# WebSocket endpoint for real-time updates
@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time data streaming."""
    await manager.connect(websocket)
    
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            
            # Echo back for now - will be enhanced in later tasks
            await manager.send_personal_message(f"Echo: {data}", websocket)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger = getattr(app.state, "logger", None)
        if logger:
            logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# Mount static files for frontend (will be created in frontend task)
try:
    app.mount("/static", StaticFiles(directory="nautilus_web/static"), name="static")
except RuntimeError:
    # Directory doesn't exist yet or is empty - will be populated in frontend task
    pass


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "nautilus_web.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
