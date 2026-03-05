import { useStore } from '../store/useStore'
import { X } from 'lucide-react'

export function Toast() {
  const { toast, hideToast } = useStore()

  const colors = {
    error:   'border-red-500/30   bg-red-500/10   text-red-300',
    success: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
    info:    'border-indigo-500/30 bg-indigo-500/10 text-indigo-300',
  }

  return (
    <div
      className={`fixed bottom-6 right-6 z-50 flex items-center gap-3 px-4 py-3 rounded-xl border backdrop-blur-xl shadow-2xl text-sm font-medium transition-all duration-300 ${colors[toast.type]} ${
        toast.visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4 pointer-events-none'
      }`}
    >
      <span>{toast.message}</span>
      <button onClick={hideToast} className="opacity-60 hover:opacity-100 transition-opacity">
        <X size={14} />
      </button>
    </div>
  )
}