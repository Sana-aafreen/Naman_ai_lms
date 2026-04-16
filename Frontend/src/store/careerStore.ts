import { create } from 'zustand'

export interface Job {
  id: string
  title: string
  department: string
  location: string
  type: string
  description: string
  requirements: string[]
  is_internal: boolean
  salary_range: string
  applicants: number
  posted: string
  deadline: string
}

export interface AssessmentResult {
  score: number;
  star_rating: number;
  overall_feedback: string;
  strengths: string[];
  improvements: string[];
  ideal_keywords: string[];
}

export interface InterviewMessage {
  role: 'user' | 'assistant'
  content: string
  assessment?: AssessmentResult
}

export interface CVExperience {
  title: string;
  company: string;
  location: string;
  start: string;
  end: string;
  bullets: string[];
}

export interface CVEducation {
  degree: string;
  institution: string;
  year: string;
}

export interface CVData {
  full_name: string;
  email: string;
  phone: string;
  location: string;
  summary: string;
  experience: CVExperience[];
  education: CVEducation[];
  skills: string[];
  certifications: string[];
}

export interface ATSResult {
  ats_score_estimate: number;
  overall_match: 'strong' | 'moderate' | 'weak';
  missing_keywords: string[];
  suggested_skills: string[];
  summary_rewrite: string;
  keyword_density_tips: string;
}

interface CareerStore {
  jobs: Job[];
  setJobs: (jobs: Job[]) => void;
  selectedJob: Job | null;
  setSelectedJob: (job: Job | null) => void;
  jobFilters: { query: string, department: string, type: string };
  setJobFilters: (filters: Partial<{query: string, department: string, type: string}>) => void;
  
  interviewRole: string;
  interviewDept: string;
  interviewHistory: InterviewMessage[];
  isInterviewActive: boolean;
  setInterviewRole: (role: string, dept: string) => void;
  addInterviewMessage: (msg: InterviewMessage) => void;
  resetInterview: () => void;
  currentQuestion: string;
  setCurrentQuestion: (q: string) => void;

  cvData: CVData;
  setCVData: (data: Partial<CVData>) => void;
  resetCV: () => void;
  atsResult: ATSResult | null;
  setATSResult: (res: ATSResult) => void;
}

const initialCV: CVData = {
  full_name: 'Sana Khan',
  email: 'sana.khan@example.com',
  phone: '+91 98765 43210',
  location: 'Bangalore, India',
  summary: 'Experienced Full-stack engineer looking for a new challenge.',
  experience: [{ title: 'Software Engineer', company: 'Google', location: 'Remote', start: '2021', end: 'Present', bullets: ['Worked on maps'] }],
  education: [{ degree: 'B.Tech', institution: 'IIT Delhi', year: '2020' }],
  skills: ['React', 'Node.js', 'Typescript'],
  certifications: ['AWS Certified Developer']
}

export const useCareerStore = create<CareerStore>((set) => ({
  jobs: [],
  setJobs: (jobs) => set({ jobs }),
  selectedJob: null,
  setSelectedJob: (job) => set({ selectedJob: job }),
  jobFilters: { query: '', department: 'all', type: 'all' },
  setJobFilters: (filters) => set((state) => ({ jobFilters: { ...state.jobFilters, ...filters } })),

  interviewRole: '',
  interviewDept: '',
  interviewHistory: [],
  isInterviewActive: false,
  setInterviewRole: (role, dept) => set({ interviewRole: role, interviewDept: dept, isInterviewActive: true }),
  addInterviewMessage: (msg) => set((state) => ({ interviewHistory: [...state.interviewHistory, msg] })),
  resetInterview: () => set({ interviewRole: '', interviewDept: '', interviewHistory: [], isInterviewActive: false, currentQuestion: '' }),
  currentQuestion: '',
  setCurrentQuestion: (q) => set({ currentQuestion: q }),

  cvData: initialCV,
  setCVData: (data) => set((state) => ({ cvData: { ...state.cvData, ...data } })),
  resetCV: () => set({ cvData: initialCV, atsResult: null }),
  atsResult: null,
  setATSResult: (res) => set({ atsResult: res }),
}))
