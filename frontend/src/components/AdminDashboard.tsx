import { useEffect, useRef, useState } from 'react'
import type { AgentLogEntry } from '../api'

interface Props {
  logs: AgentLogEntry[]
}

const LEVELS = ['all', 'tool', 'reasoning', 'success', 'denial', 'retry', 'error'] as const

export default function AdminDashboard({ logs }: Props) {
  const [filter, setFilter] = useState<string>('all')
  const bottomRef = useRef<HTMLDivElement>(null)

  const filtered = filter === 'all' ? logs : logs.filter((l) => l.level === filter)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs.length])

  return (
    <div className="panel">
      <div className="panel-header">
        Admin — Agent Reasoning Logs
        <span className="dot" title="Live connected" />
      </div>
      <div className="log-filters">
        {LEVELS.map((level) => (
          <button
            key={level}
            className={filter === level ? 'active' : ''}
            onClick={() => setFilter(level)}
          >
            {level}
          </button>
        ))}
      </div>
      <div className="log-list">
        {filtered.length === 0 ? (
          <div className="empty-state">
            Waiting for agent activity…<br />
            Send a message in the customer chat to see live reasoning.
          </div>
        ) : (
          filtered.map((log) => (
            <LogEntry key={log.id} log={log} />
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}

function LogEntry({ log }: { log: AgentLogEntry }) {
  const [expanded, setExpanded] = useState(false)
  const hasMeta = Object.keys(log.metadata).length > 0

  return (
    <div className={`log-entry ${log.level}`} onClick={() => hasMeta && setExpanded(!expanded)}>
      <div className="log-meta">
        <span className="log-level">{log.level}</span>
        <span>{new Date(log.timestamp).toLocaleTimeString()}</span>
        <span>session:{log.session_id}</span>
      </div>
      <div className="log-message">{log.message}</div>
      {expanded && hasMeta && (
        <pre className="log-detail">{JSON.stringify(log.metadata, null, 2)}</pre>
      )}
    </div>
  )
}
