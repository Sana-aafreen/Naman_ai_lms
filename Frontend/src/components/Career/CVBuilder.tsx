import { useState } from 'react'
import { Plus, Trash2, Download, Sparkles, ChevronDown, ChevronUp, Loader2, TrendingUp, X, CheckCircle2, AlertTriangle, Target } from 'lucide-react'
import { useCareerStore, type CVExperience, type CVEducation } from '../../store/careerStore'
import { useCareerAPI } from '../../hooks/useCareerAPI'

// ── Reusable form primitives ──────────────────────────────────────────────────
const Input = ({
  label, value, onChange, placeholder, type = 'text'
}: { label: string; value: string; onChange: (v: string) => void; placeholder?: string; type?: string }) => (
  <div>
    <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1.5">{label}</label>
    <input
      type={type}
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full bg-secondary/50 border border-border rounded-xl px-3 py-2.5 text-sm text-foreground placeholder-slate-600 focus:outline-none focus:border-amber-400/40 transition-colors"
    />
  </div>
)

const Textarea = ({
  label, value, onChange, placeholder, rows = 3
}: { label: string; value: string; onChange: (v: string) => void; placeholder?: string; rows?: number }) => (
  <div>
    <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1.5">{label}</label>
    <textarea
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      rows={rows}
      className="w-full bg-secondary/50 border border-border rounded-xl px-3 py-2.5 text-sm text-foreground placeholder-slate-600 resize-none focus:outline-none focus:border-amber-400/40 transition-colors"
    />
  </div>
)

// ── ATS Panel ─────────────────────────────────────────────────────────────────
function ATSPanel({ onClose }: { onClose: () => void }) {
  const { cvData, atsResult, setATSResult } = useCareerStore()
  const { optimizeATS, loading } = useCareerAPI()
  const [jd, setJD] = useState('')

  const handleOptimize = async () => {
    if (!jd.trim()) return
    const result = await optimizeATS({ job_description: jd, cv_data: cvData })
    if (result) setATSResult(result)
  }

  const matchColor = {
    strong: 'text-emerald-400',
    moderate: 'text-amber-400',
    weak: 'text-red-400',
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-lg bg-card border-l border-border overflow-y-auto p-6 flex flex-col gap-5">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-violet-400 font-bold uppercase tracking-wider mb-1">ATS Optimizer</p>
            <h3 className="text-foreground text-xl font-bold">Boost Your Score</h3>
          </div>
          <button onClick={onClose} className="text-muted-foreground/80 hover:text-foreground transition-colors">
            <X size={20} />
          </button>
        </div>

        <div>
          <Textarea
            label="Paste Target Job Description"
            value={jd}
            onChange={setJD}
            placeholder="Paste the full job description here…"
            rows={8}
          />
        </div>

        <button
          onClick={handleOptimize}
          disabled={!jd.trim() || loading}
          className="w-full py-3 rounded-xl bg-violet-500 text-foreground font-bold text-sm hover:bg-violet-400 transition-colors disabled:opacity-40 flex items-center justify-center gap-2"
        >
          {loading ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
          {loading ? 'Analyzing with Gemini…' : 'Analyze & Optimize'}
        </button>

        {atsResult && (
          <div className="space-y-4 animate-in slide-in-from-bottom-4">
            {/* Score */}
            <div className="bg-secondary/50 border border-border rounded-xl p-5 text-center">
              <p className="text-xs text-muted-foreground/80 mb-2">Estimated ATS Score</p>
              <div className="flex items-end justify-center gap-1 mb-2">
                <span className="text-5xl font-black text-foreground">{atsResult.ats_score_estimate}</span>
                <span className="text-muted-foreground/80 text-lg mb-2">/100</span>
              </div>
              <span className={`text-sm font-bold capitalize ${matchColor[atsResult.overall_match]}`}>
                {atsResult.overall_match} match
              </span>
            </div>

            {/* Missing Keywords */}
            {atsResult.missing_keywords.length > 0 && (
              <div className="bg-red-500/8 border border-red-500/20 rounded-xl p-4">
                <p className="text-xs font-bold text-red-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                  <AlertTriangle size={12} /> Missing Keywords
                </p>
                <div className="flex flex-wrap gap-2">
                  {atsResult.missing_keywords.map((kw, i) => (
                    <span key={i} className="text-xs bg-red-500/10 border border-red-500/20 text-red-300 px-2.5 py-1 rounded-full">
                      {kw}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Suggested Skills */}
            {atsResult.suggested_skills.length > 0 && (
              <div className="bg-emerald-500/8 border border-emerald-500/20 rounded-xl p-4">
                <p className="text-xs font-bold text-emerald-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                  <TrendingUp size={12} /> Skills to Add
                </p>
                <div className="flex flex-wrap gap-2">
                  {atsResult.suggested_skills.map((s, i) => (
                    <button
                      key={i}
                      onClick={() => {
                        const store = useCareerStore.getState()
                        if (!store.cvData.skills.includes(s)) {
                          store.setCVData({ skills: [...store.cvData.skills, s] })
                        }
                      }}
                      className="text-xs bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 px-2.5 py-1 rounded-full hover:bg-emerald-500/20 transition-colors flex items-center gap-1"
                    >
                      <Plus size={10} /> {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Rewritten Summary */}
            {atsResult.summary_rewrite && (
              <div className="bg-violet-500/8 border border-violet-500/20 rounded-xl p-4">
                <p className="text-xs font-bold text-violet-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                  <Target size={12} /> Optimized Summary
                </p>
                <p className="text-sm text-foreground/80 leading-relaxed">{atsResult.summary_rewrite}</p>
                <button
                  onClick={() => useCareerStore.getState().setCVData({ summary: atsResult.summary_rewrite })}
                  className="mt-3 text-xs text-violet-400 hover:text-violet-300 flex items-center gap-1 transition-colors"
                >
                  <CheckCircle2 size={11} /> Apply to CV
                </button>
              </div>
            )}

            <div className="bg-secondary/50 rounded-xl p-4">
              <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2">Tips</p>
              <p className="text-xs text-muted-foreground leading-relaxed">{atsResult.keyword_density_tips}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ── CV Preview ────────────────────────────────────────────────────────────────
function CVPreview() {
  const { cvData } = useCareerStore()

  return (
    <div className="bg-white text-[#1E293B] rounded-2xl shadow-2xl overflow-hidden font-serif text-sm leading-relaxed h-full">
      {/* Header band */}
      <div className="bg-secondary/40 px-8 py-6">
        <h1 className="text-2xl font-black text-foreground tracking-tight">
          {cvData.full_name || 'Your Name'}
        </h1>
        <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-xs text-foreground/80">
          {cvData.email && <span>{cvData.email}</span>}
          {cvData.phone && <span>{cvData.phone}</span>}
          {cvData.location && <span>{cvData.location}</span>}
        </div>
        {/* Gold divider */}
        <div className="mt-4 h-0.5 bg-amber-400 w-16" />
      </div>

      <div className="px-8 py-6 space-y-5 overflow-y-auto" style={{ maxHeight: 'calc(100% - 120px)' }}>
        {/* Summary */}
        {cvData.summary && (
          <div>
            <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-white border-b border-[#0A1628]/20 pb-1 mb-3">
              Professional Summary
            </h3>
            <p className="text-[11px] leading-relaxed text-slate-600">{cvData.summary}</p>
          </div>
        )}

        {/* Experience */}
        {cvData.experience.some(e => e.title || e.company) && (
          <div>
            <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-white border-b border-[#0A1628]/20 pb-1 mb-3">
              Work Experience
            </h3>
            <div className="space-y-4">
              {cvData.experience.filter(e => e.title || e.company).map((exp, i) => (
                <div key={i}>
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-bold text-[11px] text-white">{exp.title}</p>
                      <p className="text-[10px] text-muted-foreground/80">{exp.company}{exp.location ? ` · ${exp.location}` : ''}</p>
                    </div>
                    <p className="text-[10px] text-muted-foreground whitespace-nowrap">
                      {exp.start && `${exp.start} – ${exp.end || 'Present'}`}
                    </p>
                  </div>
                  {exp.bullets.filter(Boolean).length > 0 && (
                    <ul className="mt-1.5 space-y-1">
                      {exp.bullets.filter(Boolean).map((b, j) => (
                        <li key={j} className="text-[11px] text-slate-600 pl-3 relative before:absolute before:left-0 before:top-[6px] before:w-1.5 before:h-1.5 before:rounded-full before:bg-amber-400">
                          {b}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Education */}
        {cvData.education.some(e => e.degree || e.institution) && (
          <div>
            <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-white border-b border-[#0A1628]/20 pb-1 mb-3">
              Education
            </h3>
            <div className="space-y-2">
              {cvData.education.filter(e => e.degree || e.institution).map((edu, i) => (
                <div key={i} className="flex justify-between">
                  <div>
                    <p className="font-bold text-[11px] text-white">{edu.degree}</p>
                    <p className="text-[10px] text-muted-foreground/80">{edu.institution}</p>
                  </div>
                  <p className="text-[10px] text-muted-foreground">{edu.year}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Skills */}
        {cvData.skills.length > 0 && (
          <div>
            <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-white border-b border-[#0A1628]/20 pb-1 mb-3">
              Skills
            </h3>
            <div className="flex flex-wrap gap-1.5">
              {cvData.skills.map((s, i) => (
                <span key={i} className="text-[10px] bg-secondary/40/8 border border-[#0A1628]/15 text-white px-2 py-0.5 rounded-full">
                  {s}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Certifications */}
        {cvData.certifications.length > 0 && (
          <div>
            <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-white border-b border-[#0A1628]/20 pb-1 mb-3">
              Certifications
            </h3>
            <ul className="space-y-1">
              {cvData.certifications.map((c, i) => (
                <li key={i} className="text-[11px] text-slate-600 pl-3 relative before:absolute before:left-0 before:top-[6px] before:w-1.5 before:h-1.5 before:rounded-full before:bg-amber-400">
                  {c}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Main CV Builder ───────────────────────────────────────────────────────────
export default function CVBuilder() {
  const { cvData, setCVData, resetCV } = useCareerStore()
  const { downloadCVPDF, loading } = useCareerAPI()
  const [showATS, setShowATS] = useState(false)
  const [skillInput, setSkillInput] = useState('')
  const [certInput, setCertInput] = useState('')
  const [expandedSections, setExpandedSections] = useState({ experience: true, education: true, skills: true })

  const toggle = (s: keyof typeof expandedSections) =>
    setExpandedSections(p => ({ ...p, [s]: !p[s] }))

  const updateExp = (i: number, field: keyof CVExperience, value: any) => {
    const exp = [...cvData.experience]
    exp[i] = { ...exp[i], [field]: value }
    setCVData({ experience: exp })
  }

  const updateExpBullet = (ei: number, bi: number, value: string) => {
    const exp = [...cvData.experience]
    const bullets = [...exp[ei].bullets]
    bullets[bi] = value
    exp[ei] = { ...exp[ei], bullets }
    setCVData({ experience: exp })
  }

  const addExp = () => setCVData({
    experience: [...cvData.experience, { title: '', company: '', location: '', start: '', end: '', bullets: [''] }]
  })

  const removeExp = (i: number) => setCVData({ experience: cvData.experience.filter((_, idx) => idx !== i) })

  const updateEdu = (i: number, field: keyof CVEducation, value: string) => {
    const edu = [...cvData.education]
    edu[i] = { ...edu[i], [field]: value }
    setCVData({ education: edu })
  }

  const addSkill = () => {
    if (!skillInput.trim()) return
    setCVData({ skills: [...cvData.skills, skillInput.trim()] })
    setSkillInput('')
  }

  const addCert = () => {
    if (!certInput.trim()) return
    setCVData({ certifications: [...cvData.certifications, certInput.trim()] })
    setCertInput('')
  }

  const SectionHeader = ({ title, section }: { title: string; section: keyof typeof expandedSections }) => (
    <button
      onClick={() => toggle(section)}
      className="w-full flex items-center justify-between py-2 text-left"
    >
      <h3 className="text-xs font-black text-foreground/80 uppercase tracking-[0.2em]">{title}</h3>
      {expandedSections[section] ? <ChevronUp size={14} className="text-muted-foreground/80" /> : <ChevronDown size={14} className="text-muted-foreground/80" />}
    </button>
  )

  return (
    <div className="h-full bg-transparent text-foreground">
      {/* Header */}
      <div className="bg-secondary/40 border-b border-border px-6 py-4 flex items-center justify-between">
        <div>
          <p className="text-xs text-amber-400 font-bold uppercase tracking-[0.2em]">AI CV Builder</p>
          <h2 className="text-foreground font-black text-lg">Resume Studio</h2>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowATS(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-violet-500/15 border border-violet-500/30 text-violet-300 text-sm font-semibold hover:bg-violet-500/25 transition-colors"
          >
            <Sparkles size={14} /> ATS Optimizer
          </button>
          <button
            onClick={() => downloadCVPDF(cvData)}
            disabled={loading || !cvData.full_name}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-amber-400 text-white text-sm font-bold hover:bg-amber-300 transition-colors disabled:opacity-40"
          >
            {loading ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
            Download PDF
          </button>
        </div>
      </div>

      <div className="flex h-[calc(100vh-65px)]">
        {/* LEFT: Input Form */}
        <div className="w-1/2 overflow-y-auto border-r border-border bg-secondary/40">
          <div className="p-6 space-y-6">
            {/* Personal Info */}
            <div className="space-y-4">
              <h3 className="text-xs font-black text-foreground/80 uppercase tracking-[0.2em]">Personal Info</h3>
              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2">
                  <Input label="Full Name" value={cvData.full_name} onChange={v => setCVData({ full_name: v })} placeholder="Sana Khan" />
                </div>
                <Input label="Email" value={cvData.email} onChange={v => setCVData({ email: v })} placeholder="sana@example.com" type="email" />
                <Input label="Phone" value={cvData.phone} onChange={v => setCVData({ phone: v })} placeholder="+91 98765 43210" />
                <div className="col-span-2">
                  <Input label="Location" value={cvData.location} onChange={v => setCVData({ location: v })} placeholder="Patna, Bihar" />
                </div>
              </div>
              <Textarea
                label="Professional Summary"
                value={cvData.summary}
                onChange={v => setCVData({ summary: v })}
                placeholder="2-3 sentences about your experience, strengths, and career goals…"
                rows={3}
              />
            </div>

            <div className="border-t border-border" />

            {/* Experience */}
            <div className="space-y-3">
              <SectionHeader title="Work Experience" section="experience" />
              {expandedSections.experience && (
                <div className="space-y-4">
                  {cvData.experience.map((exp, i) => (
                    <div key={i} className="bg-secondary/30 border border-border rounded-xl p-4 space-y-3">
                      <div className="flex justify-between items-center">
                        <p className="text-xs text-muted-foreground/80 font-semibold">Experience {i + 1}</p>
                        {cvData.experience.length > 1 && (
                          <button onClick={() => removeExp(i)} className="text-red-400/60 hover:text-red-400 transition-colors">
                            <Trash2 size={13} />
                          </button>
                        )}
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <Input label="Job Title" value={exp.title} onChange={v => updateExp(i, 'title', v)} placeholder="Senior Analyst" />
                        <Input label="Company" value={exp.company} onChange={v => updateExp(i, 'company', v)} placeholder="Company Name" />
                        <Input label="Start Date" value={exp.start} onChange={v => updateExp(i, 'start', v)} placeholder="Jan 2022" />
                        <Input label="End Date" value={exp.end} onChange={v => updateExp(i, 'end', v)} placeholder="Present" />
                        <div className="col-span-2">
                          <Input label="Location" value={exp.location} onChange={v => updateExp(i, 'location', v)} placeholder="Remote / Mumbai" />
                        </div>
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Bullet Points</label>
                        <div className="space-y-2">
                          {exp.bullets.map((b, bi) => (
                            <div key={bi} className="flex gap-2">
                              <input
                                value={b}
                                onChange={e => updateExpBullet(i, bi, e.target.value)}
                                placeholder="Achieved X by doing Y, resulting in Z…"
                                className="flex-1 bg-secondary/50 border border-border rounded-lg px-3 py-2 text-xs text-foreground placeholder-slate-600 focus:outline-none focus:border-amber-400/40"
                              />
                              <button
                                onClick={() => {
                                  const exp2 = [...cvData.experience]
                                  exp2[i].bullets = exp2[i].bullets.filter((_, j) => j !== bi)
                                  setCVData({ experience: exp2 })
                                }}
                                className="text-red-400/50 hover:text-red-400 transition-colors"
                              >
                                <Trash2 size={12} />
                              </button>
                            </div>
                          ))}
                          <button
                            onClick={() => {
                              const exp2 = [...cvData.experience]
                              exp2[i].bullets.push('')
                              setCVData({ experience: exp2 })
                            }}
                            className="text-xs text-muted-foreground/80 hover:text-foreground flex items-center gap-1 transition-colors"
                          >
                            <Plus size={11} /> Add bullet
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                  <button
                    onClick={addExp}
                    className="w-full py-2.5 rounded-xl border border-dashed border-white/15 text-xs text-muted-foreground/80 hover:border-amber-400/30 hover:text-amber-400 transition-colors flex items-center justify-center gap-1.5"
                  >
                    <Plus size={13} /> Add Experience
                  </button>
                </div>
              )}
            </div>

            <div className="border-t border-border" />

            {/* Education */}
            <div className="space-y-3">
              <SectionHeader title="Education" section="education" />
              {expandedSections.education && (
                <div className="space-y-3">
                  {cvData.education.map((edu, i) => (
                    <div key={i} className="bg-secondary/30 border border-border rounded-xl p-4">
                      <div className="grid grid-cols-3 gap-2">
                        <div className="col-span-2">
                          <Input label="Degree" value={edu.degree} onChange={v => updateEdu(i, 'degree', v)} placeholder="B.Tech / MBA / B.Com" />
                        </div>
                        <Input label="Year" value={edu.year} onChange={v => updateEdu(i, 'year', v)} placeholder="2020" />
                        <div className="col-span-3">
                          <Input label="Institution" value={edu.institution} onChange={v => updateEdu(i, 'institution', v)} placeholder="University / College Name" />
                        </div>
                      </div>
                    </div>
                  ))}
                  <button
                    onClick={() => setCVData({ education: [...cvData.education, { degree: '', institution: '', year: '' }] })}
                    className="w-full py-2.5 rounded-xl border border-dashed border-white/15 text-xs text-muted-foreground/80 hover:border-amber-400/30 hover:text-amber-400 transition-colors flex items-center justify-center gap-1.5"
                  >
                    <Plus size={13} /> Add Education
                  </button>
                </div>
              )}
            </div>

            <div className="border-t border-border" />

            {/* Skills */}
            <div className="space-y-3">
              <SectionHeader title="Skills" section="skills" />
              {expandedSections.skills && (
                <div className="space-y-3">
                  <div className="flex gap-2">
                    <input
                      value={skillInput}
                      onChange={e => setSkillInput(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && addSkill()}
                      placeholder="Type a skill and press Enter…"
                      className="flex-1 bg-secondary/50 border border-border rounded-xl px-3 py-2.5 text-sm text-foreground placeholder-slate-600 focus:outline-none focus:border-amber-400/40"
                    />
                    <button
                      onClick={addSkill}
                      className="px-3 py-2.5 rounded-xl bg-secondary/80 text-foreground hover:bg-secondary transition-colors"
                    >
                      <Plus size={15} />
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {cvData.skills.map((s, i) => (
                      <span key={i} className="flex items-center gap-1.5 text-xs bg-amber-400/10 border border-amber-400/20 text-amber-300 px-2.5 py-1 rounded-full">
                        {s}
                        <button onClick={() => setCVData({ skills: cvData.skills.filter((_, j) => j !== i) })} className="opacity-60 hover:opacity-100">
                          <X size={10} />
                        </button>
                      </span>
                    ))}
                  </div>

                  {/* Certifications */}
                  <div className="pt-3 border-t border-border">
                    <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Certifications</label>
                    <div className="flex gap-2 mb-2">
                      <input
                        value={certInput}
                        onChange={e => setCertInput(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && addCert()}
                        placeholder="e.g. AWS Solutions Architect"
                        className="flex-1 bg-secondary/50 border border-border rounded-xl px-3 py-2.5 text-sm text-foreground placeholder-slate-600 focus:outline-none focus:border-amber-400/40"
                      />
                      <button onClick={addCert} className="px-3 py-2.5 rounded-xl bg-secondary/80 text-foreground hover:bg-secondary transition-colors">
                        <Plus size={15} />
                      </button>
                    </div>
                    <div className="space-y-1">
                      {cvData.certifications.map((c, i) => (
                        <div key={i} className="flex items-center justify-between text-xs text-foreground/80 py-1 border-b border-white/5">
                          <span>• {c}</span>
                          <button onClick={() => setCVData({ certifications: cvData.certifications.filter((_, j) => j !== i) })} className="text-red-400/50 hover:text-red-400">
                            <Trash2 size={11} />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Reset */}
            <div className="pt-4 border-t border-border">
              <button onClick={resetCV} className="text-xs text-red-400/60 hover:text-red-400 transition-colors flex items-center gap-1">
                <Trash2 size={11} /> Reset CV
              </button>
            </div>
          </div>
        </div>

        {/* RIGHT: Live Preview */}
        <div className="w-1/2 overflow-hidden bg-transparent p-6">
          <div className="mb-3 flex items-center justify-between">
            <p className="text-xs text-muted-foreground/80 uppercase tracking-widest font-bold">Live Preview</p>
            <span className="text-xs text-slate-600">A4 Format</span>
          </div>
          <div className="h-[calc(100%-36px)]">
            <CVPreview />
          </div>
        </div>
      </div>

      {/* ATS Panel */}
      {showATS && <ATSPanel onClose={() => setShowATS(false)} />}
    </div>
  )
}
