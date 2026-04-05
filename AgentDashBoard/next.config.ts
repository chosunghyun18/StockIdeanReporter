import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  // agents/ 디렉토리 경로를 환경변수로 전달
  env: {
    AGENTS_DIR: process.env.AGENTS_DIR || '../agents',
    PIPELINES_FILE: process.env.PIPELINES_FILE || '../config/pipelines.json',
    SESSIONS_FILE: process.env.SESSIONS_FILE || '../output/sessions.jsonl',
  },
}

export default nextConfig
