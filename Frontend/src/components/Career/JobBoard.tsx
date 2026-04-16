import { useState, useEffect } from 'react'
import { Search, MapPin, Clock, Users, Briefcase, ChevronRight, Star, Filter, X, CheckCircle2, Building2, CalendarDays } from 'lucide-react'
import { useCareerStore, type Job } from '../../store/careerStore'
import { useCareerAPI } from '../../hooks/useCareerAPI'

const DEPT_COLORS: Record<string, string> = {
  Operations:      'bg-blue-500/10 text-blue-400 border-blue-500/20',
  Technology:      'bg-violet-500/10 text-violet-400 border-violet-500/20',
  'Client Services':'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  Marketing:       'bg-orange-500/10 text-orange-400 border-orange-500/20',
  Finance:         'bg-amber-500/10 text-amber-400 border-amber-500/20',
  Content:         'bg-pink-500/10 text-pink-400 border-pink-500/20',
  HR:              'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
}

interface ApplyModalProps {
  job: Job
  onClose: () => void
  onSubmit: (coverNote: string) => void
  loading: boolean
}

function ApplyModal({ job, onClose, onSubmit, loading }: ApplyModalProps) {
  const [note, setNote] = useState('')
  const [submitted, setSubmitted] = useState(false)

  const handleSubmit = async () => {
    await onSubmit(note)
    setSubmitted(true)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm px-4">
      <div className="bg-card border border-border rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden">
        {!submitted ? (
          <>
            <div className="px-6 py-5 border-b border-border flex items-start justify-between">
              <div>
                <p className="text-xs text-amber-400 font-semibold uppercase tracking-widest mb-1">Quick Apply</p>
                <h3 className="text-foreground font-bold text-xl leading-tight">{job.title}</h3>
                <p className="text-muted-foreground text-sm mt-1">{job.department} · {job.location}</p>
              </div>
              <button onClick={onClose} className="text-muted-foreground/80 hover:text-foreground transition-colors mt-1">
                <X size={20} />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                  Cover Note (Optional)
                </label>
                <textarea
                  value={note}
                  onChange={e => setNote(e.target.value)}
                  rows={4}
                  placeholder="Why are you the right fit for this role? (2-3 sentences)"
                  className="w-full bg-secondary/50 border border-border rounded-xl px-4 py-3 text-foreground text-sm placeholder-slate-500 resize-none focus:outline-none focus:border-amber-400/50 transition-colors"
                />
              </div>
              {job.is_internal && (
                <div className="flex items-center gap-2 text-xs text-emerald-400 bg-emerald-400/10 border border-emerald-400/20 rounded-lg px-3 py-2">
                  <Star size={12} fill="currentColor" />
                  Internal posting — eligible for priority review
                </div>
              )}
            </div>
            <div className="px-6 pb-6 flex gap-3">
              <button
                onClick={onClose}
                className="flex-1 py-3 rounded-xl border border-border text-muted-foreground text-sm font-medium hover:bg-secondary/50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmit}
                disabled={loading}
                className="flex-1 py-3 rounded-xl bg-amber-400 text-navy-950 text-sm font-bold hover:bg-amber-300 transition-colors disabled:opacity-60"
                style={{ color: '#0A1628' }}
              >
                {loading ? 'Submitting…' : 'Submit Application'}
              </button>
            </div>
          </>
        ) : (
          <div className="p-10 text-center space-y-4">
            <div className="w-16 h-16 rounded-full bg-emerald-400/15 flex items-center justify-center mx-auto">
              <CheckCircle2 size={32} className="text-emerald-400" />
            </div>
            <h3 className="text-foreground text-xl font-bold">Application Sent!</h3>
            <p className="text-muted-foreground text-sm">Your application for <span className="text-foreground">{job.title}</span> has been received. HR will review within 5 business days.</p>
            <button
              onClick={onClose}
              className="mt-2 px-6 py-2.5 rounded-xl bg-secondary/80 text-foreground text-sm font-medium hover:bg-secondary transition-colors"
            >
              Done
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

interface JobCardProps {
  job: Job
  onSelect: (job: Job) => void
  onApply: (job: Job) => void
}

function JobCard({ job, onSelect, onApply }: JobCardProps) {
  const deptColor = DEPT_COLORS[job.department] || 'bg-slate-500/10 text-muted-foreground border-slate-500/20'
  const daysLeft = Math.ceil((new Date(job.deadline).getTime() - Date.now()) / 86400000)

  return (
    <div className="group relative bg-card border border-border rounded-2xl p-5 hover:border-amber-400/30 transition-all duration-300 hover:shadow-[0_0_30px_rgba(245,158,11,0.06)] cursor-pointer flex flex-col gap-4">
      {job.is_internal && (
        <div className="absolute top-4 right-4 flex items-center gap-1 bg-amber-400/10 border border-amber-400/20 rounded-full px-2.5 py-1">
          <Star size={10} fill="#F59E0B" className="text-amber-400" />
          <span className="text-[10px] text-amber-400 font-bold tracking-wider">INTERNAL</span>
        </div>
      )}

      <div>
        <span className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full border ${deptColor} mb-3`}>
          <Building2 size={10} />
          {job.department}
        </span>
        <h3 className="text-foreground font-bold text-[15px] leading-snug group-hover:text-amber-200 transition-colors pr-12">
          {job.title}
        </h3>
      </div>

      <p className="text-muted-foreground text-xs leading-relaxed line-clamp-2">{job.description}</p>

      <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5"><MapPin size={11} />{job.location}</span>
        <span className="flex items-center gap-1.5"><Briefcase size={11} />{job.type}</span>
        <span className="flex items-center gap-1.5"><Users size={11} />{job.applicants} applied</span>
        <span className={`flex items-center gap-1.5 ${daysLeft < 7 ? 'text-red-400' : ''}`}>
          <CalendarDays size={11} />{daysLeft}d left
        </span>
      </div>

      <div className="flex items-center justify-between pt-2 border-t border-border">
        <span className="text-sm font-semibold text-foreground/70">{job.salary_range}</span>
        <div className="flex gap-2">
          <button
            onClick={(e) => { e.stopPropagation(); onSelect(job) }}
            className="text-xs text-muted-foreground hover:text-foreground px-3 py-1.5 rounded-lg hover:bg-secondary/80 transition-colors"
          >
            Details
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); onApply(job) }}
            className="text-xs font-bold text-white bg-amber-400 hover:bg-amber-300 px-4 py-1.5 rounded-lg transition-colors flex items-center gap-1.5"
          >
            Apply <ChevronRight size={12} />
          </button>
        </div>
      </div>
    </div>
  )
}

interface JobDetailDrawerProps {
  job: Job
  onClose: () => void
  onApply: (job: Job) => void
}

function JobDetailDrawer({ job, onClose, onApply }: JobDetailDrawerProps) {
  const deptColor = DEPT_COLORS[job.department] || 'bg-slate-500/10 text-muted-foreground border-slate-500/20'

  return (
    <div className="fixed inset-0 z-40 flex justify-end">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-md bg-card border-l border-border overflow-y-auto p-8 space-y-6 flex flex-col">
        <div className="flex items-start justify-between">
          <div>
            <span className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full border ${deptColor} mb-3`}>
              {job.department}
            </span>
            <h2 className="text-foreground text-2xl font-bold leading-tight">{job.title}</h2>
            <p className="text-muted-foreground text-sm mt-2">{job.location} · {job.type}</p>
          </div>
          <button onClick={onClose} className="text-muted-foreground/80 hover:text-foreground mt-1 transition-colors">
            <X size={20} />
          </button>
        </div>

        <div className="grid grid-cols-2 gap-3">
          {[
            { label: 'Salary', value: job.salary_range },
            { label: 'Applicants', value: `${job.applicants} applied` },
            { label: 'Posted', value: job.posted },
            { label: 'Deadline', value: job.deadline },
          ].map(({ label, value }) => (
            <div key={label} className="bg-secondary/50 rounded-xl p-3">
              <p className="text-xs text-muted-foreground/80 mb-1">{label}</p>
              <p className="text-sm text-foreground font-semibold">{value}</p>
            </div>
          ))}
        </div>

        <div>
          <h4 className="text-xs font-bold text-muted-foreground uppercase tracking-widest mb-3">About the Role</h4>
          <p className="text-foreground/80 text-sm leading-relaxed">{job.description}</p>
        </div>

        <div>
          <h4 className="text-xs font-bold text-muted-foreground uppercase tracking-widest mb-3">Requirements</h4>
          <ul className="space-y-2">
            {job.requirements.map((req, i) => (
              <li key={i} className="flex items-center gap-2.5 text-sm text-foreground/80">
                <div className="w-1.5 h-1.5 rounded-full bg-amber-400 flex-shrink-0" />
                {req}
              </li>
            ))}
          </ul>
        </div>

        {job.is_internal && (
          <div className="flex items-center gap-3 bg-amber-400/8 border border-amber-400/20 rounded-xl p-4">
            <Star size={16} fill="#F59E0B" className="text-amber-400 flex-shrink-0" />
            <div>
              <p className="text-amber-400 text-sm font-semibold">Internal Priority Posting</p>
              <p className="text-amber-400/70 text-xs mt-0.5">Current NamanDarshan employees get priority review within 48 hours.</p>
            </div>
          </div>
        )}

        <div className="mt-auto pt-4 border-t border-border">
          <button
            onClick={() => onApply(job)}
            className="w-full py-3.5 rounded-xl bg-amber-400 font-bold text-white hover:bg-amber-300 transition-colors flex items-center justify-center gap-2"
          >
            Quick Apply <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  )
}

export default function JobBoard() {
  const { jobs, setJobs, selectedJob, setSelectedJob, jobFilters, setJobFilters } = useCareerStore()
  const { loading, error, fetchJobs, applyToJob } = useCareerAPI()
  const [departments, setDepartments] = useState<string[]>([])
  const [applyingJob, setApplyingJob] = useState<Job | null>(null)
  const [total, setTotal] = useState(0)
  const [showFilters, setShowFilters] = useState(false)

  const loadJobs = async () => {
    const data = await fetchJobs({
      query: jobFilters.query,
      department: jobFilters.department,
      type: jobFilters.type,
    })
    if (data) {
      setJobs(data.jobs)
      setDepartments(data.departments)
      setTotal(data.total)
    }
  }

  useEffect(() => { loadJobs() }, [jobFilters])

  const handleApply = async (coverNote: string) => {
    if (!applyingJob) return
    await applyToJob(applyingJob.id, 'EMP_001', coverNote)
  }

  const typeOptions = [
    { value: 'all', label: 'All Types' },
    { value: 'full-time', label: 'Full-time' },
    { value: 'part-time', label: 'Part-time' },
    { value: 'contract', label: 'Contract' },
  ]

  return (
    <div className="h-full bg-transparent text-foreground">
      {/* Hero Header */}
      <div className="relative overflow-hidden bg-gradient-to-br from-secondary/60 via-background to-secondary/60 border-b border-border">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(245,158,11,0.08),transparent_60%)]" />
        <div className="relative max-w-6xl mx-auto px-6 py-12">
          <div className="max-w-2xl">
            <p className="text-amber-400 text-xs font-bold uppercase tracking-[0.25em] mb-3">NamanDarshan Careers</p>
            <h1 className="text-4xl font-black text-foreground leading-tight mb-3">
              Build Your Career<br />
              <span className="text-amber-400">with Purpose.</span>
            </h1>
            <p className="text-muted-foreground text-base">
              Join a team dedicated to transforming India's pilgrimage experience through technology, service, and devotion.
            </p>
            <div className="mt-6 flex items-center gap-6 text-sm text-muted-foreground">
              <span><span className="text-foreground font-bold">{total}</span> Open Roles</span>
              <span><span className="text-foreground font-bold">{departments.length}</span> Departments</span>
              <span><span className="text-foreground font-bold">Remote Friendly</span></span>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* Search & Filter Bar */}
        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground/80" />
            <input
              type="text"
              placeholder="Search by role, department, or keyword…"
              value={jobFilters.query}
              onChange={e => setJobFilters({ query: e.target.value })}
              className="w-full bg-secondary/50 border border-border rounded-xl pl-11 pr-4 py-3 text-sm text-foreground placeholder-slate-500 focus:outline-none focus:border-amber-400/50 transition-colors"
            />
          </div>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-2 px-4 py-3 rounded-xl border text-sm font-medium transition-colors ${showFilters ? 'border-amber-400/50 text-amber-400 bg-amber-400/8' : 'border-border text-muted-foreground hover:border-border hover:text-foreground'}`}
          >
            <Filter size={15} />
            Filters
          </button>
        </div>

        {showFilters && (
          <div className="flex flex-wrap gap-3 mb-6 p-4 bg-secondary/30 border border-border rounded-xl">
            <div>
              <label className="block text-xs text-muted-foreground/80 mb-1.5">Department</label>
              <select
                value={jobFilters.department}
                onChange={e => setJobFilters({ department: e.target.value })}
                className="bg-card border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-amber-400/50"
              >
                <option value="all">All Departments</option>
                {departments.map(d => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-muted-foreground/80 mb-1.5">Type</label>
              <select
                value={jobFilters.type}
                onChange={e => setJobFilters({ type: e.target.value })}
                className="bg-card border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-amber-400/50"
              >
                {typeOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
            <button
              onClick={() => setJobFilters({ department: 'all', type: 'all', query: '' })}
              className="mt-auto text-xs text-muted-foreground/80 hover:text-foreground flex items-center gap-1 transition-colors"
            >
              <X size={12} /> Clear
            </button>
          </div>
        )}

        {/* Results count */}
        {!loading && (
          <p className="text-xs text-muted-foreground/80 mb-5">{total} position{total !== 1 ? 's' : ''} found</p>
        )}

        {/* Error */}
        {error && (
          <div className="text-center py-12 text-red-400 text-sm">{error}</div>
        )}

        {/* Loading skeleton */}
        {loading && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="bg-secondary/30 border border-border rounded-2xl p-5 animate-pulse space-y-3">
                <div className="h-4 bg-secondary/80 rounded w-24" />
                <div className="h-5 bg-secondary/80 rounded w-3/4" />
                <div className="h-3 bg-secondary/80 rounded w-full" />
                <div className="h-3 bg-secondary/80 rounded w-5/6" />
              </div>
            ))}
          </div>
        )}

        {/* Job Grid */}
        {!loading && jobs.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {jobs.map(job => (
              <JobCard
                key={job.id}
                job={job}
                onSelect={setSelectedJob}
                onApply={setApplyingJob}
              />
            ))}
          </div>
        )}

        {!loading && jobs.length === 0 && !error && (
          <div className="text-center py-20 text-muted-foreground/80">
            <Briefcase size={40} className="mx-auto mb-4 opacity-30" />
            <p className="text-lg font-semibold text-muted-foreground">No positions found</p>
            <p className="text-sm mt-1">Try adjusting your filters or search term.</p>
          </div>
        )}
      </div>

      {/* Modals / Drawers */}
      {selectedJob && (
        <JobDetailDrawer
          job={selectedJob}
          onClose={() => setSelectedJob(null)}
          onApply={(job) => { setSelectedJob(null); setApplyingJob(job) }}
        />
      )}
      {applyingJob && (
        <ApplyModal
          job={applyingJob}
          onClose={() => setApplyingJob(null)}
          onSubmit={handleApply}
          loading={loading}
        />
      )}
    </div>
  )
}
