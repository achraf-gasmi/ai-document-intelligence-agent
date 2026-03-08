import { NavLink } from 'react-router-dom'
import { Search, MessageSquare, RefreshCw, LayoutGrid, Clock, BarChart2, Linkedin, FileText } from 'lucide-react'
import { useState } from 'react'
import { Menu, X } from 'lucide-react'

const NAV = [
  { to: '/analyze',   label: 'Analyze',   Icon: Search },
  { to: '/qa',        label: 'Q&A',       Icon: MessageSquare },
  { to: '/improve',   label: 'Improve',   Icon: RefreshCw },
  { to: '/pipeline',  label: 'Pipeline',  Icon: LayoutGrid },
  { to: '/history',   label: 'History',   Icon: Clock },
  { to: '/dashboard', label: 'Dashboard', Icon: BarChart2 },
]

export function Sidebar() {
  const [mobileOpen, setMobileOpen] = useState(false)

  const inner = (
    <nav className="flex flex-col h-full py-6 px-4">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-2 mb-10">
        <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)' }}>
          <FileText size={16} className="text-white" />
        </div>
        <span className="font-display text-lg font-bold tracking-tight text-white" style={{ fontFamily: 'var(--font-display)' }}>
          DocIntel
        </span>
      </div>

      {/* Nav items */}
      <div className="flex flex-col gap-1 flex-1">
        {NAV.map(({ to, label, Icon }) => (
          <NavLink
            key={to}
            to={to}
            onClick={() => setMobileOpen(false)}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                isActive
                  ? 'text-indigo-400 bg-indigo-500/10 border border-indigo-500/20'
                  : 'text-slate-500 hover:text-slate-300 hover:bg-white/4'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <Icon size={16} className={isActive ? 'text-indigo-400' : 'text-slate-500'} />
                {label}
              </>
            )}
          </NavLink>
        ))}
      </div>

      {/* Author */}
      <div className="px-2 pt-6 border-t" style={{ borderColor: 'var(--color-border)' }}>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white"
            style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)' }}>
            AG
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-slate-300 truncate">Achraf Gasmi</div>
            <div className="text-xs text-slate-500">AI Engineer</div>
          </div>
          <a
            href="https://www.linkedin.com/in/achraf-gasmi-592766134/"
            target="_blank"
            rel="noopener noreferrer"
            className="text-slate-500 hover:text-indigo-400 transition-colors"
          >
            <Linkedin size={15} />
          </a>
        </div>
      </div>
    </nav>
  )

  return (
    <>
      {/* Mobile hamburger */}
      <button
        className="md:hidden fixed top-4 left-4 z-50 p-2 rounded-lg glass text-slate-400 hover:text-white"
        onClick={() => setMobileOpen(v => !v)}
      >
        {mobileOpen ? <X size={20} /> : <Menu size={20} />}
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="md:hidden fixed inset-0 z-30 bg-black/60 backdrop-blur-sm"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed md:relative z-40 h-full w-60 flex-shrink-0 transition-transform duration-300 md:translate-x-0 ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
        style={{
          background: 'rgba(10,10,18,0.85)',
          borderRight: '1px solid var(--color-border)',
          backdropFilter: 'blur(20px)',
        }}
      >
        {inner}
      </aside>
    </>
  )
}