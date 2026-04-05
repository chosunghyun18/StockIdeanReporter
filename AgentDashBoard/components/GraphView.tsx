'use client'

import { useEffect, useRef, useState } from 'react'
import * as d3 from 'd3'
import styles from './GraphView.module.css'

type AgentType = 'orchestrator' | 'analyst' | 'reviewer' | 'etf' | 'reporter' | 'builder' | 'other'

interface Node {
  slug: string
  name: string
  description: string
  model: string
  type: AgentType
  calls: string[]
  inputs: string[]
  outputs: string[]
}

interface Edge {
  source: string
  target: string
  parallel: boolean
}

interface Pipeline {
  id: string
  name: string
  description?: string
  color?: string
  steps?: string[]
}

interface GraphData {
  nodes: Node[]
  edges: Edge[]
  pipelines: Pipeline[]
}

const TYPE_COLOR: Record<AgentType, string> = {
  orchestrator: '#f59e0b',
  analyst:      '#3b82f6',
  reviewer:     '#10b981',
  etf:          '#06b6d4',
  reporter:     '#a78bfa',
  builder:      '#f97316',
  other:        '#4b5563',
}

const NW = 148, NH = 44

export default function GraphView() {
  const svgRef = useRef<SVGSVGElement>(null)
  const [data, setData] = useState<GraphData | null>(null)
  const [view, setView] = useState<'flow' | 'map'>('flow')
  const [activePid, setActivePid] = useState<string | null>(null)
  const [tooltip, setTooltip] = useState<{ node: Node; x: number; y: number } | null>(null)
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null)
  const rootRef = useRef<d3.Selection<SVGGElement, unknown, null, undefined> | null>(null)

  useEffect(() => {
    fetch('/api/graph')
      .then((r) => r.json())
      .then((g: GraphData) => {
        setData(g)
        if (g.pipelines.length) setActivePid(g.pipelines[0].id)
      })
  }, [])

  // Draw graph whenever data/view/activePid changes
  useEffect(() => {
    if (!data || !svgRef.current) return
    drawGraph()
  }, [data, view, activePid]) // eslint-disable-line react-hooks/exhaustive-deps

  function drawGraph() {
    if (!data || !svgRef.current) return
    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const defs = svg.append('defs')
    const mkArrow = (id: string, color: string) =>
      defs.append('marker')
        .attr('id', id)
        .attr('viewBox', '0 -4 8 8')
        .attr('refX', 8).attr('refY', 0)
        .attr('markerWidth', 5).attr('markerHeight', 5)
        .attr('orient', 'auto')
        .append('path').attr('d', 'M0,-4L8,0L0,4Z').attr('fill', color)

    mkArrow('arr',       '#363a52')
    mkArrow('arr-hi',    '#6c63ff')
    mkArrow('arr-green', '#10b981')

    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.2, 3])
      .on('zoom', (e) => rootRef.current?.attr('transform', e.transform.toString()))

    zoomRef.current = zoom
    svg.call(zoom)

    const root = svg.append('g')
    rootRef.current = root

    if (view === 'flow') {
      drawFlow(root, data, activePid)
    } else {
      drawMap(root, data, svgRef.current, setTooltip)
    }
  }

  function drawFlow(
    root: d3.Selection<SVGGElement, unknown, null, undefined>,
    g: GraphData,
    pid: string | null
  ) {
    if (!svgRef.current) return
    const pipeline = pid ? g.pipelines.find((p) => p.id === pid) : null
    const stepSlugs: string[] = pipeline?.steps ?? []
    const nodes = stepSlugs
      .map((s) => g.nodes.find((n) => n.slug === s))
      .filter((n): n is Node => !!n)

    if (!nodes.length) return

    const W = svgRef.current.clientWidth || 800
    const H = svgRef.current.clientHeight || 600
    const cols = Math.min(nodes.length, 4)
    const gapX = Math.min(200, (W - 80) / cols)
    const gapY = 100
    const startX = W / 2 - ((cols - 1) * gapX) / 2
    const startY = 60

    const pos = new Map<string, { x: number; y: number }>()
    nodes.forEach((n, i) => {
      const col = i % cols
      const row = Math.floor(i / cols)
      pos.set(n.slug, { x: startX + col * gapX, y: startY + row * gapY })
    })

    // edges
    const slugSet = new Set(nodes.map((n) => n.slug))
    g.edges.forEach((e) => {
      const src = typeof e.source === 'string' ? e.source : (e.source as Node).slug
      const tgt = typeof e.target === 'string' ? e.target : (e.target as Node).slug
      if (!slugSet.has(src) || !slugSet.has(tgt)) return
      const s = pos.get(src)!, t = pos.get(tgt)!

      const x1 = s.x + NW / 2, y1 = s.y + NH
      const x2 = t.x + NW / 2, y2 = t.y
      const midY = (y1 + y2) / 2

      root.append('path')
        .attr('d', `M${x1},${y1} C${x1},${midY} ${x2},${midY} ${x2},${y2}`)
        .attr('class', styles.edge)
        .attr('stroke', e.parallel ? '#404060' : '#363a52')
        .attr('stroke-dasharray', e.parallel ? '5 4' : null)
        .attr('marker-end', `url(#arr)`)
    })

    // nodes
    nodes.forEach((n) => {
      const p = pos.get(n.slug)!
      const color = TYPE_COLOR[n.type] || '#4b5563'
      const g2 = root.append('g')
        .attr('transform', `translate(${p.x},${p.y})`)
        .attr('cursor', 'pointer')
        .on('click', (_e, _d) => {
          window.location.href = `/?agent=${n.slug}`
        })

      g2.append('rect')
        .attr('width', NW).attr('height', NH)
        .attr('rx', 8)
        .attr('fill', '#1a1d2e')
        .attr('stroke', color)
        .attr('stroke-width', 1.5)

      g2.append('circle')
        .attr('cx', 12).attr('cy', NH / 2).attr('r', 4)
        .attr('fill', color)

      g2.append('text')
        .attr('x', 24).attr('y', NH / 2 + 4)
        .attr('font-size', 11).attr('fill', '#e2e4f0').attr('font-weight', 600)
        .text(n.name.length > 16 ? n.name.slice(0, 15) + '…' : n.name)

      if (n.model) {
        g2.append('text')
          .attr('x', NW - 4).attr('y', NH / 2 + 4)
          .attr('font-size', 9).attr('fill', '#5a607a')
          .attr('text-anchor', 'end')
          .text(n.model)
      }
    })
  }

  function drawMap(
    root: d3.Selection<SVGGElement, unknown, null, undefined>,
    g: GraphData,
    svgEl: SVGSVGElement,
    onTooltip: (t: { node: Node; x: number; y: number } | null) => void
  ) {
    const W = svgEl.clientWidth || 800
    const H = svgEl.clientHeight || 600

    type SimNode = Node & d3.SimulationNodeDatum & { x: number; y: number }
    const nodeMap = new Map(g.nodes.map((n) => [n.slug, n]))
    const simNodes: SimNode[] = g.nodes.map((n) => ({ ...n, x: W / 2, y: H / 2 }))
    const simEdges = g.edges.map((e) => ({
      ...e,
      source: typeof e.source === 'string' ? e.source : (e.source as Node).slug,
      target: typeof e.target === 'string' ? e.target : (e.target as Node).slug,
    }))

    const sim = d3.forceSimulation<SimNode>(simNodes)
      .force('link', d3.forceLink(simEdges).id((d: unknown) => (d as Node).slug).distance(160))
      .force('charge', d3.forceManyBody().strength(-400))
      .force('center', d3.forceCenter(W / 2, H / 2))
      .force('collision', d3.forceCollide(70))

    const link = root.append('g')
      .selectAll('line')
      .data(simEdges)
      .enter()
      .append('line')
      .attr('stroke', '#363a52')
      .attr('stroke-width', 1.5)
      .attr('marker-end', 'url(#arr)')

    const node = root.append('g')
      .selectAll('g')
      .data(simNodes)
      .enter()
      .append('g')
      .attr('cursor', 'pointer')
      .call(
        d3.drag<SVGGElement, SimNode>()
          .on('start', (e, d) => { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y })
          .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y })
          .on('end', (e, d) => { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null })
      )

    node.on('mousemove', (e, d) => {
      const n = nodeMap.get(d.slug)
      if (n) onTooltip({ node: n, x: e.clientX + 12, y: e.clientY - 12 })
    })
    node.on('mouseleave', () => onTooltip(null))

    node.append('circle')
      .attr('r', 28)
      .attr('fill', (d) => TYPE_COLOR[d.type] + '22')
      .attr('stroke', (d) => TYPE_COLOR[d.type])
      .attr('stroke-width', 1.5)

    node.append('text')
      .attr('text-anchor', 'middle')
      .attr('y', 4)
      .attr('font-size', 9.5)
      .attr('fill', '#e2e4f0')
      .attr('font-weight', 600)
      .text((d) => d.name.length > 14 ? d.name.slice(0, 13) + '…' : d.name)

    sim.on('tick', () => {
      link
        .attr('x1', (d: unknown) => ((d as { source: { x: number } }).source.x))
        .attr('y1', (d: unknown) => ((d as { source: { y: number } }).source.y))
        .attr('x2', (d: unknown) => ((d as { target: { x: number } }).target.x))
        .attr('y2', (d: unknown) => ((d as { target: { y: number } }).target.y))

      node.attr('transform', (d) => `translate(${d.x},${d.y})`)
    })
  }

  function zoomIn() {
    if (!svgRef.current || !zoomRef.current) return
    d3.select(svgRef.current).transition().call(zoomRef.current.scaleBy, 1.3)
  }
  function zoomOut() {
    if (!svgRef.current || !zoomRef.current) return
    d3.select(svgRef.current).transition().call(zoomRef.current.scaleBy, 0.77)
  }
  function resetView() {
    if (!svgRef.current || !zoomRef.current) return
    d3.select(svgRef.current).transition().call(zoomRef.current.transform, d3.zoomIdentity)
  }

  return (
    <div className={styles.body}>
      <aside className={styles.sidebar}>
        <div className={styles.sidebarSection}>
          <div className={styles.sectionLabel}>뷰 모드</div>
          <div className={styles.tabRow}>
            <button className={`${styles.tabBtn} ${view === 'flow' ? styles.active : ''}`} onClick={() => setView('flow')}>파이프라인</button>
            <button className={`${styles.tabBtn} ${view === 'map'  ? styles.active : ''}`} onClick={() => setView('map')}>전체 맵</button>
          </div>
        </div>

        {view === 'flow' && (
          <div className={styles.pipelineList}>
            {data?.pipelines.map((p) => (
              <div
                key={p.id}
                className={`${styles.pItem} ${activePid === p.id ? styles.pItemActive : ''}`}
                onClick={() => setActivePid(p.id)}
              >
                <div className={styles.pItemTop}>
                  <div className={styles.pDot} style={{ background: p.color || '#6c63ff' }} />
                  <div className={styles.pName}>{p.name}</div>
                </div>
                {p.description && <div className={styles.pMeta}>{p.description}</div>}
              </div>
            ))}
          </div>
        )}

        <div className={styles.legend}>
          <div className={styles.sectionLabel} style={{ marginBottom: 7 }}>범례</div>
          {Object.entries(TYPE_COLOR).map(([type, color]) => (
            <div key={type} className={styles.lRow}>
              <div className={styles.lDot} style={{ background: color }} />
              {type === 'orchestrator' ? '오케스트레이터'
               : type === 'analyst'   ? '분석 에이전트'
               : type === 'etf'       ? 'ETF 에이전트'
               : type === 'reporter'  ? '리포터'
               : type === 'reviewer'  ? '리뷰어'
               : type === 'builder'   ? '빌더'
               : '기타'}
            </div>
          ))}
        </div>
      </aside>

      <div className={styles.canvas}>
        <svg ref={svgRef} className={styles.svg} />
        <div className={styles.controls}>
          <button className={styles.ctrl} onClick={zoomIn}  title="확대">+</button>
          <button className={styles.ctrl} onClick={zoomOut} title="축소">−</button>
          <button className={styles.ctrl} onClick={resetView} title="초기화">⊙</button>
        </div>
      </div>

      {tooltip && (
        <div
          className={styles.tooltip}
          style={{ left: tooltip.x, top: tooltip.y }}
        >
          <div className={styles.tipName}>{tooltip.node.name}</div>
          <div className={styles.tipType} style={{ color: TYPE_COLOR[tooltip.node.type] }}>
            {tooltip.node.type}
          </div>
          {tooltip.node.description && (
            <div className={styles.tipDesc}>{tooltip.node.description}</div>
          )}
          {tooltip.node.model && (
            <div className={styles.tipModel}>{tooltip.node.model}</div>
          )}
          {tooltip.node.calls.length > 0 && (
            <div className={styles.tipContract}>
              <div className={styles.tipContractLabel}>calls</div>
              {tooltip.node.calls.map((c) => (
                <div key={c} className={styles.tipContractItem}>{c}</div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
