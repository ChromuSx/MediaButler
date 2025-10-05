"""
WebSocket manager for real-time updates
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict
import json
import asyncio

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int = None):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)

        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = []
            self.user_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int = None):
        """Remove a WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        if user_id and user_id in self.user_connections:
            if websocket in self.user_connections[user_id]:
                self.user_connections[user_id].remove(websocket)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific connection"""
        await websocket.send_json(message)

    async def send_to_user(self, message: dict, user_id: int):
        """Send a message to all connections of a specific user"""
        if user_id in self.user_connections:
            for connection in self.user_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass  # Connection might be closed

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass  # Connection might be closed

    async def broadcast_download_progress(self, download_id: int, progress: float, speed_mbps: float, eta_seconds: int):
        """Broadcast download progress update"""
        message = {
            "type": "download_progress",
            "data": {
                "download_id": download_id,
                "progress": progress,
                "speed_mbps": speed_mbps,
                "eta_seconds": eta_seconds
            }
        }
        await self.broadcast(message)

    async def broadcast_download_completed(self, download_id: int, filename: str):
        """Broadcast download completion"""
        message = {
            "type": "download_completed",
            "data": {
                "download_id": download_id,
                "filename": filename
            }
        }
        await self.broadcast(message)

    async def broadcast_download_failed(self, download_id: int, filename: str, error: str):
        """Broadcast download failure"""
        message = {
            "type": "download_failed",
            "data": {
                "download_id": download_id,
                "filename": filename,
                "error": error
            }
        }
        await self.broadcast(message)

    async def broadcast_stats_update(self, stats: dict):
        """Broadcast statistics update"""
        message = {
            "type": "stats_update",
            "data": stats
        }
        await self.broadcast(message)


# Global connection manager instance
manager = ConnectionManager()


@router.websocket("/updates")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)

    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "data": {"message": "Connected to MediaButler updates"}
        })

        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)

                # Handle different message types
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"WebSocket error: {e}")
                break

    finally:
        manager.disconnect(websocket)


# Helper function to be called from download manager
async def notify_download_progress(download_id: int, progress: float, speed_mbps: float, eta_seconds: int):
    """Notify clients of download progress"""
    await manager.broadcast_download_progress(download_id, progress, speed_mbps, eta_seconds)


async def notify_download_completed(download_id: int, filename: str):
    """Notify clients of download completion"""
    await manager.broadcast_download_completed(download_id, filename)


async def notify_download_failed(download_id: int, filename: str, error: str):
    """Notify clients of download failure"""
    await manager.broadcast_download_failed(download_id, filename, error)
