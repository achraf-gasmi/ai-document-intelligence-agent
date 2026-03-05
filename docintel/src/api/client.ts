// ─── Types ────────────────────────────────────────────────────────────────────

export interface AnalysisResult {
  filename: string
  raw_text: string
  summary: string
  key_info: string
  risks: string
  risk_score: number
  risk_reasoning: string
  report: string
  language: string
  suggested_questions: string[]
  status: string
  error: string
}

export interface ImprovementIteration {
  iteration: number
  score: number
  critique: string
  improved_text: string
  diff_markers: string
  verdict: string
  remaining: string
}

export interface ImprovementResult {
  filename: string
  doc_type: string
  language: string
  original_text: string
  final_text: string
  diff_markers: string
  improvement_score: number
  total_iterations: number
  improvement_history: ImprovementIteration[]
  improvement_status: string
  thread_id: string
  error: string
}

export interface HistoryEntry {
  id: number
  timestamp: string
  filename: string
  status: string
  summary: string
  key_info: string
  risks: string
  risk_score: number
  report: string
  language: string
  error: string
}

export interface Stats {
  total: number
  successful: number
  failed: number
  avg_risk: number
  recent: HistoryEntry[]
}

// ─── Config ───────────────────────────────────────────────────────────────────

export const API_BASE = 'http://localhost:8000'
export const MOCK_MODE = true

const sleep = (ms: number) => new Promise(r => setTimeout(r, ms))

// ─── Mock Data ────────────────────────────────────────────────────────────────

const MOCK_ANALYSIS: AnalysisResult = {
  filename: 'MSA_Acme_2023.pdf',
  raw_text: 'This Mutual Non-Disclosure Agreement ("Agreement") is entered into as of October 1, 2023...',
  summary: 'A mutual NDA between Acme Corp and Globex Inc. for evaluating a potential software integration partnership. The agreement covers exchange of proprietary technical information and business strategies. Standard boilerplate with notable deviations in liability structure and IP assignment clauses.',
  key_info: '**Parties:** Acme Corp & Globex Inc.\n**Effective Date:** October 1, 2023\n**Term:** 3 years with automatic renewal\n**Jurisdiction:** State of Delaware\n**Governing Law:** Delaware Commercial Code\n**Signatures Required:** Both authorized representatives',
  risks: '**HIGH RISK**\nClause 4.2 implies automatic IP transfer on feedback submissions. Any improvement or suggestion provided during evaluation may be claimed by the disclosing party.\n\n**MEDIUM RISK**\nNo explicit liability cap for data breaches. Standard indemnification clause is asymmetric, favoring the disclosing party disproportionately.\n\n**LOW RISK**\nPerpetual confidentiality obligation post-termination — common but worth noting. Broad definition of confidential information may capture publicly available data.',
  risk_score: 67,
  risk_reasoning: 'Contract contains an IP assignment trap in Clause 4.2 and lacks a liability cap for data incidents.',
  report: '## Document Analysis Report\n\n**Document:** MSA_Acme_2023.pdf\n**Risk Level:** High (67/100)\n**Language:** English\n\n### Executive Summary\nThis NDA presents moderate-to-high risk primarily due to the IP assignment clause and missing liability protections. Immediate legal review is recommended before signing.\n\n### Key Concerns\n1. **IP Assignment (Critical)** — Clause 4.2 automatically transfers intellectual property rights on any feedback, suggestions, or improvements shared during the evaluation period.\n2. **No Liability Cap** — The agreement does not establish a maximum liability for data breaches or confidentiality violations.\n3. **Asymmetric Indemnification** — Receiving party bears disproportionate indemnification obligations.\n\n### Recommendations\n- Renegotiate Clause 4.2 to explicitly exclude IP transfer on verbal or written feedback\n- Add a liability cap of no more than the contract value\n- Rebalance indemnification clauses to be mutual',
  language: 'English',
  suggested_questions: [
    'What does Clause 4.2 say about IP ownership?',
    'Is there a liability cap for data breaches?',
    'What is the governing law for this agreement?'
  ],
  status: 'complete',
  error: ''
}

const MOCK_IMPROVEMENT: ImprovementResult = {
  filename: 'MSA_Acme_2023.pdf',
  doc_type: 'Legal Contract',
  language: 'English',
  original_text: MOCK_ANALYSIS.raw_text,
  final_text: 'This Mutual Non-Disclosure Agreement ("Agreement") is entered into as of October 1, 2023, between Acme Corp and Globex Inc. [IMPROVED] Each party shall hold all Confidential Information in strict confidence using industry-standard security measures including encryption at rest and in transit. [IMPROVED] Neither party shall acquire any intellectual property rights over feedback, suggestions, or improvements shared during the evaluation period. Liability for data breaches shall not exceed the total contract value of USD $50,000. Indemnification obligations are mutual and proportional to each party\'s degree of fault.',
  diff_markers: '[REMOVED]  The receiving party will try to keep things secret.\n[ADDED]    The receiving party shall hold all Confidential Information in strict confidence using industry-standard security measures.\n--- Section ---\n[REMOVED]  Feedback provided during evaluation may be claimed by the disclosing party.\n[ADDED]    Neither party shall acquire any intellectual property rights over feedback or suggestions shared during the evaluation period.\n--- Section ---\n[ADDED]    Liability for data breaches shall not exceed the total contract value of USD $50,000.\n[ADDED]    Indemnification obligations are mutual and proportional to each party\'s degree of fault.',
  improvement_score: 88,
  total_iterations: 2,
  improvement_history: [
    {
      iteration: 1,
      score: 61,
      critique: '1. SECTION: Clause 4.2\nPROBLEM: Automatic IP transfer on feedback is a critical risk\nSEVERITY: Critical\nFIX: Add explicit exclusion of IP transfer for evaluation feedback\n\n2. SECTION: Liability\nPROBLEM: No liability cap defined\nSEVERITY: Major\nFIX: Add a liability cap clause not exceeding contract value',
      improved_text: 'Improved version after iteration 1...',
      diff_markers: '[ADDED]    IP transfer exclusion clause added\n[ADDED]    Initial liability cap draft inserted',
      verdict: 'Critical issues addressed but liability language still ambiguous. Indemnification remains asymmetric.',
      remaining: 'Indemnification balance, liability cap wording needs clarification'
    },
    {
      iteration: 2,
      score: 88,
      critique: '1. SECTION: Indemnification\nPROBLEM: Still slightly favors disclosing party\nSEVERITY: Minor\nFIX: Add proportional fault language',
      improved_text: 'Final improved version...',
      diff_markers: '[ADDED]    Mutual and proportional indemnification language\n[REMOVED]  One-sided indemnification clause',
      verdict: 'Document is now publication-ready. All critical and major issues resolved. Minor stylistic improvements possible.',
      remaining: ''
    }
  ],
  improvement_status: 'done',
  thread_id: 'mock-thread-abc123',
  error: ''
}

const MOCK_HISTORY: HistoryEntry[] = [
  { id: 1, timestamp: '2023-10-01', filename: 'MSA_Acme_2023.pdf',         status: 'complete', risk_score: 45, language: 'English', summary: 'A mutual NDA between Acme Corp and Globex Inc.', key_info: '', risks: '', report: '', error: '' },
  { id: 2, timestamp: '2023-10-05', filename: 'Vendor_Agreement.pdf',       status: 'complete', risk_score: 82, language: 'English', summary: 'Vendor services agreement with unfavorable termination terms.', key_info: '', risks: '', report: '', error: '' },
  { id: 3, timestamp: '2023-10-10', filename: 'Employment_Contract.pdf',    status: 'complete', risk_score: 12, language: 'Spanish', summary: 'Standard employment contract. Low risk.', key_info: '', risks: '', report: '', error: '' },
  { id: 4, timestamp: '2023-10-12', filename: 'Lease_Draft.pdf',            status: 'failed',   risk_score: 95, language: 'English', summary: '', key_info: '', risks: '', report: '', error: 'PDF extraction failed' },
]

const MOCK_STATS: Stats = {
  total: 124, successful: 118, failed: 6, avg_risk: 43.5,
  recent: MOCK_HISTORY
}

// ─── API Client ───────────────────────────────────────────────────────────────

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: { ...(options?.headers ?? {}) }
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

// ─── Public API ───────────────────────────────────────────────────────────────

export async function analyzeDocument(file: File): Promise<AnalysisResult> {
  if (MOCK_MODE) { await sleep(2000 + Math.random() * 500); return { ...MOCK_ANALYSIS, filename: file.name } }
  const form = new FormData()
  form.append('file', file)
  return request<AnalysisResult>('/analyze', { method: 'POST', body: form })
}

export async function askQuestion(question: string, filename: string, language: string): Promise<string> {
  if (MOCK_MODE) {
    await sleep(1200 + Math.random() * 600)
    const answers: Record<string, string> = {
      'What does Clause 4.2 say about IP ownership?': 'Clause 4.2 states that any feedback, suggestions, or improvements shared during the evaluation period may be claimed by the disclosing party as their intellectual property. This is a critical risk that should be renegotiated before signing.',
      'Is there a liability cap for data breaches?': 'No explicit liability cap is defined for data breaches in the current document. This is a medium risk — the receiving party is exposed to unlimited liability in the event of a security incident.',
      'What is the governing law for this agreement?': 'The agreement is governed by the State of Delaware under the Delaware Commercial Code. Disputes are subject to the exclusive jurisdiction of Delaware courts.',
    }
    return answers[question] ?? `Based on the document "${filename}", this question relates to a clause that requires careful legal review. The document is in ${language} and the relevant section appears to address this matter in general terms.`
  }
  return request<{ answer: string }>('/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, filename, language })
  }).then(r => r.answer)
}

export async function improveDocument(file: File | null, existingAnalysis: AnalysisResult | null): Promise<ImprovementResult> {
  if (MOCK_MODE) { await sleep(3000 + Math.random() * 1000); return MOCK_IMPROVEMENT }
  const form = new FormData()
  if (file) form.append('file', file)
  if (existingAnalysis) form.append('existing_analysis', JSON.stringify(existingAnalysis))
  return request<ImprovementResult>('/improve', { method: 'POST', body: form })
}

export async function resumeImprovement(threadId: string): Promise<ImprovementResult> {
  if (MOCK_MODE) { await sleep(1500); return MOCK_IMPROVEMENT }
  return request<ImprovementResult>('/resume', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ thread_id: threadId })
  })
}

export async function getHistory(): Promise<HistoryEntry[]> {
  if (MOCK_MODE) { await sleep(800); return MOCK_HISTORY }
  return request<HistoryEntry[]>('/history')
}

export async function getStats(): Promise<Stats> {
  if (MOCK_MODE) { await sleep(600); return MOCK_STATS }
  return request<Stats>('/stats')
}