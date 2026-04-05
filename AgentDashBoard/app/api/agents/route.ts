import { NextResponse } from 'next/server'
import { loadAllAgents } from '@/lib/agents'

export function GET() {
  const agents = loadAllAgents().map(({ content: _c, ...meta }) => meta)
  return NextResponse.json(agents)
}
