import { NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'
import { AGENTS_DIR } from '@/lib/agents'

export async function PUT(
  req: Request,
  { params }: { params: Promise<{ slug: string }> }
) {
  const { slug } = await params
  const filePath = path.join(AGENTS_DIR, `${slug}.md`)
  if (!fs.existsSync(filePath)) {
    return NextResponse.json({ error: 'Agent not found' }, { status: 404 })
  }

  const { content }: { content: string } = await req.json()
  fs.writeFileSync(filePath, content, 'utf-8')
  return NextResponse.json({ saved: true })
}
