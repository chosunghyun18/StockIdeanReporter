'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import styles from './Header.module.css'

interface HeaderProps {
  badge?: string
}

export default function Header({ badge }: HeaderProps) {
  const pathname = usePathname()

  return (
    <header className={styles.header}>
      <div className={styles.logo}>
        Agent <span>Viewer</span>
      </div>
      <Link href="/" className={`${styles.navLink} ${pathname === '/' ? styles.active : ''}`}>
        에이전트 목록
      </Link>
      <Link href="/graph" className={`${styles.navLink} ${pathname === '/graph' ? styles.active : ''}`}>
        플로우 맵
      </Link>
      <Link href="/sessions" className={`${styles.navLink} ${pathname === '/sessions' ? styles.active : ''}`}>
        요청 히스토리
      </Link>
      {badge && <div className={styles.badge}>{badge}</div>}
    </header>
  )
}
