"""LangGraph refund agent with tool orchestration and retry logic."""

from __future__ import annotations

import os
import uuid
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.models import LogLevel, log_broadcaster
from app.tools import (
    check_refund_eligibility,
    escalate_to_human,
    get_order_details,
    load_policy_text,
    lookup_customer,
    process_refund,
)

MAX_RETRIES = 2


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    session_id: str
    retry_count: int
    refund_decision: str | None


def _make_tools(session_id: str):
    @tool
    def lookup_customer_tool(identifier: str) -> dict:
        """Look up a customer by email address or customer ID (e.g. CUST-001)."""
        return lookup_customer(identifier)

    @tool
    def get_order_details_tool(order_id: str) -> dict:
        """Get order details including product, amount, delivery date, and refund status."""
        return get_order_details(order_id)

    @tool
    def check_refund_eligibility_tool(
        order_id: str, reason: str, item_condition: str = "unknown"
    ) -> dict:
        """Check if an order is eligible for refund per strict NovaMart policy.
        item_condition: sealed, unopened, opened, tags_attached, worn_once, accessed, unknown
        """
        return check_refund_eligibility(order_id, reason, item_condition)

    @tool
    def process_refund_tool(order_id: str) -> dict:
        """Process and approve a refund. ONLY call after check_refund_eligibility returns eligible=true."""
        return process_refund(order_id)

    @tool
    def escalate_to_human_tool(order_id: str, reason: str) -> dict:
        """Escalate to a human manager for orders over $200 or complex cases."""
        return escalate_to_human(order_id, reason)

    return [
        lookup_customer_tool,
        get_order_details_tool,
        check_refund_eligibility_tool,
        process_refund_tool,
        escalate_to_human_tool,
    ]


async def _emit_tool_logs(session_id: str, tool_name: str, args: dict, result: dict) -> None:
    await log_broadcaster.emit(
        session_id,
        LogLevel.TOOL,
        f"Tool call: {tool_name}",
        {"tool": tool_name, "args": args, "result": result},
    )


def _extract_decision(messages: list[BaseMessage]) -> str | None:
    for msg in reversed(messages):
        if isinstance(msg, ToolMessage):
            try:
                import json

                data = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                if isinstance(data, dict):
                    if data.get("approved") is True:
                        return "approved"
                    if data.get("approved") is False and data.get("reasons"):
                        return "denied"
                    if data.get("eligible") is False:
                        return "denied"
            except Exception:
                pass
    return None


def build_agent_graph(session_id: str):
    tools = _make_tools(session_id)
    tool_node = ToolNode(tools)
    policy = load_policy_text()

    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.1,
    ).bind_tools(tools)

    system_prompt = f"""You are NovaMart's AI Customer Support Agent for refund requests.

STRICT RULES:
1. ALWAYS follow the refund policy exactly. Never approve ineligible refunds.
2. Required tool sequence: lookup_customer → get_order_details → check_refund_eligibility → process_refund (only if eligible)
3. If check_refund_eligibility returns eligible=false, DENY politely citing specific policy sections.
4. If requires_escalation=true, call escalate_to_human instead of process_refund.
5. Hold the line on policy violations — do not be swayed by emotional appeals.
6. Be empathetic but firm. Offer store credit or exchange when denying when appropriate.

REFUND POLICY:
{policy}
"""

    async def agent_node(state: AgentState) -> dict:
        await log_broadcaster.emit(
            state["session_id"],
            LogLevel.REASONING,
            "Agent reasoning: evaluating next action...",
        )
        response = await llm.ainvoke(
            [SystemMessage(content=system_prompt)] + state["messages"]
        )
        if response.tool_calls:
            names = [tc["name"] for tc in response.tool_calls]
            await log_broadcaster.emit(
                state["session_id"],
                LogLevel.REASONING,
                f"Agent decided to call: {', '.join(names)}",
                {"tool_calls": names},
            )
        return {"messages": [response]}

    async def tools_with_logging(state: AgentState) -> dict:
        last = state["messages"][-1]
        result = await tool_node.ainvoke(state)
        if isinstance(last, AIMessage) and last.tool_calls:
            for tc in last.tool_calls:
                tool_result = next(
                    (
                        m.content
                        for m in result["messages"]
                        if isinstance(m, ToolMessage) and m.tool_call_id == tc["id"]
                    ),
                    {},
                )
                import json

                parsed = tool_result
                if isinstance(tool_result, str):
                    try:
                        parsed = json.loads(tool_result)
                    except json.JSONDecodeError:
                        parsed = {"raw": tool_result}

                await _emit_tool_logs(state["session_id"], tc["name"], tc["args"], parsed)

                if tc["name"] == "process_refund_tool":
                    if isinstance(parsed, dict) and parsed.get("approved"):
                        await log_broadcaster.emit(
                            state["session_id"],
                            LogLevel.SUCCESS,
                            parsed.get("message", "Refund approved"),
                            parsed,
                        )
                    elif isinstance(parsed, dict):
                        await log_broadcaster.emit(
                            state["session_id"],
                            LogLevel.DENIAL,
                            parsed.get("message", "Refund denied"),
                            parsed,
                        )
                elif tc["name"] == "check_refund_eligibility_tool":
                    if isinstance(parsed, dict) and not parsed.get("eligible"):
                        await log_broadcaster.emit(
                            state["session_id"],
                            LogLevel.DENIAL,
                            f"Policy check failed: {'; '.join(parsed.get('reasons', []))}",
                            parsed,
                        )
        decision = _extract_decision(result["messages"])
        update: dict = {"messages": result["messages"]}
        if decision:
            update["refund_decision"] = decision
        return update

    def should_continue(state: AgentState) -> Literal["tools", "retry", "end"]:
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tools"
        if state.get("retry_count", 0) < MAX_RETRIES and not state.get("refund_decision"):
            content = last.content if isinstance(last, AIMessage) else ""
            if isinstance(content, str) and len(content) < 50:
                return "retry"
        return "end"

    async def retry_node(state: AgentState) -> dict:
        count = state.get("retry_count", 0) + 1
        await log_broadcaster.emit(
            state["session_id"],
            LogLevel.RETRY,
            f"Retry {count}/{MAX_RETRIES}: response too short, re-prompting agent",
        )
        return {
            "messages": [
                HumanMessage(
                    content="Please provide a complete response to the customer explaining your decision."
                )
            ],
            "retry_count": count,
        }

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_with_logging)
    graph.add_node("retry", retry_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "retry": "retry", "end": END})
    graph.add_edge("tools", "agent")
    graph.add_edge("retry", "agent")

    return graph.compile()


# Session memory for multi-turn conversations
_sessions: dict[str, list[BaseMessage]] = {}


async def run_agent(
    user_message: str,
    session_id: str | None = None,
    customer_email: str | None = None,
) -> tuple[str, str, str | None]:
    if not os.getenv("OPENAI_API_KEY"):
        from app.agent.mock import run_mock_agent

        return await run_mock_agent(user_message, session_id, customer_email)

    sid = session_id or str(uuid.uuid4())[:8]
    graph = build_agent_graph(sid)

    await log_broadcaster.emit(
        sid,
        LogLevel.INFO,
        f"New customer message received",
        {"message": user_message, "customer_email": customer_email},
    )

    history = _sessions.get(sid, [])
    if not history and customer_email:
        user_message = f"[Customer email: {customer_email}] {user_message}"

    initial_state: AgentState = {
        "messages": history + [HumanMessage(content=user_message)],
        "session_id": sid,
        "retry_count": 0,
        "refund_decision": None,
    }

    try:
        result = await graph.ainvoke(initial_state)

    except Exception as exc:
        await log_broadcaster.emit(
            sid,
            LogLevel.ERROR,
            f"OpenAI agent failed: {exc}",
            {"error": str(exc)},
        )

        await log_broadcaster.emit(
            sid,
            LogLevel.RETRY,
            "Falling back to deterministic mock agent",
        )

        from app.agent.mock import run_mock_agent

        return await run_mock_agent(
            user_message=user_message,
            session_id=sid,
            customer_email=customer_email,
        )
    _sessions[sid] = result["messages"]

    last_ai = next(
        (m for m in reversed(result["messages"]) if isinstance(m, AIMessage) and m.content),
        None,
    )
    response_text = ""
    if last_ai:
        content = last_ai.content
        response_text = content if isinstance(content, str) else str(content)

    await log_broadcaster.emit(
        sid,
        LogLevel.INFO,
        "Agent response sent to customer",
        {"response_preview": response_text[:200]},
    )

    return sid, response_text, result.get("refund_decision")
