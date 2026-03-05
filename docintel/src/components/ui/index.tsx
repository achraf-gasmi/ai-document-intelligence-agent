import React, { useEffect, useRef, useState } from 'react'

// ─── Badge ────────────────────────────────────────────────────────────────────
type BadgeVariant = 'low' | 'medium' | 'high' | 'critical' | 'success' | 'info' | 'neutral'

const badgeStyles: Record<BadgeVariant, string> = {
  low:      'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20',
  medium:   'bg-amber-500/15   text-amber-400   border border-amber-500/20',
  high:     'bg-red-500/15     text-red-400     border border-red-500/20',
  critical: 'bg-red-600/20     text-red-300     border border-red-500/30',
  success:  'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20',
  info:     'bg-indigo-500/15  text-indigo-400  border border-indigo-500/20',
  neutral:  'bg-white/5        text-slate-400   border border-white/10',
}

export function Badge({ variant, children }: { variant: BadgeVariant; children: React.ReactNode }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold tracking-wide uppercase ${badgeStyles[variant]}`}>
      {children}
    </span>
  )
}

export function getRiskVariant(score: number): BadgeVariant {
  if (score <= 20) return 'low'
  if (score <= 50) return 'medium'
  if (score <= 80) return 'high'
  return 'critical'
}

export function getRiskLabel(score: number): string {
  if (score <= 20) return 'Low'
  if (score <= 50) return 'Medium'
  if (score <= 80) return 'High'
  return 'Critical'
}

export function getRiskColor(score: number): string {
  if (score <= 20) return '#10b981'
  if (score <= 50) return '#f59e0b'
  if (score <= 80) return '#ef4444'
  return '#dc2626'
}

// ─── Card ─────────────────────────────────────────────────────────────────────
export function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`glass p-6 ${className}`}>
      {children}
    </div>
  )
}

// ─── GaugeBar ─────────────────────────────────────────────────────────────────
export function GaugeBar({ value, color, max = 100 }: { value: number; color: string; max?: number }) {
  const [width, setWidth] = useState(0)
  useEffect(() => { const t = setTimeout(() => setWidth((value / max) * 100), 100); return () => clearTimeout(t) }, [value, max])
  return (
    <div className="w-full h-1.5 rounded-full mt-3" style={{ background: 'rgba(255,255,255,0.07)' }}>
      <div
        className="h-full rounded-full transition-all duration-1000 ease-out"
        style={{ width: `${width}%`, background: color }}
      />
    </div>
  )
}

// ─── Typewriter ───────────────────────────────────────────────────────────────
interface TypewriterProps {
  text: string
  speed?: number
  played: boolean
  onDone?: () => void
  className?: string
}

export function Typewriter({ text, speed = 8, played, onDone, className = '' }: TypewriterProps) {
  const [displayed, setDisplayed] = useState(played ? text : '')
  const [typing, setTyping] = useState(!played)
  const ref = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (played) { setDisplayed(text); setTyping(false); return }
    let idx = 0
    setDisplayed('')
    setTyping(true)
    const step = () => {
      idx += Math.ceil(speed / 2)
      if (idx >= text.length) {
        setDisplayed(text)
        setTyping(false)
        onDone?.()
        return
      }
      setDisplayed(text.slice(0, idx))
      ref.current = setTimeout(step, speed)
    }
    ref.current = setTimeout(step, speed)
    return () => { if (ref.current) clearTimeout(ref.current) }
  }, [text, played]) // eslint-disable-line

  const html = displayed
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br />')

  return (
    <p
      className={`${typing ? 'tw-cursor' : ''} ${className}`}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}

// ─── Skeleton ─────────────────────────────────────────────────────────────────
export function Skeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="flex flex-col gap-3 py-2">
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="skeleton h-4 rounded" style={{ width: `${70 + Math.random() * 25}%` }} />
      ))}
    </div>
  )
}

// ─── Tabs ─────────────────────────────────────────────────────────────────────
interface Tab { id: string; label: string }

export function Tabs({
  tabs, active, onChange
}: { tabs: Tab[]; active: string; onChange: (id: string) => void }) {
  return (
    <div className="flex gap-1 border-b mb-6" style={{ borderColor: 'var(--color-border)' }}>
      {tabs.map(t => (
        <button
          key={t.id}
          onClick={() => onChange(t.id)}
          className={`px-4 py-2.5 text-sm font-medium transition-all border-b-2 -mb-px ${
            active === t.id
              ? 'text-indigo-400 border-indigo-400'
              : 'text-slate-500 border-transparent hover:text-slate-300'
          }`}
        >
          {t.label}
        </button>
      ))}
    </div>
  )
}

// ─── Button ───────────────────────────────────────────────────────────────────
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'outline' | 'ghost'
  loading?: boolean
  fullWidth?: boolean
}

export function Button({ variant = 'primary', loading, fullWidth, children, className = '', disabled, ...props }: ButtonProps) {
  const base = 'inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg font-medium text-sm transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed'
  const variants = {
    primary: 'text-white hover:-translate-y-0.5 hover:shadow-lg hover:shadow-indigo-500/20',
    outline: 'border text-slate-300 hover:bg-white/5 hover:-translate-y-0.5',
    ghost:   'text-slate-400 hover:text-slate-200 hover:bg-white/5',
  }
  const primaryBg = variant === 'primary' ? 'bg-gradient-to-r from-indigo-500 to-violet-500' : ''
  const outlineBorder = variant === 'outline' ? 'border-white/10' : ''

  return (
    <button
      className={`${base} ${variants[variant]} ${primaryBg} ${outlineBorder} ${fullWidth ? 'w-full' : ''} ${className}`}
      disabled={disabled || loading}
      {...props}
    >
      {loading && (
        <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
        </svg>
      )}
      {children}
    </button>
  )
}

// ─── Input ────────────────────────────────────────────────────────────────────
export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={`w-full bg-white/3 border rounded-lg px-4 py-2.5 text-sm text-slate-200 placeholder-slate-500 outline-none transition-all focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/20 ${props.className ?? ''}`}
      style={{ borderColor: 'var(--color-border)', ...props.style }}
    />
  )
}