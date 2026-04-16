import { useState } from 'react'
import { Briefcase, MessageSquare, FileText } from 'lucide-react'
import JobBoard from './JobBoard'
import InterviewPrep from './InterviewPrep'
import CVBuilder from './CVBuilder'

type Tab = 'jobs' | 'interview' | 'cv'

const TABS = [
  { id: 'jobs' as Tab,      label: 'Job Board',      icon: Briefcase,     desc: 'Browse open roles' },
  { id: 'interview' as Tab, label: 'Interview Prep', icon: MessageSquare, desc: 'AI mock interviews' },
  { id: 'cv' as Tab,        label: 'CV Builder',     icon: FileText,      desc: 'Build & optimize' },
]

export default function CareerPortal() {
  const [activeTab, setActiveTab] = useState<Tab>('jobs')

  return (
    <div className="flex flex-col h-full text-foreground animate-in fade-in duration-300">
      {/* Page header */}
      <div className="mb-5">
        <div className="text-[11px] text-muted-foreground mb-2">
          Home <span className="text-saffron">/ Career Portal</span>
        </div>
        <h1 className="text-xl font-bold mb-1">Career Portal</h1>
        <p className="text-[13px] text-muted-foreground">
          Browse open roles, prepare for internal interviews with AI, and enhance your resume.
        </p>
      </div>

      {/* Tab bar */}
      <div className="flex flex-wrap gap-0.5 bg-secondary rounded-lg p-[3px] w-fit mb-5">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex items-center gap-2 px-4 py-[7px] text-xs rounded-[7px] font-medium transition-all ${activeTab === id ? "bg-card shadow-sm text-foreground" : "text-muted-foreground hover:bg-secondary/80"}`}
          >
            <Icon size={14} />
            {label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-visible">
        {activeTab === 'jobs'      && <JobBoard />}
        {activeTab === 'interview' && <InterviewPrep />}
        {activeTab === 'cv'        && <CVBuilder />}
      </div>
    </div>
  )
}
