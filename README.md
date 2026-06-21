# NovaMart AI Refund Agent

An AI-powered customer support agent that processes e-commerce refund requests using policy-aware tool orchestration, LangGraph workflows, and real-time reasoning logs.

## Overview

NovaMart AI Refund Agent evaluates customer refund requests against a strict refund policy and CRM records before approving, denying, or escalating requests.

The system demonstrates:

* AI-powered customer support automation
* Tool-calling workflows with LangGraph
* Policy enforcement and compliance
* Real-time reasoning transparency
* Voice-enabled customer interactions
* Graceful fallback when LLM services are unavailable

---

## Features

### Customer Support Agent

* Refund request handling
* Policy-aware decision making
* Multi-step tool orchestration
* Human escalation workflow
* Voice interaction support

### Mock CRM Database

* 15 customer profiles
* Order history
* Loyalty tiers
* Refund abuse indicators

### Refund Policy Engine

* 30-day refund window enforcement
* Final-sale restrictions
* Duplicate refund prevention
* Escalation rules for high-value orders

### Admin Dashboard

* Live reasoning logs
* Tool execution tracing
* Success and denial tracking
* Retry and error visibility

### Resilience

* Automatic fallback to deterministic policy engine when OpenAI services are unavailable
* No interruption to customer support workflows

---

## Tech Stack

### Backend

* FastAPI
* LangGraph
* LangChain
* OpenAI
* WebSockets

### Frontend

* React
* TypeScript
* Vite

---

## Architecture

Customer Chat / Voice

↓

LangGraph Agent

↓

Tool Orchestration

* lookup_customer
* get_order_details
* check_refund_eligibility
* process_refund
* escalate_to_human

↓

Refund Decision

↓

Admin Reasoning Dashboard

---

## Demo Scenarios

### Standard Refund Approval

Customer:
Chris Martinez

Order:
ORD-10014

Result:
Refund Approved

---

### Policy Violation ("Holding the Line")

Customer:
Robert Taylor

Order:
ORD-10008

Result:
Refund Denied

Reasons:

* Final Sale Item
* Outside Refund Window

---

### Voice Interaction

Speak a refund request using the microphone button and observe the same agent workflow execute through voice input.

---

## Setup

### Backend

```bash
cd backend

python -m venv .venv

source .venv/bin/activate
# Windows:
# .venv\Scripts\activate

pip install -r requirements.txt

uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend

npm install

npm run dev
```

---

## Environment Variables

Create:

backend/.env

```env
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-4o-mini
```

---

## API Documentation

FastAPI Swagger UI:

http://localhost:8000/docs

---

## Loom Video Walkthrough

Loom Video:

[https://www.loom.com/share/7013555f435c419ba2fe2bb9dd835860]

---

## GitHub Repository

https://github.com/dhineshkannan6543/novamart-ai-refund-agent
