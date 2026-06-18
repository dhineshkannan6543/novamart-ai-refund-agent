"""FastAPI application — chat API, WebSocket logs, voice transcription."""

from __future__ import annotations

import os
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.agent.graph import run_agent
from app.models import ChatRequest, ChatResponse, log_broadcaster
from app.tools import load_policy_text

load_dotenv()

app = FastAPI(title="NovaMart AI Refund Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok", "openai_configured": bool(os.getenv("OPENAI_API_KEY"))}


@app.get("/api/policy")
async def get_policy():
    return {"policy": load_policy_text()}


@app.get("/api/customers")
async def list_customers():
    from app.tools import _load_crm

    data = _load_crm()
    return {
        "customers": [
            {
                "customer_id": c["customer_id"],
                "name": c["name"],
                "email": c["email"],
                "loyalty_tier": c["loyalty_tier"],
                "orders": len(c["orders"]),
            }
            for c in data["customers"]
        ]
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    session_id, message, decision = await run_agent(
        request.message,
        session_id=request.session_id,
        customer_email=request.customer_email,
    )
    return ChatResponse(
        session_id=session_id,
        message=message,
        refund_decision=decision,
    )


class VoiceRequest(BaseModel):
    transcript: str
    session_id: str | None = None
    customer_email: str | None = None


@app.post("/api/voice", response_model=ChatResponse)
async def voice_chat(request: VoiceRequest):
    """Process voice transcript through the same agent pipeline."""
    prefixed = f"[Voice channel] {request.transcript}"
    session_id, message, decision = await run_agent(
        prefixed,
        session_id=request.session_id,
        customer_email=request.customer_email,
    )
    return ChatResponse(
        session_id=session_id,
        message=message,
        refund_decision=decision,
    )


@app.get("/api/logs")
async def get_logs(limit: int = 100):
    return {"logs": [e.model_dump() for e in log_broadcaster.get_history(limit)]}


@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await websocket.accept()
    await log_broadcaster.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await log_broadcaster.disconnect(websocket)
