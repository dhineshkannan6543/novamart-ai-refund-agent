"""Shared types and log broadcasting for the refund agent."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class LogLevel(str, Enum):
    INFO = "info"
    TOOL = "tool"
    REASONING = "reasoning"
    SUCCESS = "success"
    ERROR = "error"
    RETRY = "retry"
    DENIAL = "denial"


class AgentLogEntry(BaseModel):
    id: str
    session_id: str
    timestamp: str
    level: LogLevel
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    customer_email: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    message: str
    refund_decision: str | None = None


class LogBroadcaster:
    """Broadcasts agent logs to all connected admin WebSocket clients."""

    def __init__(self) -> None:
        self._connections: set[Any] = set()
        self._history: list[AgentLogEntry] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: Any) -> None:
        async with self._lock:
            self._connections.add(websocket)
        for entry in self._history[-200:]:
            await websocket.send_text(entry.model_dump_json())

    async def disconnect(self, websocket: Any) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def emit(
        self,
        session_id: str,
        level: LogLevel,
        message: str,
        metadata: dict[str, Any] | None = None,
        entry_id: str | None = None,
    ) -> AgentLogEntry:
        entry = AgentLogEntry(
            id=entry_id or f"log-{len(self._history) + 1}",
            session_id=session_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=level,
            message=message,
            metadata=metadata or {},
        )
        async with self._lock:
            self._history.append(entry)
            if len(self._history) > 500:
                self._history = self._history[-500:]
            dead: set[Any] = set()
            payload = entry.model_dump_json()
            for ws in self._connections:
                try:
                    await ws.send_text(payload)
                except Exception:
                    dead.add(ws)
            self._connections -= dead
        return entry

    def get_history(self, limit: int = 100) -> list[AgentLogEntry]:
        return self._history[-limit:]


log_broadcaster = LogBroadcaster()
