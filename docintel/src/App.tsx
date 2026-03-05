import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Sidebar } from './components/Sidebar'
import { Toast } from './components/Toast'
import Analyze from './panels/Analyze'
import QA from './panels/QA'
import Improve from './panels/Improve'
import { Pipeline } from './panels/Pipeline'
import { History } from './panels/History'
import { Dashboard } from './panels/Dashboard'

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen overflow-hidden" style={{ background: 'var(--color-base)' }}>
        {/* Ambient background */}
        <div className="mesh-bg" />

        {/* Sidebar */}
        <Sidebar />

        {/* Main content */}
        <main className="flex-1 overflow-y-auto relative z-10">
          <div style={{ maxWidth: 860, margin: '0 auto', padding: '40px 24px' }}>
            <Routes>
              <Route path="/"          element={<Navigate to="/analyze" replace />} />
              <Route path="/analyze"   element={<Analyze />} />
              <Route path="/qa"        element={<QA />} />
              <Route path="/improve"   element={<Improve />} />
              <Route path="/pipeline"  element={<Pipeline />} />
              <Route path="/history"   element={<History />} />
              <Route path="/dashboard" element={<Dashboard />} />
            </Routes>
          </div>
        </main>

        {/* Toast */}
        <Toast />
      </div>
    </BrowserRouter>
  )
}