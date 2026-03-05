// Pipeline Panel
import { Card } from '../components/ui'

function FlowNode({ label, desc, accent = false }: { label: string; desc: string; accent?: boolean }) {
  return (
    <div className="flex flex-col items-center justify-center gap-1 px-4 py-3 rounded-xl text-center" style={{
      background: accent ? 'rgba(99,102,241,0.08)' : 'var(--color-elevated)',
      border: `1px solid ${accent ? 'rgba(99,102,241,0.25)' : 'var(--color-border)'}`,
      minWidth: 120,
    }}>
      <div className="text-sm font-semibold" style={{ fontFamily: 'var(--font-display)', color: accent ? '#818cf8' : 'var(--color-text)' }}>{label}</div>
      <div className="text-[11px]" style={{ color: 'var(--color-muted)' }}>{desc}</div>
    </div>
  )
}

function FlowArrow({ label }: { label?: string }) {
  return (
    <div className="flex flex-col items-center gap-0.5">
      {label && <span className="text-[10px]" style={{ color: 'var(--color-muted)' }}>{label}</span>}
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
        <path d="M12 5v14M5 12l7 7 7-7" stroke="rgba(99,102,241,0.4)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
          strokeDasharray="3 2" style={{ animation: 'dashFlow 1.5s linear infinite' }} />
      </svg>
    </div>
  )
}

export function Pipeline() {
  return (
    <div className="flex flex-col gap-6 panel-enter">
      <div>
        <h1 className="text-2xl font-bold tracking-tight" style={{ fontFamily: 'var(--font-display)' }}>Architecture & Pipeline</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--color-muted)' }}>How DocIntel processes and improves your documents.</p>
      </div>

      {/* Analysis pipeline */}
      <Card>
        <h2 className="text-xs font-semibold uppercase tracking-wide mb-6" style={{ color: 'var(--color-muted)', fontFamily: 'var(--font-display)' }}>
          🕸️ Analysis Pipeline
        </h2>
        <div className="flex flex-col items-center gap-2">
          <FlowNode label="PDF Upload" desc="User input" />
          <FlowArrow />
          <FlowNode label="Agent 1 — Document Processor" desc="Extract text · detect language · store in ChromaDB" accent />
          <FlowArrow label="async parallel" />

          <div className="flex gap-4 items-start">
            <div className="flex flex-col items-center gap-1">
              <div className="text-[10px] px-3 py-1 rounded-full mb-2" style={{ background: 'rgba(139,92,246,0.1)', border: '1px solid rgba(139,92,246,0.2)', color: '#a78bfa' }}>
                ⚡ asyncio.gather() — runs concurrently
              </div>
              <div className="flex gap-4">
                <FlowNode label="Agent 2" desc="Summarizer" />
                <FlowNode label="Agent 3" desc="Key Info Extractor" />
                <FlowNode label="Agent 4" desc="Risk Flagger" />
              </div>
            </div>
          </div>

          <FlowArrow />
          <FlowNode label="Risk Score Calculator" desc="Context-aware · LLM-powered · 0–100" accent />
          <FlowArrow />
          <FlowNode label="Agent 5 — Report Generator" desc="Synthesizes all outputs into structured report" accent />
          <FlowArrow />
          <FlowNode label="Agent 6 — Questions Generator" desc="Generates document-specific Q&A suggestions" accent />
          <FlowArrow />
          <div className="flex gap-4">
            <FlowNode label="💬 Q&A (RAG)" desc="ChromaDB semantic search" />
            <FlowNode label="⬇ Export" desc="TXT + PDF download" />
          </div>
        </div>
      </Card>

      {/* Improvement loop */}
      <Card>
        <h2 className="text-xs font-semibold uppercase tracking-wide mb-6" style={{ color: 'var(--color-muted)', fontFamily: 'var(--font-display)' }}>
          🔧 Improvement Loop — Agentic Cycle
        </h2>
        <svg viewBox="0 0 920 280" className="w-full" style={{ minHeight: 220 }}>
          <defs>
            <marker id="arr2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M0 0 L10 5 L0 10z" fill="rgba(99,102,241,0.6)" />
            </marker>
            <marker id="arr2g" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M0 0 L10 5 L0 10z" fill="#10b981" />
            </marker>
            <marker id="arr2r" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M0 0 L10 5 L0 10z" fill="rgba(239,68,68,0.7)" />
            </marker>
          </defs>

          {/* Dashed box */}
          <rect x="60" y="90" width="580" height="100" rx="14" fill="none" stroke="rgba(99,102,241,0.15)" strokeWidth="1.5" strokeDasharray="6 4" />
          <text x="350" y="106" textAnchor="middle" fontSize="10" fill="rgba(99,102,241,0.4)" fontFamily="var(--font-body)">max 3 iterations · LangGraph SqliteSaver checkpoint</text>

          {/* Nodes */}
          {[['Critique','🧐 Find issues', 90, 120], ['Improve','✍️ Fix & rewrite', 310, 120], ['Verify','✅ adversarial t=0', 530, 120]].map(([label, desc, x, y]) => (
            <g key={label as string}>
              <rect x={x as number} y={y as number} width={160} height={64} rx={10}
                fill="rgba(14,14,26,0.9)" stroke="rgba(255,255,255,0.09)" strokeWidth="1" />
              <text x={(x as number)+80} y={(y as number)+26} textAnchor="middle" fontSize="13" fontWeight="600"
                fill="rgba(240,242,255,0.9)" fontFamily="var(--font-display)">{label as string}</text>
              <text x={(x as number)+80} y={(y as number)+46} textAnchor="middle" fontSize="10"
                fill="rgba(124,132,163,0.8)" fontFamily="var(--font-body)">{desc as string}</text>
            </g>
          ))}

          {/* Flow arrows */}
          <path d="M 250 152 L 310 152" stroke="rgba(99,102,241,0.4)" strokeWidth="1.5" strokeDasharray="4 3" markerEnd="url(#arr2)" style={{ animation: 'dashFlow 1.5s linear infinite' }} />
          <path d="M 470 152 L 530 152" stroke="rgba(99,102,241,0.4)" strokeWidth="1.5" strokeDasharray="4 3" markerEnd="url(#arr2)" style={{ animation: 'dashFlow 1.5s linear infinite' }} />

          {/* Loop back */}
          <path d="M 650 120 C 650 45, 170 45, 170 120" fill="none" stroke="rgba(239,68,68,0.45)" strokeWidth="1.5" strokeDasharray="5 4" markerEnd="url(#arr2r)" style={{ animation: 'dashFlow 2s linear infinite' }} />
          <text x="410" y="36" textAnchor="middle" fontSize="11" fill="rgba(239,68,68,0.65)" fontFamily="var(--font-body)">Score &lt; 85 — loop back (LangGraph conditional edge)</text>

          {/* Finalizer */}
          <path d="M 690 152 L 740 152" stroke="rgba(16,185,129,0.5)" strokeWidth="1.5" markerEnd="url(#arr2g)" />
          <rect x="748" y="128" width="130" height="48" rx="8" fill="rgba(16,185,129,0.08)" stroke="rgba(16,185,129,0.25)" strokeWidth="1" />
          <text x="813" y="152" textAnchor="middle" dominantBaseline="middle" fontSize="13" fill="#6ee7b7" fontFamily="var(--font-display)">Finalizer</text>

          {/* Score label */}
          <text x="718" y="145" textAnchor="middle" fontSize="10" fill="#10b981" fontFamily="var(--font-body)">≥85</text>
        </svg>
      </Card>

      {/* Tech stack */}
      <div className="grid grid-cols-2 gap-4">
        {[
          { icon: '🦜', name: 'LangGraph 1.0+',    desc: 'Agentic cycles, conditional edges, SqliteSaver checkpointing' },
          { icon: '⚡', name: 'Groq API',           desc: 'llama-3.3-70b-versatile — fast inference, low latency' },
          { icon: '🗄️', name: 'ChromaDB',           desc: 'Persistent vector store for RAG-based Q&A' },
          { icon: '🐍', name: 'FastAPI',             desc: 'REST API layer connecting frontend to the agent pipeline' },
        ].map(t => (
          <Card key={t.name} className="flex gap-4 items-start">
            <span className="text-2xl">{t.icon}</span>
            <div>
              <div className="font-semibold text-sm" style={{ fontFamily: 'var(--font-display)' }}>{t.name}</div>
              <div className="text-xs mt-1 leading-relaxed" style={{ color: 'var(--color-muted)' }}>{t.desc}</div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}