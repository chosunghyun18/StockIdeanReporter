#!/usr/bin/env node
/**
 * session-tracker.js — Stop 훅
 * Claude Code 응답 완료 시 실행.
 * 마지막 사용자 프롬프트와 호출된 에이전트를 output/sessions.jsonl 에 저장.
 */
const fs   = require('fs')
const path = require('path')

const KNOWN_AGENTS = [
  'orchestrator', 'market-bias-analyst', 'industry-analyst', 'price-analyst',
  'idea-generator', 'etf-manager', 'leveraged-etf-analyst', 'thematic-etf-analyst',
  'etf-launch-monitor', 'reporter', 'stock-screener', 'peer-analyst',
  'it-orchestrator', 'tech-explorer', 'tech-researcher', 'service-designer',
  'service-builder', 'qa-engineer', 'security-dev',
  'planner', 'code-reviewer', 'security-reviewer', 'python-reviewer',
  'architect', 'tdd-guide', 'refactor-cleaner',
]

let raw = ''
process.stdin.on('data', chunk => { raw += chunk })
process.stdin.on('end', () => {
  try {
    const data = JSON.parse(raw)
    const transcript = data.transcript || []
    const sessionId  = data.session_id || String(Date.now())

    // ── Extract last user prompt ──────────────────────────────────────────────
    let lastPrompt = ''
    for (const msg of transcript) {
      if (msg.role !== 'user') continue
      const content = msg.content
      if (typeof content === 'string') {
        lastPrompt = content
      } else if (Array.isArray(content)) {
        lastPrompt = content
          .filter(b => b.type === 'text')
          .map(b => b.text)
          .join(' ')
      }
    }
    lastPrompt = lastPrompt.trim().slice(0, 400)
    if (!lastPrompt) return

    // ── Find called agents (only from Agent/Task tool_use blocks) ─────────────
    const calledAgents = new Set()
    for (const msg of transcript) {
      if (msg.role !== 'assistant') continue
      const blocks = Array.isArray(msg.content) ? msg.content : []
      for (const block of blocks) {
        if (block.type !== 'tool_use') continue
        if (block.name !== 'Agent' && block.name !== 'Task') continue

        // Search agent slugs in description + prompt fields
        const searchText = [
          block.input?.description || '',
          block.input?.prompt      || '',
          block.input?.subagent_type || '',
        ].join(' ').toLowerCase()

        for (const agent of KNOWN_AGENTS) {
          if (searchText.includes(agent)) calledAgents.add(agent)
        }
      }

      // Also scan assistant text for explicit agent mentions (e.g. "market-bias-analyst 호출")
      for (const block of blocks) {
        if (block.type !== 'text') continue
        const t = (block.text || '').toLowerCase()
        for (const agent of KNOWN_AGENTS) {
          // Only count if the pattern suggests invocation, not just mention
          if (
            t.includes(agent + ' 호출') ||
            t.includes(agent + ' 실행') ||
            t.includes('invoking ' + agent) ||
            t.includes('calling ' + agent) ||
            t.includes('launch ' + agent)
          ) {
            calledAgents.add(agent)
          }
        }
      }
    }

    // ── Write to sessions.jsonl ───────────────────────────────────────────────
    const logPath = path.join(process.cwd(), 'output', 'sessions.jsonl')
    fs.mkdirSync(path.dirname(logPath), { recursive: true })

    const entry = {
      session_id: sessionId,
      timestamp:  new Date().toISOString(),
      prompt:     lastPrompt,
      agents:     [...calledAgents],
    }
    fs.appendFileSync(logPath, JSON.stringify(entry) + '\n', 'utf8')

  } catch (_) {
    // Silent — never disrupt Claude Code
  }
  process.exit(0)
})
