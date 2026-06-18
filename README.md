# NovaMart AI Refund Agent

A full-stack AI customer support agent that processes or denies e-commerce refunds using **LangGraph** tool orchestration, a mock CRM with 15 customer profiles, and a strict refund policy.

![Architecture](https://img.shields.io/badge/LangGraph-Agent-blue) ![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-green) ![Voice](https://img.shields.io/badge/Voice-Web_Speech_API-orange)

## Demo Video

> **[Add your Loom walkthrough link here]**

Suggested 7–10 min script:
1. **Standard refund** — Michael Brown (`ORD-10012`, $22 apparel, tags on) → approved
2. **Policy violation** — Robert Taylor (`ORD-10008`, final sale jacket) → denied, agent holds the line
3. **Voice demo** — click mic, speak a refund request
4. **Code tour** — `backend/app/agent/graph.py`, `tools.py`, WebSocket logs
5. **Admin panel** — tool calls, denials, retries in real time

## Features

| Component | Details |
|-----------|---------|
| **Mock CRM** | 15 customer profiles with orders, loyalty tiers, abuse flags |
| **Refund Policy** | Strict markdown policy (`backend/data/refund_policy.md`) |
| **Agent Backend** | LangGraph loop with 5 tools + retry logic |
| **Admin Dashboard** | Real-time reasoning logs via WebSocket |
| **Customer Chat** | Text chat with quick demo prompts |
| **Voice** | Web Speech API (STT) + browser TTS |

## Architecture

```
┌─────────────────┐     REST/WS      ┌──────────────────────────────┐
│  React Frontend │ ◄──────────────► │  FastAPI Backend             │
│  - Chat + Voice │                  │  - /api/chat, /api/voice     │
│  - Admin Logs   │                  │  - /ws/logs (WebSocket)      │
└─────────────────┘                  └──────────────┬───────────────┘
                                                    │
                                         ┌──────────▼──────────┐
                                         │  LangGraph Agent    │
                                         │  ┌───────────────┐  │
                                         │  │ agent → tools │  │
                                         │  │     ↓ retry   │  │
                                         │  └───────────────┘  │
                                         └──────────┬──────────┘
                                                    │
                              ┌─────────────────────┼─────────────────────┐
                              ▼                     ▼                     ▼
                      lookup_customer    check_refund_eligibility   process_refund
                      get_order_details  escalate_to_human          (CRM JSON)
```

### Agent Tools (required sequence)

1. `lookup_customer` — verify identity & loyalty tier
2. `get_order_details` — order data, delivery date, final-sale flags
3. `check_refund_eligibility` — automated policy enforcement
4. `process_refund` — only when `eligible: true`
5. `escalate_to_human` — orders > $200

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- OpenAI API key (optional — mock mode works without it)

### 1. Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
cp ../.env.example ../.env   # add OPENAI_API_KEY
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**

## Demo Scenarios

| Customer | Order | Scenario | Expected |
|----------|-------|----------|----------|
| Michael Brown | ORD-10012 | Standard apparel refund, tags on | ✅ Approved |
| Robert Taylor | ORD-10008 | Final sale clearance jacket | ❌ Denied (Policy §2) |
| David Kim | ORD-10005 | Abuse-flagged customer | ❌ Denied (Policy §4) |
| Lisa Park | ORD-10011 | $299 sealed webcam | ⚠️ Escalation (> $200) |
| Jessica Williams | ORD-10007 | Digital e-book accessed | ❌ Denied (Policy §2) |
| James Wilson | ORD-10010 | 109 days since delivery | ❌ Denied (Policy §1) |

Use the **quick prompt buttons** in the chat UI for instant demo scenarios.

## Project Structure

```
ai-refund-agent/
├── backend/
│   ├── app/
│   │   ├── agent/
│   │   │   ├── graph.py      # LangGraph agent loop
│   │   │   └── mock.py       # Fallback without API key
│   │   ├── main.py           # FastAPI + WebSocket
│   │   ├── models.py         # Log broadcaster
│   │   └── tools.py          # CRM + policy tools
│   └── data/
│       ├── crm.json          # 15 customer profiles
│       └── refund_policy.md  # Strict policy doc
├── frontend/
│   └── src/
│       ├── App.tsx
│       └── components/
│           ├── ChatPanel.tsx
│           └── AdminDashboard.tsx
└── README.md
```

## Environment Variables

| Variable | Required | Default |
|----------|----------|---------|
| `OPENAI_API_KEY` | No* | — |
| `OPENAI_MODEL` | No | `gpt-4o-mini` |

\* Without an API key, the app runs in **mock mode** (rule-based agent with full tool logging).

## License

MIT
