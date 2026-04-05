import Header from '@/components/Header'
import SessionsView from '@/components/SessionsView'

export default function SessionsPage() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <Header />
      <SessionsView />
    </div>
  )
}
