'use client'

import { useState, useEffect, useCallback } from 'react'
import styles from './AgentViewer.module.css'

type AgentType = 'orchestrator' | 'analyst' | 'reviewer' | 'etf' | 'reporter' | 'builder' | 'other'

interface AgentMeta {
  slug: string
  name: string
  description: string
  model: string
  type: AgentType
}

interface Agent extends AgentMeta {
  content: string
}

const TYPE_LABELS: Record<AgentType, string> = {
  orchestrator: '오케스트레이터',
  analyst: '분석가',
  reviewer: '리뷰어',
  etf: 'ETF',
  reporter: '리포터',
  builder: '빌더',
  other: '기타',
}

const FILTERS: { key: string; label: string }[] = [
  { key: 'all', label: '전체' },
  { key: 'orchestrator', label: '오케스트레이터' },
  { key: 'analyst', label: '분석가' },
  { key: 'etf', label: 'ETF' },
  { key: 'reviewer', label: '리뷰어' },
  { key: 'reporter', label: '리포터' },
  { key: 'builder', label: '빌더' },
  { key: 'other', label: '기타' },
]

// ── Markdown highlighter ──────────────────────────────────────────────────────
function esc(s: string) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function highlight(text: string): string {
  return text
    .split('\n')
    .map((line) => {
      if (line.startsWith('---')) return `<span class="${styles.yaml}">${esc(line)}</span>`
      if (/^(name|description|tools|model|calls|inputs|outputs):/.test(line))
        return `<span class="${styles.yaml}">${esc(line)}</span>`
      if (line.startsWith('# '))  return `<span class="${styles.h1}">${esc(line)}</span>`
      if (line.startsWith('## ')) return `<span class="${styles.h2}">${esc(line)}</span>`
      if (line.startsWith('### ')) return `<span class="${styles.h3}">${esc(line)}</span>`
      let l = esc(line)
      l = l.replace(/`([^`]+)`/g, `<span class="${styles.code}">$1</span>`)
      l = l.replace(/\*\*([^*]+)\*\*/g, `<span class="${styles.bold}">$1</span>`)
      return l
    })
    .join('\n')
}

// ── Toast ─────────────────────────────────────────────────────────────────────
function useToast() {
  const [toasts, setToasts] = useState<{ id: number; msg: string; type: 'success' | 'error' }[]>([])

  const showToast = useCallback((msg: string, type: 'success' | 'error' = 'success') => {
    const id = Date.now()
    setToasts((prev) => [...prev, { id, msg, type }])
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 2800)
  }, [])

  return { toasts, showToast }
}

// ── Main Component ─────────────────────────────────────────────────────────────
export default function AgentViewer() {
  const [agents, setAgents] = useState<AgentMeta[]>([])
  const [current, setCurrent] = useState<Agent | null>(null)
  const [pendingContent, setPendingContent] = useState<string | null>(null)
  const [activeFilter, setActiveFilter] = useState('all')
  const [query, setQuery] = useState('')
  const [instruction, setInstruction] = useState('')
  const [loading, setLoading] = useState<'preview' | 'apply' | null>(null)
  const { toasts, showToast } = useToast()

  useEffect(() => {
    fetch('/api/agents')
      .then((r) => r.json())
      .then(setAgents)
      .catch(() => showToast('에이전트 로딩 실패', 'error'))
  }, [showToast])

  const filteredAgents = agents.filter((a) => {
    const matchType = activeFilter === 'all' || a.type === activeFilter
    const q = query.toLowerCase()
    const matchQ = !q || a.name.toLowerCase().includes(q) || a.description.toLowerCase().includes(q)
    return matchType && matchQ
  })

  async function selectAgent(slug: string) {
    setPendingContent(null)
    const res = await fetch(`/api/agents/${slug}`)
    if (!res.ok) { showToast('에이전트 로딩 실패', 'error'); return }
    const data: Agent = await res.json()
    setCurrent(data)
    setInstruction('')
  }

  async function runEdit(preview: boolean) {
    if (!instruction.trim()) { showToast('수정 내용을 입력하세요', 'error'); return }
    if (!current) { showToast('에이전트를 먼저 선택하세요', 'error'); return }

    setLoading(preview ? 'preview' : 'apply')
    try {
      const res = await fetch(`/api/agents/${current.slug}/edit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instruction, preview }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error || '서버 오류')
      }
      const data = await res.json()

      if (preview) {
        setPendingContent(data.content)
        showToast('미리보기 생성 완료')
      } else {
        setCurrent((prev) => prev ? { ...prev, content: data.content } : prev)
        setPendingContent(null)
        setInstruction('')
        showToast('저장 완료 ✓')
      }
    } catch (e) {
      showToast((e as Error).message, 'error')
    } finally {
      setLoading(null)
    }
  }

  async function savePending() {
    if (!pendingContent || !current) return
    const res = await fetch(`/api/agents/${current.slug}/content`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: pendingContent }),
    })
    if (res.ok) {
      setCurrent((prev) => prev ? { ...prev, content: pendingContent } : prev)
      setPendingContent(null)
      setInstruction('')
      showToast('저장 완료 ✓')
    } else {
      showToast('저장 실패', 'error')
    }
  }

  return (
    <div className={styles.app}>
      {/* Toasts */}
      <div className={styles.toastContainer}>
        {toasts.map((t) => (
          <div key={t.id} className={`${styles.toast} ${t.type === 'error' ? styles.toastError : styles.toastSuccess}`}>
            {t.msg}
          </div>
        ))}
      </div>

      {/* Sidebar */}
      <aside className={styles.sidebar}>
        <div className={styles.sidebarSearch}>
          <input
            type="text"
            placeholder="에이전트 검색…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <div className={styles.sidebarFilters}>
          {FILTERS.map((f) => (
            <button
              key={f.key}
              className={`${styles.filterBtn} ${activeFilter === f.key ? styles.active : ''}`}
              onClick={() => setActiveFilter(f.key)}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className={styles.agentList}>
          {filteredAgents.length === 0 ? (
            <div className={styles.emptyList}>검색 결과 없음</div>
          ) : (
            filteredAgents.map((a) => (
              <div
                key={a.slug}
                className={`${styles.agentCard} ${current?.slug === a.slug ? styles.agentCardActive : ''}`}
                onClick={() => selectAgent(a.slug)}
              >
                <div className={styles.agentCardTop}>
                  <div className={`${styles.typeDot} ${styles[`dot_${a.type}`]}`} />
                  <div className={styles.agentName}>{a.name}</div>
                  {a.model && <div className={styles.modelBadge}>{a.model}</div>}
                </div>
                <div className={styles.agentDesc}>{a.description}</div>
              </div>
            ))
          )}
        </div>
      </aside>

      {/* Main */}
      <main className={styles.main}>
        {/* Main Header */}
        {current && (
          <div className={styles.mainHeader}>
            <div className={styles.mainTitle}>{current.name}</div>
            <div className={`${styles.typeBadge} ${styles[`badge_${current.type}`]}`}>
              {TYPE_LABELS[current.type]}
            </div>
            <div className={styles.mainActions}>
              {pendingContent && (
                <>
                  <button className={`${styles.btn} ${styles.btnGhost}`} onClick={() => setPendingContent(null)}>
                    변경 취소
                  </button>
                  <button className={`${styles.btn} ${styles.btnSuccess}`} onClick={savePending}>
                    저장
                  </button>
                </>
              )}
            </div>
          </div>
        )}

        {/* Content */}
        <div className={`${styles.contentArea} ${pendingContent ? styles.hasDiff : ''}`}>
          {!current ? (
            <div className={styles.emptyState}>
              <div className={styles.emptyIcon}>🤖</div>
              <div className={styles.emptyText}>에이전트를 선택하세요</div>
              <div className={styles.emptyHint}>좌측 목록에서 에이전트를 클릭하면 내용을 볼 수 있습니다</div>
            </div>
          ) : (
            <>
              <div className={styles.editorPane}>
                <div className={styles.paneLabel}>현재 파일</div>
                <div
                  className={styles.editorContent}
                  dangerouslySetInnerHTML={{ __html: highlight(current.content) }}
                />
              </div>
              {pendingContent && (
                <div className={`${styles.editorPane} ${styles.diffPane}`}>
                  <div className={styles.paneLabel}>
                    수정 미리보기
                    <span className={styles.saveIndicator}>↑ 저장 버튼으로 적용</span>
                  </div>
                  <div
                    className={styles.editorContent}
                    dangerouslySetInnerHTML={{ __html: highlight(pendingContent) }}
                  />
                </div>
              )}
            </>
          )}
        </div>

        {/* Edit Bar */}
        {current && (
          <div className={styles.editBar}>
            <div className={styles.editBarInner}>
              <div className={styles.editBarLabel}>수정 지시 → Claude가 파일을 직접 수정합니다</div>
              <textarea
                className={styles.editInput}
                placeholder="예: 롱 확률 계산 가중치를 기술적 50%, 펀더멘털 30%, 시장바이어스 20%로 변경해줘"
                rows={2}
                value={instruction}
                onChange={(e) => setInstruction(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                    e.preventDefault()
                    runEdit(false)
                  }
                }}
              />
            </div>
            <div className={styles.editActions}>
              <button
                className={`${styles.btn} ${styles.btnGhost}`}
                disabled={loading !== null}
                onClick={() => runEdit(true)}
              >
                {loading === 'preview' ? <span className={styles.spinner} /> : '미리보기'}
              </button>
              <button
                className={`${styles.btn} ${styles.btnPrimary}`}
                disabled={loading !== null}
                onClick={() => runEdit(false)}
              >
                {loading === 'apply' ? <span className={styles.spinner} /> : '적용 및 저장'}
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
