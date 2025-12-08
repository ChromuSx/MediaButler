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

    async def _send_safe(self, connection: WebSocket, message: dict):
        """
        Safely send message to a connection, handling errors gracefully.

        Args:
            connection: WebSocket connection
            message: Message to send

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            await connection.send_json(message)
            return True
        except Exception:
            # Connection might be closed or broken
            return False

    async def send_to_user(self, message: dict, user_id: int):
        """
        Send a message to all connections of a specific user in parallel.

        Uses asyncio.gather to send to all user connections simultaneously,
        improving performance for users with multiple active sessions.

        Args:
            message: Message dict to send
            user_id: Target user ID
        """
        if user_id in self.user_connections:
            # Send to all user connections in parallel
            await asyncio.gather(
                *[
                    self._send_safe(conn, message)
                    for conn in self.user_connections[user_id]
                ],
                return_exceptions=True,
            )

    async def broadcast(self, message: dict):
        """
        Broadcast a message to all connected clients in parallel.

        Optimized to send messages concurrently using asyncio.gather instead
        of sequential sends. This significantly improves performance when
        broadcasting to many connected clients.

        Args:
            message: Message dict to send to all clients

        Performance:
            - Sequential (old): O(n) where n = number of connections
            - Parallel (new): O(1) with concurrent sends
        """
        if not self.active_connections:
            return

        # Broadcast to all connections in parallel
        await asyncio.gather(
            *[self._send_safe(conn, message) for conn in self.active_connections],
            return_exceptions=True,
        )

    async def broadcast_download_progress(
        self, download_id: int, progress: float, speed_mbps: float, eta_seconds: int
    ):
        """Broadcast download progress update"""
        message = {
            "type": "download_progress",
            "data": {
                "download_id": download_id,
                "progress": progress,
                "speed_mbps": speed_mbps,
                "eta_seconds": eta_seconds,
            },
        }
        await self.broadcast(message)

    async def broadcast_download_completed(self, download_id: int, filename: str):
        """Broadcast download completion"""
        message = {
            "type": "download_completed",
            "data": {"download_id": download_id, "filename": filename},
        }
        await self.broadcast(message)

    async def broadcast_download_failed(
        self, download_id: int, filename: str, error: str
    ):
        """Broadcast download failure"""
        message = {
            "type": "download_failed",
            "data": {"download_id": download_id, "filename": filename, "error": error},
        }
        await self.broadcast(message)

    async def broadcast_stats_update(self, stats: dict):
        """Broadcast statistics update"""
        message = {"type": "stats_update", "data": stats}
        await self.broadcast(message)

    async def broadcast_download_started(
        self, download_id: int, filename: str, user_id: int
    ):
        """Broadcast download started"""
        message = {
            "type": "download_started",
            "data": {
                "download_id": download_id,
                "filename": filename,
                "user_id": user_id,
                "timestamp": None,  # Will be set by client
            },
        }
        await self.broadcast(message)

    async def broadcast_user_added(self, user_id: int, username: str):
        """Broadcast new user added"""
        message = {
            "type": "user_added",
            "data": {"user_id": user_id, "username": username},
        }
        await self.broadcast(message)

    async def broadcast_user_removed(self, user_id: int):
        """Broadcast user removed"""
        message = {"type": "user_removed", "data": {"user_id": user_id}}
        await self.broadcast(message)

    async def broadcast_space_warning(self, available_gb: float, threshold_gb: float):
        """Broadcast low space warning"""
        message = {
            "type": "space_warning",
            "data": {"available_gb": available_gb, "threshold_gb": threshold_gb},
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
        await websocket.send_json(
            {
                "type": "connected",
                "data": {"message": "Connected to MediaButler updates"},
            }
        )

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
async def notify_download_progress(
    download_id: int, progress: float, speed_mbps: float, eta_seconds: int
):
    """Notify clients of download progress"""
    await manager.broadcast_download_progress(
        download_id, progress, speed_mbps, eta_seconds
    )


async def notify_download_completed(download_id: int, filename: str):
    """Notify clients of download completion"""
    await manager.broadcast_download_completed(download_id, filename)


async def notify_download_failed(download_id: int, filename: str, error: str):
    """Notify clients of download failure"""
    await manager.broadcast_download_failed(download_id, filename, error)


async def notify_download_started(download_id: int, filename: str, user_id: int):
    """Notify clients of download start"""
    await manager.broadcast_download_started(download_id, filename, user_id)


async def notify_stats_update(stats: dict):
    """Notify clients of stats update"""
    await manager.broadcast_stats_update(stats)


async def notify_user_added(user_id: int, username: str):
    """Notify clients of new user"""
    await manager.broadcast_user_added(user_id, username)


async def notify_user_removed(user_id: int):
    """Notify clients of removed user"""
    await manager.broadcast_user_removed(user_id)


async def notify_space_warning(available_gb: float, threshold_gb: float):
    """Notify clients of low space warning"""
    await manager.broadcast_space_warning(available_gb, threshold_gb)
