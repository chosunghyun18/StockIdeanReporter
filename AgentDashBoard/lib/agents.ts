import fs from 'fs'
import path from 'path'

const BASE_DIR = path.resolve(process.cwd(), '..')
export const AGENTS_DIR = path.resolve(BASE_DIR, 'agents')
export const PIPELINES_FILE = path.resolve(BASE_DIR, 'config', 'pipelines.json')
export const SESSIONS_FILE = path.resolve(BASE_DIR, 'output', 'sessions.jsonl')

export interface AgentMeta {
  slug: string
  name: string
  description: string
  model: string
  type: AgentType
  calls: string[]
  inputs: string[]
  outputs: string[]
}

export interface Agent extends AgentMeta {
  content: string
}

export type AgentType =
  | 'orchestrator'
  | 'analyst'
  | 'reviewer'
  | 'etf'
  | 'reporter'
  | 'builder'
  | 'other'

export function parseFrontmatter(content: string): Record<string, string | string[]> {
  const meta: Record<string, string | string[]> = {}
  const m = content.match(/^---\n([\s\S]*?)\n---/)
  if (!m) return meta

  for (const line of m[1].split('\n')) {
    if (!line.includes(':')) continue
    const colonIdx = line.indexOf(':')
    const key = line.slice(0, colonIdx).trim()
    const raw = line.slice(colonIdx + 1).trim().replace(/^"|"$/g, '')

    if (raw.startsWith('[') && raw.endsWith(']')) {
      meta[key] = raw
        .slice(1, -1)
        .split(',')
        .map((x) => x.trim().replace(/^['"]|['"]$/g, ''))
        .filter(Boolean)
    } else {
      meta[key] = raw
    }
  }
  return meta
}

export function agentType(name: string): AgentType {
  const n = name.toLowerCase()
  if (n.includes('orchestrator') || n.endsWith('-manager')) return 'orchestrator'
  if (n.includes('analyst')) return 'analyst'
  if (n.includes('reviewer')) return 'reviewer'
  if (n.includes('etf')) return 'etf'
  if (n.includes('reporter') || n.includes('writer')) return 'reporter'
  if (n.includes('resolver') || n.includes('builder')) return 'builder'
  return 'other'
}

export function loadAgent(slug: string): Agent | null {
  const filePath = path.join(AGENTS_DIR, `${slug}.md`)
  if (!fs.existsSync(filePath)) return null

  const content = fs.readFileSync(filePath, 'utf-8')
  const meta = parseFrontmatter(content)
  const name = (meta.name as string) || slug

  return {
    slug,
    name,
    description: (meta.description as string) || '',
    model: (meta.model as string) || '',
    type: agentType(name),
    calls: (meta.calls as string[]) || [],
    inputs: (meta.inputs as string[]) || [],
    outputs: (meta.outputs as string[]) || [],
    content,
  }
}

export function loadAllAgents(): Agent[] {
  if (!fs.existsSync(AGENTS_DIR)) return []

  return fs
    .readdirSync(AGENTS_DIR)
    .filter((f) => f.endsWith('.md'))
    .sort()
    .map((f) => loadAgent(f.replace('.md', '')))
    .filter((a): a is Agent => a !== null)
}

export function loadPipelines(): unknown[] {
  if (!fs.existsSync(PIPELINES_FILE)) return []
  const data = JSON.parse(fs.readFileSync(PIPELINES_FILE, 'utf-8'))
  return data.pipelines ?? []
}

export interface Session {
  session_id: string
  timestamp: string
  prompt: string
  agents: string[]
}

export function loadSessions(): Session[] {
  if (!fs.existsSync(SESSIONS_FILE)) return []

  const merged = new Map<string, Session>()
  const lines = fs.readFileSync(SESSIONS_FILE, 'utf-8').split('\n')

  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed) continue
    try {
      const entry = JSON.parse(trimmed)
      const sid: string = entry.session_id || ''
      if (!merged.has(sid)) {
        merged.set(sid, {
          session_id: sid,
          timestamp: entry.timestamp || '',
          prompt: entry.prompt || '',
          agents: [...(entry.agents || [])],
        })
      } else {
        const existing = merged.get(sid)!
        const agentSet = new Set([...existing.agents, ...(entry.agents || [])])
        existing.agents = Array.from(agentSet)
        if ((entry.timestamp || '') > existing.timestamp) {
          existing.timestamp = entry.timestamp
        }
      }
    } catch {
      // skip malformed lines
    }
  }

  return Array.from(merged.values()).sort((a, b) =>
    b.timestamp.localeCompare(a.timestamp)
  )
}
