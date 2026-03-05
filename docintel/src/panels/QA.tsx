import { useRef, useState } from 'react'
import { Send, Trash2 } from 'lucide-react'
import { askQuestion } from '../api/client'
import { useStore } from '../store/useStore'
import { Card, Button, Input } from '../components/ui'

export default function QA() {
  const { analysisResult, qaHistory, addQaMessage, clearQaHistory, showToast } = useStore()
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () =>
    setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), 50)

  const ask = async (question: string) => {
    if (!question.trim() || !analysisResult || loading) return
    setInput('')
    addQaMessage('user', question)
    scrollToBottom()
    setLoading(true)
    try {
      const answer = await askQuestion(question, analysisResult.filename, analysisResult.language)
      addQaMessage('ai', answer)
    } catch {
      showToast('Failed to get answer')
      addQaMessage('ai', 'Sorry, something went wrong. Please try again.')
    }
    setLoading(false)
    scrollToBottom()
  }

  return (
    <div className="flex flex-col gap-6 panel-enter">
      <div>
        <h1 className="text-2xl font-bold tracking-tight" style={{ fontFamily: 'var(--font-display)' }}>Document Q&A</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--color-muted)' }}>Ask anything about your analyzed document.</p>
      </div>

      {!analysisResult ? (
        <Card className="flex flex-col items-center justify-center py-20 gap-4 text-center">
          <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-2" style={{ background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.2)' }}>
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-indigo-400">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <path d="M9 13h6M9 17h3"/>
              <circle cx="17" cy="17" r="3" stroke="currentColor" fill="none"/>
              <path d="M20 20l2 2"/>
            </svg>
          </div>
          <div>
            <div className="font-semibold text-slate-300">No document analyzed yet</div>
            <div className="text-sm mt-1" style={{ color: 'var(--color-muted)' }}>Go to Analyze to get started</div>
          </div>
          <Button variant="outline" onClick={() => window.location.href = '/analyze'}>
            → Go to Analyze
          </Button>
        </Card>
      ) : (
        <>
          {/* Context pill */}
          <div className="flex items-center gap-2 text-xs px-3 py-2 rounded-full w-fit" style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid var(--color-border)' }}>
            <span style={{ color: 'var(--color-muted)' }}>📄</span>
            <span className="text-slate-400 font-medium">{analysisResult.filename}</span>
            <span style={{ color: 'var(--color-faint)' }}>·</span>
            <span style={{ color: 'var(--color-muted)' }}>🌐 {analysisResult.language}</span>
          </div>

          {/* Suggested questions */}
          {analysisResult.suggested_questions?.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {analysisResult.suggested_questions.map((q, i) => (
                <button
                  key={i}
                  onClick={() => ask(q)}
                  className="text-xs px-3 py-1.5 rounded-full transition-all"
                  style={{ background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.2)', color: 'var(--color-muted)' }}
                  onMouseEnter={e => { (e.target as HTMLElement).style.color = '#818cf8'; (e.target as HTMLElement).style.borderColor = 'rgba(99,102,241,0.4)' }}
                  onMouseLeave={e => { (e.target as HTMLElement).style.color = 'var(--color-muted)'; (e.target as HTMLElement).style.borderColor = 'rgba(99,102,241,0.2)' }}
                >
                  {q}
                </button>
              ))}
            </div>
          )}

          {/* Chat */}
          <Card className="flex flex-col" style={{ minHeight: 480 }}>
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-semibold uppercase tracking-wide" style={{ color: 'var(--color-muted)' }}>Conversation</span>
              {qaHistory.length > 0 && (
                <Button variant="ghost" className="text-xs !px-2 !py-1" onClick={clearQaHistory}>
                  <Trash2 size={12} /> Clear
                </Button>
              )}
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto flex flex-col gap-4 mb-4 pr-1" style={{ maxHeight: 360 }}>
              {qaHistory.length === 0 && (
                <div className="flex-1 flex items-center justify-center text-sm" style={{ color: 'var(--color-muted)' }}>
                  Ask a question to start the conversation
                </div>
              )}
              {qaHistory.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div
                    className="max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed"
                    style={
                      msg.role === 'user'
                        ? { background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', color: 'white', borderBottomRightRadius: 4 }
                        : { background: 'var(--color-elevated)', border: '1px solid var(--color-border)', color: 'rgba(240,242,255,0.9)', borderBottomLeftRadius: 4 }
                    }
                  >
                    {msg.text}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex justify-start">
                  <div className="px-4 py-3 rounded-2xl text-sm" style={{ background: 'var(--color-elevated)', border: '1px solid var(--color-border)', borderBottomLeftRadius: 4 }}>
                    <div className="flex gap-1 items-center" style={{ color: 'var(--color-muted)' }}>
                      <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>

            {/* Input */}
            <div className="flex gap-2 pt-4" style={{ borderTop: '1px solid var(--color-border)' }}>
              <Input
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && ask(input)}
                placeholder="Ask anything about the document…"
                disabled={loading}
              />
              <Button onClick={() => ask(input)} disabled={!input.trim() || loading} className="flex-shrink-0">
                <Send size={15} />
              </Button>
            </div>
          </Card>
        </>
      )}
    </div>
  )
}