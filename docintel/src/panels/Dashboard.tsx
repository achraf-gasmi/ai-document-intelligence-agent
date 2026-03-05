import { useEffect, useState } from 'react'
import { getStats } from '../api/client'
import { useStore } from '../store/useStore'
import { Card, Badge, Skeleton, getRiskVariant, getRiskLabel, getRiskColor } from '../components/ui'

export function Dashboard() {
  const { stats, setStats, showToast } = useStore()
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (stats) return
    setLoading(true)
    getStats()
      .then(setStats)
      .catch(() => showToast('Failed to load stats'))
      .finally(() => setLoading(false))
  }, []) // eslint-disable-line

  if (loading || !stats) {
    return (
      <div className="flex flex-col gap-6 panel-enter">
        <div>
          <h1 className="text-2xl font-bold tracking-tight" style={{ fontFamily: 'var(--font-display)' }}>Dashboard</h1>
        </div>
        <div className="grid grid-cols-2 gap-4">
          {[1,2,3,4].map(i => <Card key={i}><Skeleton lines={2} /></Card>)}
        </div>
      </div>
    )
  }

  const successRate = Math.round((stats.successful / stats.total) * 100)

  const distLabels = ['Low', 'Medium', 'High', 'Critical']
  const distColors = ['#10b981', '#f59e0b', '#ef4444', '#dc2626']
  const dist = (stats as unknown as { dist: number[] }).dist ?? [40, 35, 15, 10]

  return (
    <div className="flex flex-col gap-6 panel-enter">
      <div>
        <h1 className="text-2xl font-bold tracking-tight" style={{ fontFamily: 'var(--font-display)' }}>Dashboard</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--color-muted)' }}>Overview of all document analyses.</p>
      </div>

      {/* Metric cards 2×2 */}
      <div className="grid grid-cols-2 gap-4">
        {[
          { label: 'Total Analyses',  value: stats.total,      color: '#818cf8', sub: 'All time' },
          { label: 'Success Rate',    value: `${successRate}%`, color: '#10b981', sub: `${stats.successful} successful` },
          { label: 'Avg Risk Score',  value: stats.avg_risk,   color: getRiskColor(stats.avg_risk), sub: getRiskLabel(stats.avg_risk) + ' average' },
          { label: 'Failed',          value: stats.failed,     color: '#ef4444', sub: 'Extraction errors' },
        ].map(m => (
          <Card key={m.label} className="relative overflow-hidden">
            <div className="absolute bottom-0 left-0 right-0 h-0.5 opacity-60" style={{ background: m.color }} />
            <div className="text-xs font-semibold uppercase tracking-wide mb-3" style={{ color: 'var(--color-muted)' }}>{m.label}</div>
            <div className="text-4xl font-bold mb-1" style={{ fontFamily: 'var(--font-display)', color: m.color }}>{m.value}</div>
            <div className="text-xs" style={{ color: 'var(--color-muted)' }}>{m.sub}</div>
          </Card>
        ))}
      </div>

      {/* Bottom row */}
      <div className="grid grid-cols-2 gap-4">
        {/* Risk distribution */}
        <Card>
          <h3 className="text-xs font-semibold uppercase tracking-wide mb-4" style={{ color: 'var(--color-muted)', fontFamily: 'var(--font-display)' }}>
            Risk Distribution
          </h3>
          <div className="flex flex-col gap-3">
            {distLabels.map((label, i) => (
              <div key={label} className="flex items-center gap-3">
                <span className="text-xs w-14 text-right" style={{ color: 'var(--color-muted)' }}>{label}</span>
                <div className="flex-1 h-5 rounded" style={{ background: 'var(--color-elevated)' }}>
                  <BarFill pct={dist[i]} color={distColors[i]} />
                </div>
                <span className="text-xs w-8" style={{ color: 'var(--color-muted)' }}>{dist[i]}%</span>
              </div>
            ))}
          </div>
        </Card>

        {/* Recent analyses */}
        <Card>
          <h3 className="text-xs font-semibold uppercase tracking-wide mb-4" style={{ color: 'var(--color-muted)', fontFamily: 'var(--font-display)' }}>
            Recent Analyses
          </h3>
          <div className="flex flex-col gap-2">
            {stats.recent.slice(0, 5).map((r, i) => (
              <div key={i} className="flex items-center justify-between py-2 px-3 rounded-lg transition-colors"
                style={{ background: 'var(--color-elevated)', border: '1px solid var(--color-border)' }}
                onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--color-border-hover)')}
                onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--color-border)')}
              >
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-medium truncate">{r.filename}</div>
                  <div className="text-xs mt-0.5" style={{ color: 'var(--color-muted)' }}>{r.timestamp}</div>
                </div>
                <Badge variant={getRiskVariant(r.risk_score)}>{r.risk_score}</Badge>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}

function BarFill({ pct, color }: { pct: number; color: string }) {
  const [width, setWidth] = useState(0)
  useEffect(() => { const t = setTimeout(() => setWidth(pct), 200); return () => clearTimeout(t) }, [pct])
  return (
    <div className="h-full rounded transition-all duration-700 ease-out flex items-center justify-end pr-2"
      style={{ width: `${width}%`, background: `${color}cc`, minWidth: width > 0 ? 8 : 0 }}>
      {pct > 10 && <span className="text-[10px] font-bold" style={{ color: 'rgba(0,0,0,0.7)' }}>{pct}%</span>}
    </div>
  )
}