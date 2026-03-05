import { useEffect, useState } from 'react'
import { getHistory } from '../api/client'
import { useStore } from '../store/useStore'
import { Card, Badge, Skeleton, Input, Button, getRiskVariant, getRiskLabel } from '../components/ui'
import { ChevronDown, ChevronUp, Download } from 'lucide-react'

export function History() {
  const { history, setHistory, showToast } = useStore()
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [expanded, setExpanded] = useState<number | null>(null)

  useEffect(() => {
    if (history.length > 0) return
    setLoading(true)
    getHistory()
      .then(setHistory)
      .catch(() => showToast('Failed to load history'))
      .finally(() => setLoading(false))
  }, []) // eslint-disable-line

  const filtered = history.filter(h =>
    h.filename.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="flex flex-col gap-6 panel-enter">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight" style={{ fontFamily: 'var(--font-display)' }}>Analysis History</h1>
          <p className="text-sm mt-1" style={{ color: 'var(--color-muted)' }}>All past document analyses.</p>
        </div>
        <Button variant="ghost" className="text-xs text-red-400 hover:text-red-300" onClick={() => {
          setHistory([])
          showToast('History cleared', 'info')
        }}>
          🗑 Clear History
        </Button>
      </div>

      <Input
        value={search}
        onChange={e => setSearch(e.target.value)}
        placeholder="🔍  Search by filename…"
      />

      <Card className="!p-0 overflow-hidden">
        {loading ? (
          <div className="p-6"><Skeleton lines={4} /></div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3 text-center">
            <div className="text-3xl">📭</div>
            <div className="text-sm" style={{ color: 'var(--color-muted)' }}>No analyses yet</div>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr style={{ borderBottom: '1px solid var(--color-border)' }}>
                {['Filename','Date','Risk Score','Language','Status',''].map(h => (
                  <th key={h} className="text-left px-5 py-3 text-xs font-semibold uppercase tracking-wide" style={{ color: 'var(--color-muted)' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((entry, i) => (
                <>
                  <tr
                    key={entry.id}
                    onClick={() => setExpanded(expanded === i ? null : i)}
                    className="cursor-pointer transition-colors"
                    style={{ borderBottom: expanded === i ? 'none' : '1px solid var(--color-border)' }}
                    onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.02)')}
                    onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                  >
                    <td className="px-5 py-4 text-sm font-medium">{entry.filename}</td>
                    <td className="px-5 py-4 text-sm" style={{ color: 'var(--color-muted)' }}>{entry.timestamp}</td>
                    <td className="px-5 py-4">
                      <Badge variant={getRiskVariant(entry.risk_score)}>{entry.risk_score} · {getRiskLabel(entry.risk_score)}</Badge>
                    </td>
                    <td className="px-5 py-4 text-sm" style={{ color: 'var(--color-muted)' }}>{entry.language}</td>
                    <td className="px-5 py-4">
                      <Badge variant={entry.status === 'complete' ? 'success' : 'high'}>
                        {entry.status === 'complete' ? '✓ Complete' : '✗ Failed'}
                      </Badge>
                    </td>
                    <td className="px-5 py-4 text-right">
                      {expanded === i ? <ChevronUp size={16} className="text-slate-500 inline" /> : <ChevronDown size={16} className="text-slate-500 inline" />}
                    </td>
                  </tr>
                  {expanded === i && entry.summary && (
                    <tr key={`${entry.id}-detail`} style={{ borderBottom: '1px solid var(--color-border)' }}>
                      <td colSpan={6} className="px-5 py-4 panel-enter" style={{ background: 'rgba(0,0,0,0.2)' }}>
                        <div className="text-sm leading-relaxed mb-3" style={{ color: 'rgba(240,242,255,0.7)' }}>
                          <strong className="text-slate-400">Summary: </strong>{entry.summary}
                        </div>
                        <Button variant="outline" className="text-xs !px-3 !py-1.5">
                          <Download size={12} /> Download Report
                        </Button>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  )
}