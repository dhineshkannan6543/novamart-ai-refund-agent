import { useCallback, useEffect, useRef, useState } from 'react'
import { sendChat, sendVoice, fetchCustomers, type ChatMessage, type Customer } from '../api'

interface Props {
  onSessionChange: (sessionId: string) => void
}

const QUICK_PROMPTS = [
  { label: 'Standard refund', text: 'Hi, I\'d like a refund for order ORD-10012. The shirt doesn\'t fit and I haven\'t worn it — tags are still on.' },
  { label: 'Final sale denial', text: 'I need a refund for order ORD-10008. I bought the clearance jacket but changed my mind. Please process it today.' },
  { label: 'Abuse flag denial', text: 'Refund order ORD-10005 please. The speaker is fine, I just don\'t want it anymore.' },
  { label: 'High-value escalation', text: 'I want to return order ORD-10011, the webcam is still sealed in the box.' },
]

export default function ChatPanel({ onSessionChange }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [customers, setCustomers] = useState<Customer[]>([])
  const [selectedEmail, setSelectedEmail] = useState('')
  const [listening, setListening] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const recognitionRef = useRef<SpeechRecognition | null>(null)

  useEffect(() => {
    fetchCustomers().then(setCustomers).catch(console.error)
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const submitMessage = useCallback(async (text: string, viaVoice = false) => {
    if (!text.trim() || loading) return
    setMessages((prev) => [...prev, { role: 'user', content: text }])
    setInput('')
    setLoading(true)

    try {
      const fn = viaVoice ? sendVoice : sendChat
      const res = await fn(text, sessionId, selectedEmail || null)
      if (!sessionId) {
        setSessionId(res.session_id)
        onSessionChange(res.session_id)
      }
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: res.message, decision: res.refund_decision },
      ])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Error: ${err instanceof Error ? err.message : 'Unknown error'}` },
      ])
    } finally {
      setLoading(false)
    }
  }, [loading, sessionId, selectedEmail, onSessionChange])

  const toggleVoice = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) {
      alert('Speech recognition is not supported in this browser. Try Chrome.')
      return
    }

    if (listening && recognitionRef.current) {
      recognitionRef.current.stop()
      setListening(false)
      return
    }

    const recognition = new SpeechRecognition()
    recognition.continuous = false
    recognition.interimResults = false
    recognition.lang = 'en-US'

    recognition.onstart = () => setListening(true)
    recognition.onend = () => setListening(false)
    recognition.onerror = () => setListening(false)
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript
      submitMessage(transcript, true)
    }

    recognitionRef.current = recognition
    recognition.start()
  }

  return (
    <div className="panel">
      <div className="panel-header">Customer Support Chat</div>
      <div className="customer-setup">
        <label htmlFor="customer-select">Act as:</label>
        <select
          id="customer-select"
          value={selectedEmail}
          onChange={(e) => setSelectedEmail(e.target.value)}
        >
          <option value="">— Select demo customer —</option>
          {customers.map((c) => (
            <option key={c.customer_id} value={c.email}>
              {c.name} ({c.email}) — {c.loyalty_tier}
            </option>
          ))}
        </select>
      </div>
      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="empty-state">
            Welcome to NovaMart Support.<br />
            Select a customer and ask about a refund, or use a quick prompt below.
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            {msg.content}
            {msg.decision && (
              <div className={`decision-badge ${msg.decision}`}>
                {msg.decision}
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="typing-indicator">
            <span /><span /><span />
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <div className="quick-prompts">
        {QUICK_PROMPTS.map((p) => (
          <button key={p.label} onClick={() => submitMessage(p.text)} disabled={loading}>
            {p.label}
          </button>
        ))}
      </div>
      <div className="chat-input-area">
        <button
          className={`btn-voice ${listening ? 'listening' : ''}`}
          onClick={toggleVoice}
          title="Voice input (Web Speech API)"
          disabled={loading}
        >
          🎤
        </button>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              submitMessage(input)
            }
          }}
          placeholder="Describe your refund request…"
          rows={1}
          disabled={loading}
        />
        <button
          className="btn btn-primary"
          onClick={() => submitMessage(input)}
          disabled={loading || !input.trim()}
        >
          Send
        </button>
      </div>
    </div>
  )
}

// Web Speech API types
interface SpeechRecognition extends EventTarget {
  continuous: boolean
  interimResults: boolean
  lang: string
  start(): void
  stop(): void
  onstart: ((ev: Event) => void) | null
  onend: ((ev: Event) => void) | null
  onerror: ((ev: Event) => void) | null
  onresult: ((ev: SpeechRecognitionEvent) => void) | null
}

interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList
}

declare global {
  interface Window {
    SpeechRecognition: new () => SpeechRecognition
    webkitSpeechRecognition: new () => SpeechRecognition
  }
}
