import { NextResponse } from 'next/server'
import { loadAllAgents, loadPipelines } from '@/lib/agents'

export function GET() {
  const agents = loadAllAgents()
  const pipelines = loadPipelines()

  const agentMap = new Map(agents.map((a) => [a.slug, a]))

  const edges = agents.flatMap((src) =>
    src.calls
      .filter((tgt) => agentMap.has(tgt))
      .map((tgt) => ({ source: src.slug, target: tgt, parallel: false }))
  )

  const nodes = agents.map(({ content: _c, ...meta }) => meta)

  return NextResponse.json({ nodes, edges, pipelines })
}
