import { NextResponse } from 'next/server'
import { loadAgent } from '@/lib/agents'

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ slug: string }> }
) {
  const { slug } = await params
  const agent = loadAgent(slug)
  if (!agent) return NextResponse.json({ error: 'Not found' }, { status: 404 })
  return NextResponse.json(agent)
}
