'use client'

import { useEffect, useState } from 'react'
import styles from './SessionsView.module.css'

type AgentType = 'orchestrator' | 'analyst' | 'reviewer' | 'etf' | 'reporter' | 'builder' | 'other'

interface AgentMeta {
  slug: string
  name: string
  description: string
  type: AgentType
}

interface Session {
  session_id: string
  timestamp: string
  prompt: string
  agents: string[]
}

const TYPE_COLOR: Record<AgentType, string> = {
  orchestrator: '#f59e0b',
  analyst:      '#3b82f6',
  reviewer:     '#10b981',
  etf:          '#06b6d4',
  reporter:     '#a78bfa',
  builder:      '#f97316',
  other:        '#4b5563',
}

function formatTime(ts: string): string {
  if (!ts) return ''
  try {
    return new Date(ts).toLocaleString('ko-KR', {
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit',
    })
  } catch {
    return ts
  }
}

export default function SessionsView() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [agents, setAgents] = useState<Map<string, AgentMeta>>(new Map())
  const [selected, setSelected] = useState<Session | null>(null)

  useEffect(() => {
    Promise.all([
      fetch('/api/sessions').then((r) => r.json()),
      fetch('/api/agents').then((r) => r.json()),
    ]).then(([sessionData, agentData]: [Session[], AgentMeta[]]) => {
      setSessions(sessionData)
      setAgents(new Map(agentData.map((a) => [a.slug, a])))
      if (sessionData.length) setSelected(sessionData[0])
    })
  }, [])

  const activeAgentSlugs = new Set(selected?.agents ?? [])

  return (
    <div className={styles.body}>
      {/* ── Session List ── */}
      <aside className={styles.sessionList}>
        <div className={styles.listHeader}>
          <div className={styles.listTitle}>요청 히스토리</div>
          <div className={styles.listHint}>{sessions.length}건</div>
        </div>
        <div className={styles.listScroll}>
          {sessions.length === 0 ? (
            <div className={styles.emptyState}>
              <div className={styles.emptyIcon}>📭</div>
              <div>아직 기록이 없습니다</div>
            </div>
          ) : (
            sessions.map((s) => (
              <div
                key={s.session_id}
                className={`${styles.sessionItem} ${selected?.session_id === s.session_id ? styles.active : ''}`}
                onClick={() => setSelected(s)}
              >
                <div className={styles.siTime}>{formatTime(s.timestamp)}</div>
                <div className={styles.siPrompt}>{s.prompt || '(프롬프트 없음)'}</div>
                <div className={styles.siAgents}>
                  {s.agents.slice(0, 10).map((slug) => {
                    const agent = agents.get(slug)
                    const color = agent ? TYPE_COLOR[agent.type] : '#4b5563'
                    return (
                      <span
                        key={slug}
                        className={styles.siAgentDot}
                        style={{ background: color }}
                        title={agent?.name ?? slug}
                      />
                    )
                  })}
                </div>
              </div>
            ))
          )}
        </div>
      </aside>

      {/* ── Right Panel ── */}
      <div className={styles.rightPanel}>
        {!selected ? (
          <div className={styles.selectHint}>
            <div className={styles.selectHintIcon}>🕐</div>
            <div className={styles.selectHintText}>
              좌측 목록에서 요청을 선택하면<br />에이전트 실행 현황을 볼 수 있습니다
            </div>
          </div>
        ) : (
          <>
            <div className={styles.detailHeader}>
              <div className={styles.detailPromptIcon}>💬</div>
              <div className={styles.detailPromptWrap}>
                <div className={styles.detailPromptLabel}>요청 내용</div>
                <div className={styles.detailPromptText}>{selected.prompt || '(없음)'}</div>
                <div className={styles.detailTime}>{formatTime(selected.timestamp)}</div>
              </div>
            </div>

            <div className={styles.agentCanvas}>
              <div className={styles.pipelineGroup}>
                <div className={styles.pipelineGroupLabel}>실행된 에이전트</div>
                <div className={styles.agentRow}>
                  {Array.from(agents.values()).map((agent) => {
                    const isActive = activeAgentSlugs.has(agent.slug)
                    const color = TYPE_COLOR[agent.type] ?? '#4b5563'
                    return (
                      <div
                        key={agent.slug}
                        className={`${styles.agentCard} ${isActive ? styles.agentCardActive : ''}`}
                        style={{ '--card-color': color } as React.CSSProperties}
                      >
                        <div className={styles.acBadge}>실행됨</div>
                        <div className={styles.acName}>{agent.name}</div>
                        <div className={styles.acDesc}>{agent.description}</div>
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
