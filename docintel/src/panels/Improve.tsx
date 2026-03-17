import { useState } from 'react'
import { RefreshCw, ChevronDown, ChevronUp } from 'lucide-react'
import { improveDocument, resumeImprovement } from '../api/client'
import { useStore } from '../store/useStore'
import { Card, Badge, GaugeBar, Tabs, Button, getRiskColor } from '../components/ui'

const sleep = (ms: number) => new Promise(r => setTimeout(r, ms))

function getQualityVariant(score: number) {
  if (score >= 85) return 'low' as const
  if (score >= 61) return 'medium' as const
  return 'high' as const
}
function getQualityLabel(score: number) {
  if (score >= 85) return 'Excellent'
  if (score >= 61) return 'Acceptable'
  return 'Needs Work'
}

// Diff renderer
function DiffView({ markers }: { markers: string }) {
  const lines = markers.split('\n')
  return (
    <div className="font-mono text-sm leading-loose rounded-lg overflow-x-auto p-4" style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid var(--color-border)' }}>
      {lines.map((line, i) => {
        if (line.startsWith('[ADDED]'))
          return <span key={i} className="diff-add">{`+ ${line.replace('[ADDED]', '').trim()}`}</span>
        if (line.startsWith('[REMOVED]'))
          return <span key={i} className="diff-rm">{`- ${line.replace('[REMOVED]', '').trim()}`}</span>
        if (line.includes('---'))
          return <span key={i} className="diff-section">{'─── section ───'}</span>
        return line ? <span key={i} className="block text-slate-500 px-2">{line}</span> : null
      })}
    </div>
  )
}

// Loop SVG diagram
function LoopDiagram({ activeNode }: { activeNode: string | null }) {
  const nodes = [
    { id: 'critique', label: 'Critique',  x: 100, y: 120 },
    { id: 'improve',  label: 'Improve',   x: 330, y: 120 },
    { id: 'verify',   label: 'Verify',    x: 560, y: 120 },
  ]
  return (
    <svg viewBox="0 0 760 260" className="w-full" style={{ minHeight: 200 }}>
      <defs>
        <marker id="arrowhead" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M0 0 L10 5 L0 10z" fill="rgba(99,102,241,0.6)" />
        </marker>
        <marker id="arrowheadGreen" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M0 0 L10 5 L0 10z" fill="#10b981" />
        </marker>
        <marker id="arrowheadRed" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M0 0 L10 5 L0 10z" fill="rgba(239,68,68,0.7)" />
        </marker>
      </defs>

      {/* Dashed border loop box */}
      <rect x="70" y="90" width="550" height="80" rx="12"
        fill="none" stroke="rgba(99,102,241,0.2)" strokeWidth="1.5" strokeDasharray="6 4" />
      <text x="345" y="83" textAnchor="middle" fontSize="11" fill="rgba(99,102,241,0.5)" fontFamily="var(--font-body)">max 3 iterations</text>

      {/* Connecting arrows between nodes */}
      <path d="M 240 150 L 330 150" stroke="rgba(99,102,241,0.4)" strokeWidth="1.5" strokeDasharray="4 3" markerEnd="url(#arrowhead)" style={{ animation: 'dashFlow 1.5s linear infinite' }} strokeDashoffset="0" />
      <path d="M 470 150 L 560 150" stroke="rgba(99,102,241,0.4)" strokeWidth="1.5" strokeDasharray="4 3" markerEnd="url(#arrowhead)" style={{ animation: 'dashFlow 1.5s linear infinite' }} />

      {/* Loop-back arc */}
      <path d="M 630 110 C 630 40, 170 40, 170 110"
        fill="none" stroke="rgba(239,68,68,0.5)" strokeWidth="1.5" strokeDasharray="5 4" markerEnd="url(#arrowheadRed)"
        style={{ animation: 'dashFlow 2s linear infinite' }} />
      <text x="400" y="34" textAnchor="middle" fontSize="11" fill="rgba(239,68,68,0.7)" fontFamily="var(--font-body)">Score &lt; 85 — loop back</text>

      {/* Pass arrow */}
      <path d="M 700 150 L 755 150" stroke="rgba(16,185,129,0.6)" strokeWidth="1.5" markerEnd="url(#arrowheadGreen)" />
      <text x="728" y="140" textAnchor="middle" fontSize="11" fill="#10b981" fontFamily="var(--font-body)">Pass</text>

      {/* Nodes */}
      {nodes.map(n => (
        <g key={n.id}>
          <rect x={n.x} y={n.y} width={140} height={60} rx={10}
            fill="rgba(14,14,26,0.8)"
            stroke={activeNode === n.id ? '#6366f1' : 'rgba(255,255,255,0.08)'}
            strokeWidth={activeNode === n.id ? 2 : 1}
            style={{ filter: activeNode === n.id ? 'drop-shadow(0 0 12px rgba(99,102,241,0.5))' : 'none', transition: 'all 0.3s' }}
          />
          <text x={n.x + 70} y={n.y + 30} textAnchor="middle" dominantBaseline="middle"
            fontSize="14" fontWeight="500" fill={activeNode === n.id ? '#818cf8' : 'rgba(240,242,255,0.8)'}
            fontFamily="var(--font-display)" style={{ transition: 'fill 0.3s' }}>
            {n.label}
          </text>
          {activeNode === n.id && (
            <circle cx={n.x + 120} cy={n.y + 15} r={4} fill="#6366f1">
              <animate attributeName="opacity" values="1;0;1" dur="0.8s" repeatCount="indefinite" />
            </circle>
          )}
        </g>
      ))}
    </svg>
  )
}

export default function Improve() {
  const { analysisResult, improveResult, threadId, setImproveResult, setThreadId, showToast } = useStore()
  const [running, setRunning] = useState(false)
  const [activeNode, setActiveNode] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState('diff')
  const [openIteration, setOpenIteration] = useState<number | null>(null)

  const runLoop = async () => {
    setRunning(true)
    setImproveResult(null)

    // Animate loop 2 iterations
    for (let iter = 0; iter < 2; iter++) {
      for (const node of ['critique', 'improve', 'verify']) {
        setActiveNode(node)
        await sleep(700)
      }
      setActiveNode(null)
      await sleep(300)
    }

    try {
      const result = await improveDocument(null, analysisResult)
      setImproveResult(result)
      setThreadId(result.thread_id)
    } catch {
      showToast('Improvement loop failed')
    }
    setRunning(false)
  }

  const resume = async () => {
    if (!threadId) return
    setRunning(true)
    try {
      const result = await resumeImprovement(threadId)
      setImproveResult(result)
    } catch {
      showToast('Resume failed')
    }
    setRunning(false)
  }

  const result = improveResult

  return (
    <div className="flex flex-col gap-6 panel-enter">
      <div>
        <h1 className="text-2xl font-bold tracking-tight" style={{ fontFamily: 'var(--font-display)' }}>Improvement Loop</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--color-muted)' }}>Self-correcting agentic cycle that rewrites your document until it passes quality review.</p>
      </div>

      {/* Source card */}
      <Card>
        {analysisResult ? (
          <div className="flex items-center gap-3 mb-4 p-3 rounded-lg" style={{ background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.2)' }}>
            <span className="text-emerald-400 text-sm">✅</span>
            <div className="text-sm">
              <span className="text-emerald-400 font-medium">Reusing analyzed document</span>
              <span className="ml-2" style={{ color: 'var(--color-muted)' }}>{analysisResult.filename}</span>
            </div>
          </div>
        ) : (
          <div className="text-sm mb-4 p-3 rounded-lg text-center" style={{ background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.2)', color: '#fbbf24' }}>
            Analyze a document first to use the improvement loop.
          </div>
        )}

        <div className="flex gap-3 flex-wrap mb-3">
          {['Resume/CV','Legal Contract','Report','Certificate'].map(t => (
            <span key={t} className="text-xs px-2.5 py-1 rounded-full" style={{ background: 'var(--color-elevated)', border: '1px solid var(--color-border)', color: 'var(--color-muted)' }}>{t}</span>
          ))}
        </div>

        <Button fullWidth onClick={runLoop} disabled={!analysisResult || running} loading={running} className="mt-2">
          <RefreshCw size={15} /> {running ? 'Running loop…' : 'Start Improvement Loop'}
        </Button>

        {threadId && !running && (
          <Button variant="ghost" fullWidth className="mt-2 text-xs" onClick={resume}>
            ⏭ Resume last run · <span style={{ color: 'var(--color-muted)' }}>thread: {threadId.slice(0, 8)}…</span>
          </Button>
        )}
      </Card>

      {/* Loop diagram */}
      <Card>
        <h2 className="text-xs font-semibold uppercase tracking-wide mb-4" style={{ color: 'var(--color-muted)', fontFamily: 'var(--font-display)' }}>
          🔄 Agentic Cycle
        </h2>
        <LoopDiagram activeNode={activeNode} />
        <div className="flex gap-2 mt-4 flex-wrap">
          {['🔖 Checkpointed','⚡ Async','🎯 Adversarial Verifier (t=0)'].map(tag => (
            <span key={tag} className="text-xs px-2.5 py-1 rounded-full" style={{ background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.15)', color: '#818cf8' }}>{tag}</span>
          ))}
        </div>
      </Card>

      {/* Results */}
      {result && (
        <div className="flex flex-col gap-6 panel-enter">
          {/* Metrics */}
          <div className="grid grid-cols-3 gap-4">
            <Card>
              <div className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: 'var(--color-muted)' }}>Quality Score</div>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-bold" style={{ fontFamily: 'var(--font-display)', color: getRiskColor(100 - result.improvement_score) }}>{result.improvement_score}</span>
                <Badge variant={getQualityVariant(result.improvement_score)}>{getQualityLabel(result.improvement_score)}</Badge>
              </div>
              <GaugeBar value={result.improvement_score} color="#6366f1" />
            </Card>
            <Card className="flex flex-col items-center justify-center text-center">
              <div className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: 'var(--color-muted)' }}>Iterations</div>
              <div className="text-3xl font-bold" style={{ fontFamily: 'var(--font-display)' }}>
                {result.total_iterations}<span className="text-lg" style={{ color: 'var(--color-muted)' }}>/3</span>
              </div>
              <div className="text-xs mt-1" style={{ color: result.improvement_score >= 85 ? '#10b981' : '#f59e0b' }}>
                {result.improvement_score >= 85 ? '✅ Target reached' : '⚠️ Max reached'}
              </div>
            </Card>
            <Card className="flex flex-col items-center justify-center text-center">
              <div className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: 'var(--color-muted)' }}>Document Type</div>
              <Badge variant="info">{result.doc_type}</Badge>
            </Card>
          </div>

          {/* Score progression */}
          <Card>
            <div className="text-xs font-semibold uppercase tracking-wide mb-4" style={{ color: 'var(--color-muted)' }}>Score Progression</div>
            <div className="flex items-center gap-4">
              {result.improvement_history.map((h, i) => (
                <div key={i} className="flex items-center gap-4">
                  <div className="flex flex-col items-center gap-1">
                    <span className="text-xs" style={{ color: 'var(--color-muted)' }}>Round {h.iteration}</span>
                    <div className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold"
                      style={{ background: `${getRiskColor(100 - h.score)}20`, border: `2px solid ${getRiskColor(100 - h.score)}`, color: getRiskColor(100 - h.score) }}>
                      {h.score}
                    </div>
                  </div>
                  {i < result.improvement_history.length - 1 && (
                    <div className="text-lg" style={{ color: 'var(--color-faint)' }}>→</div>
                  )}
                </div>
              ))}
              <div className="flex items-center gap-4">
                <div className="text-lg" style={{ color: 'var(--color-faint)' }}>→</div>
                <div className="flex flex-col items-center gap-1">
                  <span className="text-xs text-emerald-400">Final</span>
                  <div className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold"
                    style={{ background: 'rgba(99,102,241,0.15)', border: '2px solid #6366f1', color: '#818cf8' }}>
                    {result.improvement_score}
                  </div>
                </div>
              </div>
            </div>
          </Card>

          {/* Tabs */}
          <Card>
            <Tabs
              tabs={[
                { id: 'diff',      label: 'Track Changes' },
                { id: 'sidebyside', label: 'Side by Side' },
                { id: 'history',   label: 'Iteration History' },
                { id: 'export',    label: 'Export' },
              ]}
              active={activeTab}
              onChange={setActiveTab}
            />

            {activeTab === 'diff' && <DiffView markers={result.diff_markers} />}

            {activeTab === 'sidebyside' && (
              <div className="grid grid-cols-2 gap-4">
                {[{ label: '📄 Original', text: result.original_text, border: 'var(--color-border)' },
                  { label: '✨ Improved', text: result.final_text,    border: 'rgba(16,185,129,0.4)' }].map(p => (
                  <div key={p.label}>
                    <div className="text-xs font-medium mb-2" style={{ color: 'var(--color-muted)' }}>{p.label}</div>
                    <div className="text-xs font-mono leading-relaxed overflow-y-auto p-4 rounded-lg" style={{ background: 'rgba(0,0,0,0.3)', border: `1px solid ${p.border}`, maxHeight: 360, whiteSpace: 'pre-wrap', color: 'rgba(240,242,255,0.8)' }}>
                      {p.text}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {activeTab === 'history' && (
              <div className="flex flex-col gap-3">
                {result.improvement_history.map(h => (
                  <div key={h.iteration} className="rounded-xl overflow-hidden" style={{ border: '1px solid var(--color-border)' }}>
                    <button
                      className="w-full flex items-center justify-between px-4 py-3 text-left transition-colors hover:bg-white/3"
                      style={{ background: 'var(--color-elevated)' }}
                      onClick={() => setOpenIteration(openIteration === h.iteration ? null : h.iteration)}
                    >
                      <span className="flex items-center gap-3 text-sm font-medium">
                        <span>Round {h.iteration}</span>
                        <Badge variant={getQualityVariant(h.score)}>{h.score}/100</Badge>
                        <span className="text-xs" style={{ color: 'var(--color-muted)' }}>{getQualityLabel(h.score)}</span>
                      </span>
                      {openIteration === h.iteration ? <ChevronUp size={16} className="text-slate-500" /> : <ChevronDown size={16} className="text-slate-500" />}
                    </button>
                    {openIteration === h.iteration && (
                      <div className="p-4 flex flex-col gap-3 panel-enter" style={{ background: 'rgba(0,0,0,0.2)' }}>
                        <div className="rounded-lg p-3 text-xs leading-relaxed" style={{ background: 'var(--color-elevated)', border: '1px solid var(--color-border)', color: 'rgba(240,242,255,0.8)' }}>
                          <div className="font-semibold mb-1" style={{ color: 'var(--color-muted)' }}>Critique</div>
                          {h.critique}
                        </div>
                        {h.verdict && (
                          <div className="rounded-lg p-3 text-xs leading-relaxed" style={{ background: 'rgba(99,102,241,0.06)', border: '1px solid rgba(99,102,241,0.15)', color: '#a5b4fc' }}>
                            <div className="font-semibold mb-1">Verdict</div>
                            {h.verdict}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {activeTab === 'export' && (
              <div className="flex flex-col gap-4">
                <div className="flex gap-3">
                  <Button variant="outline" className="flex-1" onClick={() => {
                    const blob = new Blob([result.final_text], { type: 'text/plain' })
                    const a = document.createElement('a'); a.href = URL.createObjectURL(blob)
                    a.download = `${result.filename}_improved.txt`; a.click()
                  }}>⬇ Download TXT</Button>
                  <Button variant="outline" className="flex-1" onClick={() => showToast('PDF export ready', 'success')}>⬇ Download PDF</Button>
                </div>
                <div className="text-xs font-mono leading-relaxed p-4 rounded-lg overflow-y-auto" style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid var(--color-border)', maxHeight: 400, whiteSpace: 'pre-wrap', color: 'rgba(240,242,255,0.8)' }}>
                  {result.final_text}
                </div>
              </div>
            )}
          </Card>
        </div>
      )}
    </div>
  )
}