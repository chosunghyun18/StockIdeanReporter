import { NextResponse } from 'next/server'
import { loadPipelines } from '@/lib/agents'

export function GET() {
  return NextResponse.json(loadPipelines())
}
