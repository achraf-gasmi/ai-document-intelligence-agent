import { create } from 'zustand'
import type { AnalysisResult, ImprovementResult, HistoryEntry, Stats } from '../api/client'

interface ToastState {
  message: string
  type: 'error' | 'success' | 'info'
  visible: boolean
}

interface AppStore {
  // Analysis
  analyzedFile: File | null
  analysisResult: AnalysisResult | null
  setAnalyzedFile: (f: File | null) => void
  setAnalysisResult: (r: AnalysisResult | null) => void

  // Q&A
  qaHistory: { role: 'user' | 'ai'; text: string }[]
  addQaMessage: (role: 'user' | 'ai', text: string) => void
  clearQaHistory: () => void

  // Improvement
  improveResult: ImprovementResult | null
  threadId: string | null
  setImproveResult: (r: ImprovementResult | null) => void
  setThreadId: (id: string | null) => void

  // History & Stats
  history: HistoryEntry[]
  stats: Stats | null
  setHistory: (h: HistoryEntry[]) => void
  setStats: (s: Stats) => void

  // UI
  toast: ToastState
  showToast: (message: string, type?: 'error' | 'success' | 'info') => void
  hideToast: () => void

  // Typed tabs tracking (tab id → played)
  typedTabs: Set<string>
  markTabTyped: (id: string) => void
  clearTypedTabs: () => void
}

export const useStore = create<AppStore>((set) => ({
  analyzedFile: null,
  analysisResult: null,
  setAnalyzedFile: (f) => set({ analyzedFile: f }),
  setAnalysisResult: (r) => set({ analysisResult: r, typedTabs: new Set() }),

  qaHistory: [],
  addQaMessage: (role, text) =>
    set((s) => ({ qaHistory: [...s.qaHistory, { role, text }] })),
  clearQaHistory: () => set({ qaHistory: [] }),

  improveResult: null,
  threadId: null,
  setImproveResult: (r) => set({ improveResult: r }),
  setThreadId: (id) => set({ threadId: id }),

  history: [],
  stats: null,
  setHistory: (h) => set({ history: h }),
  setStats: (s) => set({ stats: s }),

  toast: { message: '', type: 'error', visible: false },
  showToast: (message, type = 'error') => {
    set({ toast: { message, type, visible: true } })
    setTimeout(() => set((s) => ({ toast: { ...s.toast, visible: false } })), 4000)
  },
  hideToast: () => set((s) => ({ toast: { ...s.toast, visible: false } })),

  typedTabs: new Set(),
  markTabTyped: (id) =>
    set((s) => ({ typedTabs: new Set([...s.typedTabs, id]) })),
  clearTypedTabs: () => set({ typedTabs: new Set() }),
}))