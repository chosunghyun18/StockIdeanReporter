import Header from '@/components/Header'
import AgentViewer from '@/components/AgentViewer'

export default function Home() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <Header />
      <AgentViewer />
    </div>
  )
}
