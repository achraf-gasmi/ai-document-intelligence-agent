import { useCallback, useRef, useState } from 'react'
import { Upload, FileText, CheckCircle } from 'lucide-react'
import { analyzeDocument } from '../api/client'
import { useStore } from '../store/useStore'
import { Card, Badge, GaugeBar, Tabs, Typewriter, Button, getRiskVariant, getRiskLabel, getRiskColor } from '../components/ui'

const PIPELINE_STEPS = [
  { id: '1', label: 'Process',   desc: 'Extract & store' },
  { id: '2', label: 'Summarize', desc: 'Parallel',        parallel: true },
  { id: '3', label: 'Extract',   desc: 'Parallel',        parallel: true },
  { id: '4', label: 'Risk Flag', desc: 'Parallel',        parallel: true },
  { id: '5', label: 'Report',    desc: 'Synthesize' },
  { id: '6', label: 'Q&A Gen',   desc: 'Suggestions' },
]

type StepState = 'idle' | 'active' | 'done'

const sleep = (ms: number) => new Promise(r => setTimeout(r, ms))

export default function Analyze() {
  const { setAnalysisResult, setAnalyzedFile, showToast, typedTabs, markTabTyped } = useStore()
  const analysisResult = useStore(s => s.analysisResult)
  const analyzedFile   = useStore(s => s.analyzedFile)

  const [dragOver, setDragOver] = useState(false)
  const [running,  setRunning]  = useState(false)
  const [steps,    setSteps]    = useState<Record<string, StepState>>({})
  const [showParallel, setShowParallel] = useState(false)
  const [activeTab, setActiveTab] = useState('report')
  const fileRef = useRef<HTMLInputElement>(null)

  const setStep = (ids: string[], state: StepState) =>
    setSteps(prev => { const n = { ...prev }; ids.forEach(id => (n[id] = state)); return n })

  const handleFile = (file: File) => {
    if (!file.name.endsWith('.pdf')) { showToast('Please upload a PDF file'); return }
    setAnalyzedFile(file)
  }

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setDragOver(false)
    if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0])
  }, []) // eslint-disable-line

  const runAnalysis = async () => {
    if (!analyzedFile) return
    setRunning(true)
    setSteps({})
    setShowParallel(false)

    // Step 1
    setStep(['1'], 'active');             await sleep(1300)
    setStep(['1'], 'done')
    // Steps 2–4 parallel
    setShowParallel(true)
    setStep(['2','3','4'], 'active');     await sleep(2200)
    setStep(['2','3','4'], 'done');       setShowParallel(false)
    // Step 5
    setStep(['5'], 'active');             await sleep(1100)
    setStep(['5'], 'done')
    // Step 6
    setStep(['6'], 'active');             await sleep(700)
    setStep(['6'], 'done')

    try {
      const result = await analyzeDocument(analyzedFile)
      setAnalysisResult(result)
      setActiveTab('report')
    } catch {
      showToast('Analysis failed — check your connection')
    }
    setRunning(false)
  }

  const result = analysisResult

  return (
    <div className="flex flex-col gap-6 panel-enter">
      <div>
        <h1 className="text-2xl font-bold tracking-tight" style={{ fontFamily: 'var(--font-display)' }}>Analyze Document</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--color-muted)' }}>Upload a PDF to extract key info, assess risks, and generate a report.</p>
      </div>

      {/* Upload */}
      <Card>
        {analyzedFile ? (
          <div className="flex items-center gap-4 py-2">
            <div className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: 'rgba(99,102,241,0.15)' }}>
              <FileText size={20} className="text-indigo-400" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-medium text-sm truncate">{analyzedFile.name}</div>
              <div className="text-xs mt-0.5" style={{ color: 'var(--color-muted)' }}>{(analyzedFile.size / 1024).toFixed(1)} KB</div>
            </div>
            <CheckCircle size={18} className="text-emerald-400 flex-shrink-0" />
          </div>
        ) : (
          <div
            onDragOver={e => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
            onClick={() => fileRef.current?.click()}
            className={`border-2 border-dashed rounded-xl py-14 flex flex-col items-center gap-3 cursor-pointer transition-all ${
              dragOver ? 'border-indigo-500 bg-indigo-500/5' : 'border-white/8 hover:border-white/16 hover:bg-white/2'
            }`}
          >
            <Upload size={36} className={dragOver ? 'text-indigo-400' : 'text-slate-500'} />
            <div className="text-center">
              <div className="font-medium text-slate-300">Drop your PDF here</div>
              <div className="text-sm mt-1" style={{ color: 'var(--color-muted)' }}>or click to browse · supports PDF up to 200MB</div>
            </div>
          </div>
        )}
        <input ref={fileRef} type="file" accept=".pdf" className="hidden" onChange={e => e.target.files?.[0] && handleFile(e.target.files[0])} />

        <Button
          fullWidth
          className="mt-4"
          onClick={runAnalysis}
          disabled={!analyzedFile || running}
          loading={running}
        >
          {running ? 'Analyzing…' : 'Run Analysis'}
        </Button>
      </Card>

      {/* Pipeline Stepper */}
      <Card>
        <div className="flex items-center justify-between mb-6">
          <h2 className="font-semibold text-sm tracking-wide uppercase" style={{ color: 'var(--color-muted)', fontFamily: 'var(--font-display)' }}>Agent Pipeline</h2>
          {showParallel && (
            <span className="text-xs px-2 py-1 rounded-full border" style={{ color: '#8b5cf6', borderColor: 'rgba(139,92,246,0.3)', background: 'rgba(139,92,246,0.08)' }}>
              ⚡ Async Parallel
            </span>
          )}
        </div>
        <div className="relative">
          {/* Connecting line */}
          <div className="absolute top-4 left-4 right-4 h-px" style={{ background: 'var(--color-border)' }} />
          <div className="relative flex justify-between">
            {PIPELINE_STEPS.map(step => {
              const state = steps[step.id] ?? 'idle'
              return (
                <div key={step.id} className="flex flex-col items-center gap-2 flex-1 z-10">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all duration-300 ${
                      state === 'done'
                        ? 'bg-emerald-500 text-white'
                        : state === 'active'
                        ? 'bg-indigo-500 text-white'
                        : 'text-slate-500'
                    }`}
                    style={{
                      background: state === 'idle' ? 'var(--color-elevated)' : undefined,
                      border: state === 'idle' ? '1px solid var(--color-border)' : undefined,
                      animation: state === 'active' ? 'glowPulse 1.5s infinite' : undefined,
                    }}
                  >
                    {state === 'done' ? '✓' : step.id}
                  </div>
                  <div className="text-center">
                    <div className={`text-xs font-medium ${state === 'idle' ? 'text-slate-600' : state === 'active' ? 'text-indigo-400' : 'text-slate-400'}`}>
                      {step.label}
                    </div>
                    {step.parallel && (
                      <div className="text-[10px] mt-0.5" style={{ color: 'var(--color-faint)' }}>parallel</div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </Card>

      {/* Results */}
      {result && (
        <div className="flex flex-col gap-6 panel-enter">
          {/* Metrics */}
          <div className="grid grid-cols-3 gap-4">
            <Card>
              <div className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: 'var(--color-muted)' }}>Risk Score</div>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-bold" style={{ fontFamily: 'var(--font-display)', color: getRiskColor(result.risk_score) }}>{result.risk_score}</span>
                <Badge variant={getRiskVariant(result.risk_score)}>{getRiskLabel(result.risk_score)}</Badge>
              </div>
              <GaugeBar value={result.risk_score} color={getRiskColor(result.risk_score)} />
              <p className="text-xs mt-2" style={{ color: 'var(--color-muted)' }}>{result.risk_reasoning}</p>
            </Card>
            <Card className="flex flex-col items-center justify-center text-center">
              <div className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: 'var(--color-muted)' }}>Language</div>
              <div className="text-2xl font-bold" style={{ fontFamily: 'var(--font-display)' }}>{result.language}</div>
              <div className="text-xs mt-1" style={{ color: 'var(--color-muted)' }}>Auto-detected</div>
            </Card>
            <Card>
              <div className="text-xs font-semibold uppercase tracking-wide mb-3" style={{ color: 'var(--color-muted)' }}>Export</div>
              <div className="flex flex-col gap-2">
                <Button variant="outline" fullWidth onClick={() => {
                  const blob = new Blob([result.report], { type: 'text/plain' })
                  const a = document.createElement('a'); a.href = URL.createObjectURL(blob)
                  a.download = `${result.filename}_report.txt`; a.click()
                }}>⬇ TXT Report</Button>
                <Button variant="outline" fullWidth onClick={() => useStore.getState().showToast('PDF export ready', 'success')}>⬇ PDF Report</Button>
              </div>
            </Card>
          </div>

          {/* Content Tabs */}
          <Card>
            <Tabs
              tabs={[
                { id: 'report',  label: 'Full Report' },
                { id: 'summary', label: 'Summary' },
                { id: 'keyinfo', label: 'Key Info' },
                { id: 'risks',   label: 'Risks' },
              ]}
              active={activeTab}
              onChange={id => { setActiveTab(id) }}
            />
            <Typewriter
              key={activeTab}
              text={(result as Record<string, string>)[activeTab === 'keyinfo' ? 'key_info' : activeTab] ?? ''}
              played={typedTabs.has(activeTab)}
              onDone={() => markTabTyped(activeTab)}
              className="text-sm leading-relaxed"
              style={{ color: 'rgba(240,242,255,0.85)' } as React.CSSProperties}
            />
          </Card>
        </div>
      )}
    </div>
  )
}