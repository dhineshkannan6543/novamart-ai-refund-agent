import { useEffect, useState } from 'react'
import ChatPanel from './components/ChatPanel'
import AdminDashboard from './components/AdminDashboard'
import { connectLogStream, type AgentLogEntry } from './api'

export default function App() {
  const [logs, setLogs] = useState<AgentLogEntry[]>([])
  const [activeTab, setActiveTab] = useState<'split' | 'chat' | 'admin'>('split')
  const [, setSessionId] = useState<string | null>(null)

  useEffect(() => {
    const ws = connectLogStream((entry) => {
      setLogs((prev) => {
        if (prev.some((l) => l.id === entry.id)) return prev
        return [...prev, entry]
      })
    })
    return () => ws.close()
  }, [])

  return (
    <>
      <header className="app-header">
        <h1>
          <span>NovaMart</span> AI Refund Agent
        </h1>
        <span className="header-badge">LangGraph · OpenAI · WebSocket Logs</span>
      </header>

      <nav className="tab-bar">
        <button className={activeTab === 'split' ? 'active' : ''} onClick={() => setActiveTab('split')}>
          Split View
        </button>
        <button className={activeTab === 'chat' ? 'active' : ''} onClick={() => setActiveTab('chat')}>
          Customer Chat
        </button>
        <button className={activeTab === 'admin' ? 'active' : ''} onClick={() => setActiveTab('admin')}>
          Admin Logs
        </button>
      </nav>

      <div className="main-layout">
        {(activeTab === 'split' || activeTab === 'chat') && (
          <ChatPanel onSessionChange={setSessionId} />
        )}
        {(activeTab === 'split' || activeTab === 'admin') && (
          <AdminDashboard logs={logs} />
        )}
      </div>

      <div className="demo-guide">
        <strong>Loom demo script:</strong>{' '}
        Standard refund → select <code>Michael Brown</code>, quick prompt "Standard refund" (<code>ORD-10012</code>, $22 apparel).{' '}
        Policy violation → <code>Robert Taylor</code> + "Final sale denial" (<code>ORD-10008</code>).{' '}
        Voice → click 🎤 and speak your request. Watch admin panel for tool calls, denials, and retries.
      </div>
    </>
  )
}
