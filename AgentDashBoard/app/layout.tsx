import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Agent Viewer',
  description: '투자 분석 에이전트 대시보드',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  )
}
