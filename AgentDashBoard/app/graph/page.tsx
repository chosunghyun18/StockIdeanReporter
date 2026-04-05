import Header from '@/components/Header'
import GraphView from '@/components/GraphView'

export default function GraphPage() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <Header />
      <GraphView />
    </div>
  )
}
