import { useState, useRef, useEffect } from 'react'
import { Mic, Send, RotateCcw, Star, TrendingUp, Lightbulb, MessageSquare, ChevronRight, Loader2, Volume2, Award, BookOpen } from 'lucide-react'
import { useCareerStore, type InterviewMessage, type AssessmentResult } from '../../store/careerStore'
import { useCareerAPI } from '../../hooks/useCareerAPI'

const PRESET_ROLES = [
  { role: 'AI/ML Engineer – Darshan Tech', dept: 'Technology' },
  { role: 'Senior Yatra Operations Manager', dept: 'Operations' },
  { role: 'VIP Darshan Relationship Manager', dept: 'Client Services' },
  { role: 'Digital Marketing Lead', dept: 'Marketing' },
  { role: 'Finance & Accounts Executive', dept: 'Finance' },
]

function ScoreRing({ score, max = 10 }: { score: number; max?: number }) {
  const pct = score / max
  const r = 28
  const circ = 2 * Math.PI * r
  const dash = circ * pct
  const color = pct > 0.7 ? '#10B981' : pct > 0.5 ? '#F59E0B' : '#EF4444'

  return (
    <svg width="72" height="72" viewBox="0 0 72 72" className="rotate-[-90deg]">
      <circle cx="36" cy="36" r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="6" />
      <circle
        cx="36" cy="36" r={r} fill="none" stroke={color} strokeWidth="6"
        strokeDasharray={`${dash} ${circ}`} strokeLinecap="round"
        style={{ transition: 'stroke-dasharray 0.8s ease' }}
      />
      <text
        x="36" y="36" textAnchor="middle" dominantBaseline="central"
        fill="white" fontSize="16" fontWeight="bold"
        style={{ transform: 'rotate(90deg)', transformOrigin: '36px 36px' }}
      >
        {score}
      </text>
    </svg>
  )
}

function StarRating({ rating }: { rating: number }) {
  return (
    <div className="flex items-center gap-0.5">
      {Array.from({ length: 5 }).map((_, i) => (
        <Star
          key={i}
          size={14}
          className={i < Math.floor(rating) ? 'text-amber-400' : 'text-foreground/15'}
          fill={i < Math.floor(rating) ? '#F59E0B' : 'none'}
        />
      ))}
      <span className="text-xs text-muted-foreground ml-1">{rating.toFixed(1)}</span>
    </div>
  )
}

function AssessmentCard({ result, question }: { result: AssessmentResult; question: string }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="mt-3 border border-border rounded-xl overflow-hidden bg-secondary/40/60">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-secondary/30 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8">
            <ScoreRing score={result.score} />
          </div>
          <div>
            <p className="text-xs font-bold text-foreground/80">Gemini Assessment</p>
            <StarRating rating={result.star_rating} />
          </div>
        </div>
        <ChevronRight size={14} className={`text-muted-foreground/80 transition-transform ${open ? 'rotate-90' : ''}`} />
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-3 border-t border-border">
          <p className="text-xs text-muted-foreground mt-3 italic">Q: {question}</p>
          <p className="text-sm text-foreground/80">{result.overall_feedback}</p>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <p className="text-xs font-bold text-emerald-400 mb-2 flex items-center gap-1.5"><TrendingUp size={11} /> Strengths</p>
              <ul className="space-y-1">
                {result.strengths.map((s, i) => (
                  <li key={i} className="text-xs text-foreground/80 flex items-start gap-1.5">
                    <span className="text-emerald-400 mt-0.5">+</span>{s}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <p className="text-xs font-bold text-amber-400 mb-2 flex items-center gap-1.5"><Lightbulb size={11} /> Improve</p>
              <ul className="space-y-1">
                {result.improvements.map((s, i) => (
                  <li key={i} className="text-xs text-foreground/80 flex items-start gap-1.5">
                    <span className="text-amber-400 mt-0.5">→</span>{s}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div>
            <p className="text-xs font-bold text-violet-400 mb-2 flex items-center gap-1.5"><BookOpen size={11} /> Keywords to use</p>
            <div className="flex flex-wrap gap-1.5">
              {result.ideal_keywords.map((kw, i) => (
                <span key={i} className="text-xs bg-violet-500/10 border border-violet-500/20 text-violet-300 px-2 py-0.5 rounded-full">
                  {kw}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function MessageBubble({ msg, onAssess, role, assessing }: {
  msg: InterviewMessage
  onAssess?: () => void
  role: string
  assessing?: boolean
}) {
  const isUser = msg.role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} gap-3`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-amber-400/15 border border-amber-400/20 flex items-center justify-center flex-shrink-0 mt-1">
          <span className="text-amber-400 text-xs font-black">A</span>
        </div>
      )}
      <div className={`max-w-[80%] ${isUser ? 'items-end' : 'items-start'} flex flex-col`}>
        <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed ${
          isUser
            ? 'bg-amber-400 text-white rounded-br-sm font-medium'
            : 'bg-secondary/80 text-slate-200 rounded-bl-sm border border-border'
        }`}>
          {msg.content}
        </div>
        {isUser && !msg.assessment && onAssess && (
          <button
            onClick={onAssess}
            disabled={assessing}
            className="mt-1.5 text-[10px] text-violet-400 hover:text-violet-300 flex items-center gap-1 transition-colors disabled:opacity-50"
          >
            {assessing ? <Loader2 size={10} className="animate-spin" /> : <Award size={10} />}
            {assessing ? 'Assessing…' : 'Get AI Assessment'}
          </button>
        )}
        {msg.assessment && (
          <div className="w-full">
            <AssessmentCard result={msg.assessment} question={msg.content} />
          </div>
        )}
      </div>
      {isUser && (
        <div className="w-8 h-8 rounded-full bg-secondary/80 flex items-center justify-center flex-shrink-0 mt-1">
          <span className="text-foreground text-xs font-bold">You</span>
        </div>
      )}
    </div>
  )
}

export default function InterviewPrep() {
  const {
    interviewRole, interviewDept, interviewHistory, isInterviewActive,
    setInterviewRole, addInterviewMessage, resetInterview, currentQuestion, setCurrentQuestion
  } = useCareerStore()

  const { streamInterviewReply, assessAnswer, loading } = useCareerAPI()

  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [assessingIdx, setAssessingIdx] = useState<number | null>(null)
  const [selectedPreset, setSelectedPreset] = useState<typeof PRESET_ROLES[0] | null>(null)
  const [customRole, setCustomRole] = useState('')
  const [customDept, setCustomDept] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [interviewHistory])

  const startInterview = () => {
    const role = selectedPreset?.role || customRole
    const dept = selectedPreset?.dept || customDept
    if (!role || !dept) return
    setInterviewRole(role, dept)
    // Kick off with first interviewer message
    const opener: InterviewMessage = {
      role: 'assistant',
      content: `Namaste! I'm Arjun from NamanDarshan HR. Thank you for your interest in the ${role} position. Let's begin — could you start by telling me a little about yourself and what drew you to NamanDarshan?`,
    }
    addInterviewMessage(opener)
    setCurrentQuestion("Tell me about yourself and why you want to join NamanDarshan.")
  }

  const sendMessage = async () => {
    if (!input.trim() || streaming) return
    const userMsg: InterviewMessage = { role: 'user', content: input.trim() }
    addInterviewMessage(userMsg)
    setInput('')
    setStreaming(true)

    // Placeholder for streaming response
    const placeholderIdx = interviewHistory.length + 1
    addInterviewMessage({ role: 'assistant', content: '' })

    let fullResponse = ''
    await streamInterviewReply(
      { job_role: interviewRole, department: interviewDept, history: interviewHistory.slice(-8), user_answer: input.trim() },
      (chunk) => {
        fullResponse += chunk
        // Update last message in store
        useCareerStore.setState(s => {
          const history = [...s.interviewHistory]
          history[history.length - 1] = { role: 'assistant', content: fullResponse }
          return { interviewHistory: history }
        })
      },
      () => {
        setStreaming(false)
        setCurrentQuestion(fullResponse)
      }
    )
  }

  const handleAssess = async (idx: number) => {
    const msg = interviewHistory[idx]
    if (!msg || msg.role !== 'user') return
    setAssessingIdx(idx)
    const prevAssistantMsg = interviewHistory.slice(0, idx).reverse().find(m => m.role === 'assistant')
    const result = await assessAnswer({
      job_role: interviewRole,
      question: prevAssistantMsg?.content || currentQuestion,
      answer: msg.content,
    })
    if (result) {
      useCareerStore.setState(s => {
        const history = [...s.interviewHistory]
        history[idx] = { ...history[idx], assessment: result }
        return { interviewHistory: history }
      })
    }
    setAssessingIdx(null)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() }
  }

  // ── Setup Screen ──────────────────────────────────────────────────────────
  if (!isInterviewActive) {
    return (
      <div className="h-full bg-transparent text-foreground flex flex-col items-center justify-center px-6 py-16">
        <div className="w-full max-w-2xl space-y-8">
          <div className="text-center">
            <div className="w-16 h-16 rounded-2xl bg-amber-400/10 border border-amber-400/20 flex items-center justify-center mx-auto mb-5">
              <MessageSquare size={28} className="text-amber-400" />
            </div>
            <p className="text-amber-400 text-xs font-bold uppercase tracking-[0.25em] mb-3">AI Interview Prep</p>
            <h1 className="text-3xl font-black text-foreground mb-3">Mock Interview Studio</h1>
            <p className="text-muted-foreground text-sm max-w-md mx-auto">
              Practice with <span className="text-amber-400 font-semibold">Arjun</span> — our Groq-powered HR interviewer. 
              Get real-time conversation + Gemini's structural assessment after each answer.
            </p>
          </div>

          <div className="bg-card border border-border rounded-2xl p-6 space-y-5">
            <div>
              <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-3">Choose a Role to Practice</p>
              <div className="space-y-2">
                {PRESET_ROLES.map(p => (
                  <button
                    key={p.role}
                    onClick={() => { setSelectedPreset(p); setCustomRole(''); setCustomDept('') }}
                    className={`w-full flex items-center justify-between px-4 py-3 rounded-xl border text-sm text-left transition-all ${
                      selectedPreset?.role === p.role
                        ? 'border-amber-400/40 bg-amber-400/8 text-foreground'
                        : 'border-border text-muted-foreground hover:border-white/15 hover:text-foreground hover:bg-secondary/30'
                    }`}
                  >
                    <span>{p.role}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full border ${
                      selectedPreset?.role === p.role
                        ? 'bg-amber-400/15 border-amber-400/30 text-amber-400'
                        : 'bg-secondary/50 border-border text-muted-foreground/80'
                    }`}>{p.dept}</span>
                  </button>
                ))}
              </div>
            </div>

            <div className="relative">
              <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-border" /></div>
              <div className="relative flex justify-center">
                <span className="bg-card px-3 text-xs text-muted-foreground/80">or enter custom</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-muted-foreground/80 mb-1.5">Role Title</label>
                <input
                  value={customRole}
                  onChange={e => { setCustomRole(e.target.value); setSelectedPreset(null) }}
                  placeholder="e.g. HR Manager"
                  className="w-full bg-secondary/50 border border-border rounded-xl px-3 py-2.5 text-sm text-foreground placeholder-slate-500 focus:outline-none focus:border-amber-400/50 transition-colors"
                />
              </div>
              <div>
                <label className="block text-xs text-muted-foreground/80 mb-1.5">Department</label>
                <input
                  value={customDept}
                  onChange={e => { setCustomDept(e.target.value); setSelectedPreset(null) }}
                  placeholder="e.g. HR"
                  className="w-full bg-secondary/50 border border-border rounded-xl px-3 py-2.5 text-sm text-foreground placeholder-slate-500 focus:outline-none focus:border-amber-400/50 transition-colors"
                />
              </div>
            </div>
          </div>

          <div className="flex gap-3">
            <div className="flex-1 bg-card border border-border rounded-2xl p-4 text-center">
              <div className="text-amber-400 font-black text-xl mb-1">⚡ Groq</div>
              <p className="text-xs text-muted-foreground">Real-time streaming<br />conversation</p>
            </div>
            <div className="flex-1 bg-card border border-border rounded-2xl p-4 text-center">
              <div className="text-violet-400 font-black text-xl mb-1">✦ Gemini</div>
              <p className="text-xs text-muted-foreground">Structured answer<br />assessment</p>
            </div>
          </div>

          <button
            onClick={startInterview}
            disabled={!selectedPreset && (!customRole || !customDept)}
            className="w-full py-4 rounded-2xl bg-amber-400 text-white font-black text-base hover:bg-amber-300 transition-colors disabled:opacity-40 flex items-center justify-center gap-2"
          >
            Start Mock Interview <ChevronRight size={18} />
          </button>
        </div>
      </div>
    )
  }

  // ── Interview Screen ──────────────────────────────────────────────────────
  return (
    <div className="h-full bg-transparent text-foreground flex flex-col">
      {/* Header */}
      <div className="bg-secondary/40 border-b border-border px-6 py-4 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-0.5">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs text-emerald-400 font-semibold">Live Session</span>
          </div>
          <p className="text-foreground font-bold text-sm">{interviewRole}</p>
          <p className="text-muted-foreground text-xs">{interviewDept}</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-center">
            <p className="text-xs text-muted-foreground/80">Exchange</p>
            <p className="text-foreground font-bold text-lg">{Math.floor(interviewHistory.length / 2)}</p>
          </div>
          <button
            onClick={resetInterview}
            className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground border border-border hover:border-border px-3 py-2 rounded-lg transition-colors"
          >
            <RotateCcw size={12} /> Reset
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-5 max-w-3xl w-full mx-auto">
        {interviewHistory.map((msg, i) => (
          <MessageBubble
            key={i}
            msg={msg}
            role={interviewRole}
            onAssess={msg.role === 'user' && !msg.assessment ? () => handleAssess(i) : undefined}
            assessing={assessingIdx === i}
          />
        ))}
        {streaming && (
          <div className="flex items-center gap-2 text-muted-foreground/80 text-sm pl-11">
            <Loader2 size={14} className="animate-spin" />
            Arjun is typing…
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="bg-secondary/40 border-t border-border px-4 py-4">
        <div className="max-w-3xl mx-auto flex gap-3 items-end">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={2}
            placeholder="Type your answer… (Enter to send, Shift+Enter for new line)"
            disabled={streaming}
            className="flex-1 bg-secondary/50 border border-border rounded-xl px-4 py-3 text-sm text-foreground placeholder-slate-500 resize-none focus:outline-none focus:border-amber-400/50 transition-colors disabled:opacity-50"
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || streaming}
            className="w-11 h-11 rounded-xl bg-amber-400 text-white flex items-center justify-center hover:bg-amber-300 transition-colors disabled:opacity-40 flex-shrink-0"
          >
            {streaming ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
          </button>
        </div>
        <p className="text-center text-[10px] text-slate-600 mt-2">
          ⚡ Powered by Groq llama-3.3-70b  ·  ✦ Assessments by Gemini 1.5 Pro
        </p>
      </div>
    </div>
  )
}
