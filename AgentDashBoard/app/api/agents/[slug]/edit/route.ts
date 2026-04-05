import { NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'
import Anthropic from '@anthropic-ai/sdk'
import { AGENTS_DIR } from '@/lib/agents'

interface EditRequest {
  instruction: string
  preview?: boolean
}

export async function POST(
  req: Request,
  { params }: { params: Promise<{ slug: string }> }
) {
  const { slug } = await params
  const filePath = path.join(AGENTS_DIR, `${slug}.md`)
  if (!fs.existsSync(filePath)) {
    return NextResponse.json({ error: 'Agent not found' }, { status: 404 })
  }

  const apiKey = process.env.ANTHROPIC_API_KEY
  if (!apiKey) {
    return NextResponse.json({ error: 'ANTHROPIC_API_KEY 환경변수가 없습니다' }, { status: 500 })
  }

  const { instruction, preview = false }: EditRequest = await req.json()
  if (!instruction?.trim()) {
    return NextResponse.json({ error: '수정 지시를 입력하세요' }, { status: 400 })
  }

  const original = fs.readFileSync(filePath, 'utf-8')

  const client = new Anthropic({ apiKey })
  const msg = await client.messages.create({
    model: 'claude-sonnet-4-6',
    max_tokens: 4096,
    system: [
      '당신은 Claude Code 에이전트 파일(.md) 편집 전문가입니다.',
      '사용자의 수정 지시에 따라 에이전트 파일을 수정하세요.',
      '',
      '규칙:',
      '1. YAML frontmatter는 필요한 경우만 수정',
      '2. frontmatter의 calls/inputs/outputs 필드는 배열 형식 유지: [a, b, c]',
      '3. 수정하지 않은 부분은 그대로 유지',
      '4. 응답은 수정된 전체 파일 내용만 출력 (설명 없이, 코드블록 없이)',
      '5. 한국어 주석/설명 유지',
    ].join('\n'),
    messages: [
      {
        role: 'user',
        content: `## 수정 지시\n${instruction}\n\n## 현재 파일\n${original}`,
      },
    ],
  })

  const newContent = (msg.content[0] as { text: string }).text.trim()

  if (!preview) {
    fs.writeFileSync(filePath, newContent, 'utf-8')
  }

  return NextResponse.json({ slug, content: newContent, saved: !preview })
}
