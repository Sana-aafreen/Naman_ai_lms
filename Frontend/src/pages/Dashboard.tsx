import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { useAuth } from "@/contexts/AuthContext";
import { apiGet, apiPost } from "@/lib/api";
import { WhatsNewSection } from "@/components/WhatsNewSection";
import { 
  Trophy, 
  CheckCircle2, 
  Clock, 
  Award, 
  Activity, 
  ArrowRight, 
  ChevronRight,
  TrendingUp,
  X,
  BookOpen,
  Calendar as CalendarIcon,
  FileText,
  Briefcase,
  Bot,
  ShieldCheck,
  LayoutDashboard,
  BarChart3,
  Calendar
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

// --- Types ---

interface ProgressReport {
  overallScore: number;
  coursesDone: number;
  learningHours: number;
  departmentRank: string;
}

interface CalendarData {
  meetings?: Array<{
    id: number | null;
    title: string;
    date: string;
    start_time: string;
    end_time: string;
    location?: string;
    meeting_link?: string;
  }>;
}

type UpdateCategory = "Achievement" | "Policy" | "Event" | "Announcement" | "Training" | "Other";

const CATEGORIES: UpdateCategory[] = ["Achievement", "Policy", "Event", "Announcement", "Training", "Other"];

const CHART_DATA = [
  { day: "Mon", hours: 1.5 },
  { day: "Tue", hours: 2.3 },
  { day: "Wed", hours: 1.8 },
  { day: "Thu", hours: 3.2 },
  { day: "Fri", hours: 2.5 },
  { day: "Sat", hours: 0.8 },
  { day: "Sun", hours: 1.2 },
];

const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4, delay, ease: "easeOut" } as const,
});

// --- Subcomponents ---

const StatCard: React.FC<{
  icon: React.ReactNode;
  label: string;
  value: string;
  color: string;
  trend?: string;
  loading?: boolean;
  delay?: number;
}> = ({ icon, label, value, color, trend, loading, delay = 0 }) => (
  <motion.div 
    {...fadeUp(delay)} 
    className="bg-white border border-slate-100 rounded-2xl p-6 group hover:border-amber-200/50 transition-all duration-300 shadow-sm hover:shadow-xl hover:shadow-amber-900/5"
  >
    <div className="flex items-start justify-between mb-5">
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center transition-colors duration-300 ${color} group-hover:bg-amber-50 group-hover:text-[#FF7033]`}>
        {icon}
      </div>
      {trend && (
        <div className="flex items-center gap-1 text-[11px] font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-100/50">
          <TrendingUp className="w-3 h-3" /> {trend}
        </div>
      )}
    </div>
    <div className="min-w-0">
      <div className="text-[11px] text-slate-400 font-bold uppercase tracking-widest mb-1.5">{label}</div>
      <div className="text-2xl font-bold text-slate-800 tracking-tight">{loading ? "..." : value}</div>
    </div>
  </motion.div>
);

const ActivityChart: React.FC = () => (
  <div className="h-[160px] w-full mt-2">
    <ResponsiveContainer width="99%" height={160}>
      <AreaChart data={CHART_DATA}>
        <defs>
          <linearGradient id="colorHours" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#FBBD23" stopOpacity={0.1}/>
            <stop offset="95%" stopColor="#FF7033" stopOpacity={0}/>
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
        <XAxis 
          dataKey="day" 
          axisLine={false} 
          tickLine={false} 
          tick={{ fontSize: 10, fill: "#64748b", fontWeight: 500 }}
          dy={10}
        />
        <YAxis hide domain={[0, 'dataMax + 1']} />
        <Tooltip 
          contentStyle={{ 
            borderRadius: '12px', 
            border: '1px solid #f1f5f9', 
            boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
            fontSize: '11px',
            fontWeight: '600'
          }} 
        />
        <Area 
          type="monotone" 
          dataKey="hours" 
          stroke="#FF7033" 
          strokeWidth={3}
          fillOpacity={1} 
          fill="url(#colorHours)" 
        />
      </AreaChart>
    </ResponsiveContainer>
  </div>
);

const WelcomeHero: React.FC<{ name: string; department: string }> = ({ name, department }) => (
  <motion.div 
    initial={{ opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    className="bg-white border border-slate-100 p-10 mb-10 rounded-[2rem] overflow-hidden relative shadow-sm group"
  >
    <div className="absolute inset-0 mandala-subtle opacity-[0.02]" />
    <div className="absolute top-0 right-0 w-[400px] h-[400px] bg-amber-50/50 blur-[100px] -mr-32 -mt-32 rounded-full group-hover:scale-110 duration-1000 transition-transform" />
    
    <div className="relative z-10 flex flex-col lg:flex-row lg:items-center gap-12">
      <div className="flex-1">
        <div className="flex items-center gap-3 mb-6">
          <span className="px-3 py-1 rounded-lg bg-slate-50 text-slate-500 border border-slate-100 text-[10px] font-bold uppercase tracking-widest flex items-center gap-2">
            <Activity className="w-3.5 h-3.5" /> Stability: 98.4%
          </span>
          <span className="px-3 py-1 rounded-lg bg-amber-50 text-amber-700 border border-amber-100 text-[10px] font-bold uppercase tracking-widest">
            Level 4 Practitioner
          </span>
        </div>
        
        <h1 className="text-4xl md:text-5xl font-bold text-slate-900 mb-6 tracking-tight">
          Welcome back, <span className="text-[#FF7033]">{name.split(" ")[0]}</span>.
        </h1>
        
        <p className="text-slate-500 text-lg mb-10 leading-relaxed max-w-2xl font-medium">
          You've maintained exceptional progress in <span className="text-slate-900 font-semibold">{department}</span>. Complete your current module to unlock the next certification tier.
        </p>
        
        <div className="flex flex-wrap gap-4">
          <Link 
            to="/training" 
            className="enterprise-btn-primary flex items-center gap-3 shadow-none hover:shadow-lg transition-all"
          >
            Continue Learning <ArrowRight className="w-4 h-4" />
          </Link>
          <div className="hidden sm:flex items-center gap-8 px-8 py-3 bg-slate-50 border border-slate-100 rounded-xl">
            <div>
              <div className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">Skill Growth</div>
              <div className="text-lg font-bold text-slate-800 flex items-center gap-1.5">
                +12% <TrendingUp className="w-4 h-4 text-emerald-500" />
              </div>
            </div>
            <div className="w-px h-8 bg-slate-200" />
            <div>
              <div className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">Global Rank</div>
              <div className="text-lg font-bold text-slate-800">Top 5%</div>
            </div>
          </div>
        </div>
      </div>
      
      <div className="hidden xl:block w-[320px] h-[200px] bg-slate-50/50 rounded-2xl border border-slate-100 p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 leading-none">Learning Activity</div>
          <div className="text-[10px] font-bold text-emerald-600 bg-white px-2 py-0.5 rounded-full border border-emerald-100 shadow-sm">+2.4h Today</div>
        </div>
        <ActivityChart />
      </div>
    </div>
  </motion.div>
);

const SectionHeader: React.FC<{
  title: string;
  linkTo?: string;
  linkLabel?: string;
  action?: React.ReactNode;
}> = ({ title, linkTo, linkLabel, action }) => (
  <div className="flex items-center justify-between mb-8">
    <div className="flex items-center gap-3">
      <div className="w-1.5 h-6 bg-amber-400 rounded-full" />
      <h2 className="text-lg font-bold text-slate-800 tracking-tight">{title}</h2>
    </div>
    <div className="flex items-center gap-6">
      {action}
      {linkTo && (
        <Link to={linkTo} className="text-[13px] font-semibold text-amber-600 hover:text-amber-700 flex items-center gap-1.5 transition-all group">
          {linkLabel ?? "View All"} <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
        </Link>
      )}
    </div>
  </div>
);

const EmptyState: React.FC<{ message: string }> = ({ message }) => (
  <div className="py-12 text-center border-2 border-dashed border-slate-100 rounded-2xl bg-slate-50/30">
    <Bot className="w-8 h-8 text-slate-200 mx-auto mb-3" />
    <p className="text-[12px] text-slate-400 font-medium">{message}</p>
  </div>
);

const UpdateComposerModal: React.FC<{
  open: boolean;
  onClose: () => void;
  onSubmit: (data: { title: string; body: string; category: UpdateCategory }) => Promise<void>;
}> = ({ open, onClose, onSubmit }) => {
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [category, setCategory] = useState<UpdateCategory>("Announcement");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!title || !body) return;
    setSubmitting(true);
    try { await onSubmit({ title, body, category }); setTitle(""); setBody(""); onClose(); }
    finally { setSubmitting(false); }
  };

  const handleClose = () => { setTitle(""); setBody(""); onClose(); };

  return (
    <AnimatePresence>
      {open && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-[100] flex items-center justify-center p-6 bg-slate-900/40 backdrop-blur-sm">
          <motion.div initial={{ scale: 0.95, y: 20 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.95, y: 20 }} className="bg-white rounded-3xl w-full max-w-lg p-8 shadow-2xl overflow-hidden relative">
            <div className="absolute top-0 right-0 w-32 h-32 bg-amber-50/50 blur-[60px] -mr-16 -mt-16 rounded-full" />
            <div className="relative z-10">
              <div className="flex items-center justify-between mb-8">
                 <h2 className="text-xl font-bold text-slate-900 tracking-tight">Post New Update</h2>
                 <button onClick={handleClose} className="p-2 hover:bg-slate-50 rounded-full transition-colors"><X className="w-5 h-5 text-slate-400" /></button>
              </div>
              <div className="space-y-6">
                <div>
                  <label className="text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-3 block">Category</label>
                  <div className="flex flex-wrap gap-2">
                    {CATEGORIES.map((cat) => (
                      <button key={cat} onClick={() => setCategory(cat)} className={`px-4 py-2 rounded-lg text-[11px] font-bold transition-all ${category === cat ? "bg-[#30231D] text-white shadow-md shadow-slate-900/10" : "bg-slate-50 text-slate-400 hover:text-slate-600 border border-slate-100"}`}>{cat}</button>
                    ))}
                  </div>
                </div>
                <input type="text" placeholder="Title of transmission..." value={title} onChange={(e) => setTitle(e.target.value)} className="w-full bg-slate-50/50 border border-slate-100 rounded-xl px-4 py-3 text-sm font-semibold text-slate-900 outline-none focus:bg-white focus:border-amber-200 transition-all" />
                <textarea placeholder="Write your update content here..." value={body} onChange={(e) => setBody(e.target.value)} rows={4} className="w-full bg-slate-50/50 border border-slate-100 rounded-xl px-4 py-3 text-sm font-medium text-slate-600 outline-none focus:bg-white focus:border-amber-200 transition-all resize-none" />
              </div>
              <div className="flex gap-4 mt-10">
                <button onClick={handleClose} className="flex-1 py-3.5 rounded-xl border border-slate-100 text-sm font-bold text-slate-400 hover:bg-slate-50 transition-all">Cancel</button>
                <button disabled={submitting} onClick={handleSubmit} className="flex-1 py-3.5 rounded-xl bg-[#30231D] text-white text-sm font-bold shadow-lg shadow-slate-900/10 hover:shadow-xl hover:brightness-110 transition-all">{submitting ? "Processing..." : "Publish Post"}</button>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

// --- Main Dashboard ---

const Dashboard: React.FC = () => {
  const { user, hasRole } = useAuth();
  const isAdminOrManager = user?.role === "Admin" || user?.role === "Manager";

  const [report, setReport] = useState<ProgressReport | null>(null);
  const [calendarData, setCalendarData] = useState<CalendarData | null>(null);
  const [loading, setLoading] = useState(true);
  const [composerOpen, setComposerOpen] = useState(false);

  useEffect(() => {
    const today = new Date();
    const year = today.getFullYear();
    const month = today.getMonth() + 1;
    
    Promise.all([
      apiGet<ProgressReport>("/api/progress-report"),
      apiGet<CalendarData>(`/api/calendar?year=${year}&month=${month}`)
    ]).then(([p, c]) => {
      setReport(p);
      setCalendarData(c);
    }).finally(() => setLoading(false));
  }, []);

  const handleSubmitUpdate = async (data: { title: string; body: string; category: UpdateCategory }) => {
    await apiPost("/api/whats-new", { ...data, author_id: user?.id, author_name: user?.name, author_role: user?.role, department: user?.department });
  };

  const quickLinks = [
    { icon: <BookOpen className="w-5 h-5" />, label: "Courses", to: "/courses", color: "text-amber-500" },
    { icon: <Briefcase className="w-5 h-5" />, label: "Career", to: "/career", color: "text-blue-500" },
    { icon: <CalendarIcon className="w-5 h-5" />, label: "Holdays", to: "/holidays", color: "text-emerald-500" },
    { icon: <FileText className="w-5 h-5" />, label: "Leaves", to: "/leaves", color: "text-rose-500" },
    { icon: <BarChart3 className="w-5 h-5" />, label: "Analytics", to: "/progress", color: "text-indigo-500" },
    { icon: <Bot className="w-5 h-5" />, label: "AI Help", to: "/ai", color: "text-purple-500" },
    { icon: <TrendingUp className="w-5 h-5" />, label: isAdminOrManager ? "KPI Mgr" : "My KPI", to: "/kpi", color: "text-violet-500" },
    ...(isAdminOrManager ? [{ icon: <ShieldCheck className="w-5 h-5" />, label: "Admin", to: "/admin", color: "text-slate-800" }] : []),
    ...(isAdminOrManager ? [{ icon: <LayoutDashboard className="w-5 h-5" />, label: "SOPs", to: "/sop", color: "text-amber-800" }] : []),
  ];

  return (
    <>
      <UpdateComposerModal open={composerOpen} onClose={() => setComposerOpen(false)} onSubmit={handleSubmitUpdate} />
      <div className="pb-20 max-w-[1280px] mx-auto px-4 md:px-6">
        <motion.div {...fadeUp(0)} className="mb-8 pt-6">
          <div className="text-[10px] text-slate-400 font-bold uppercase tracking-[0.25em] flex items-center gap-2">
            Main <ChevronRight className="w-3 h-3" /> <span className="text-slate-800 font-black">Overview</span>
          </div>
        </motion.div>

        <WelcomeHero name={user?.name ?? "User"} department={user?.department ?? "Organization"} />

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
          <StatCard icon={<Trophy className="w-5 h-5" />} label="Avg Score" value={`${report?.overallScore ?? 0}%`} color="text-amber-500" trend="+4.2%" loading={loading} delay={0.05} />
          <StatCard icon={<CheckCircle2 className="w-5 h-5" />} label="Modules Done" value={`${report?.coursesDone ?? 0}`} color="text-emerald-500" loading={loading} delay={0.1} />
          <StatCard icon={<Clock className="w-5 h-5" />} label="Learn Time" value={`${report?.learningHours ?? 0}h`} color="text-blue-500" trend="+1.5h" loading={loading} delay={0.15} />
          <StatCard icon={<Award className="w-5 h-5" />} label="Dept Rank" value={report?.departmentRank ?? "..."} color="text-purple-500" loading={loading} delay={0.2} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-10">
          <div className="space-y-10">
            <motion.div {...fadeUp(0.25)} className="enterprise-card p-10 bg-white">
              <SectionHeader title="Operational Shortcuts" />
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-6">
                {quickLinks.map((link, i) => (
                  <Link key={i} to={link.to} className="flex flex-col items-center gap-4 group">
                    <div className={`w-16 h-16 rounded-2xl bg-slate-50 border border-slate-100 flex items-center justify-center ${link.color} shadow-sm group-hover:bg-white group-hover:border-amber-200 group-hover:shadow-xl group-hover:shadow-amber-900/5 transition-all duration-300`}>{link.icon}</div>
                    <span className="text-[12px] font-semibold text-slate-500 group-hover:text-slate-800 transition-colors">{link.label}</span>
                  </Link>
                ))}
              </div>
            </motion.div>

            <motion.div {...fadeUp(0.3)} className="enterprise-card p-10 bg-white">
              <SectionHeader title="Your Agenda" linkTo="/holidays" linkLabel="FULL CALENDAR" />
              {loading ? <EmptyState message="Synchronizing calendar data..." /> : (calendarData?.meetings?.length ?? 0) === 0 ? <EmptyState message="No scheduled events for today." /> : (
                <div className="space-y-2">
                  {calendarData?.meetings?.slice(0, 4).map((m, i) => (
                    <div key={i} className="flex items-center gap-6 p-4 rounded-2xl hover:bg-slate-50 border border-transparent hover:border-slate-100 transition-all group">
                      <div className="w-14 h-14 rounded-xl bg-[#30231D] text-white flex flex-col items-center justify-center shadow-lg">
                        <div className="text-[9px] font-black uppercase opacity-60 leading-none mb-1">{new Date(m.date).toLocaleDateString("en", { month: "short" })}</div>
                        <div className="text-xl font-bold leading-none">{new Date(m.date).getDate()}</div>
                      </div>
                      <div className="flex-1 min-w-0">
                        <h4 className="text-[15px] font-bold text-slate-800 group-hover:text-[#FF7033] transition-colors truncate">{m.title}</h4>
                        <div className="flex items-center gap-3 mt-1.5 text-[11px] font-medium text-slate-400"><Clock className="w-3.5 h-3.5" /> {m.start_time} - {m.end_time}</div>
                      </div>
                      <ChevronRight className="w-5 h-5 text-slate-200 group-hover:translate-x-1 transition-all" />
                    </div>
                  ))}
                </div>
              )}
            </motion.div>
          </div>

          <div className="space-y-10">
            <motion.div {...fadeUp(0.35)} className="enterprise-card p-8 bg-white">
              <SectionHeader title="New Updates" action={<button onClick={() => setComposerOpen(true)} className="w-10 h-10 bg-emerald-50 text-emerald-600 rounded-lg flex items-center justify-center hover:bg-emerald-600 hover:text-white transition-all"><ArrowRight className="w-5 h-5 -rotate-45" /></button>} />
              <WhatsNewSection 
                isAdmin={hasRole("Admin")} 
                currentUser={user} 
                onOpenComposer={() => setComposerOpen(true)} 
              />
            </motion.div>

            <motion.div {...fadeUp(0.4)} className="enterprise-card p-8 bg-white">
              <SectionHeader title="Skill Velocity" linkTo="/progress" />
              <div className="space-y-7">
                {[
                  { name: "Strategic Intelligence", score: 92, color: "from-amber-400 to-amber-500" },
                  { name: "Technical Aptitude", score: 78, color: "from-blue-400 to-blue-500" },
                  { name: "Operational Flow", score: 96, color: "from-emerald-400 to-emerald-500" },
                  { name: "Brand Culture", score: 85, color: "from-slate-700 to-slate-800" },
                ].map((s, i) => (
                  <div key={i}>
                    <div className="flex justify-between items-center text-[11px] font-bold text-slate-500 mb-2.5"><span>{s.name}</span><span className="text-slate-900">{s.score}%</span></div>
                    <div className="h-2 bg-slate-50 border border-slate-100 p-0.5 rounded-full">
                      <motion.div initial={{ width: 0 }} animate={{ width: `${s.score}%` }} transition={{ duration: 1, delay: 0.5 + (i * 0.1) }} className={`h-full bg-gradient-to-r ${s.color} rounded-full`} />
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    </>
  );
};

export default Dashboard;
