import { NextResponse } from 'next/server'
import { loadSessions } from '@/lib/agents'

export function GET() {
  return NextResponse.json(loadSessions())
}
