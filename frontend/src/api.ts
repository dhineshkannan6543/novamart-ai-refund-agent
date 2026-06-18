export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  decision?: string | null
}

export interface AgentLogEntry {
  id: string
  session_id: string
  timestamp: string
  level: 'info' | 'tool' | 'reasoning' | 'success' | 'error' | 'retry' | 'denial'
  message: string
  metadata: Record<string, unknown>
}

export interface Customer {
  customer_id: string
  name: string
  email: string
  loyalty_tier: string
  orders: number
}

const API = '/api'

export async function sendChat(
  message: string,
  sessionId: string | null,
  customerEmail: string | null,
): Promise<{ session_id: string; message: string; refund_decision: string | null }> {
  const res = await fetch(`${API}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId, customer_email: customerEmail }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function sendVoice(
  transcript: string,
  sessionId: string | null,
  customerEmail: string | null,
): Promise<{ session_id: string; message: string; refund_decision: string | null }> {
  const res = await fetch(`${API}/voice`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ transcript, session_id: sessionId, customer_email: customerEmail }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function fetchCustomers(): Promise<Customer[]> {
  const res = await fetch(`${API}/customers`)
  const data = await res.json()
  return data.customers
}

export function connectLogStream(onLog: (entry: AgentLogEntry) => void): WebSocket {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const ws = new WebSocket(`${protocol}//${window.location.host}/ws/logs`)
  ws.onmessage = (event) => {
    onLog(JSON.parse(event.data))
  }
  return ws
}
