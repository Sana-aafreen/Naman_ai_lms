import React, { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";
import { 
  Trophy, 
  Target, 
  TrendingUp, 
  Award, 
  CheckCircle2, 
  Clock, 
  BarChart3, 
  Medal,
  Activity,
  ChevronRight,
  Sparkles,
  Zap,
  ShieldCheck
} from "lucide-react";
import { motion } from "framer-motion";

interface ProgressReport {
  overallScore: number;
  coursesDone: number;
  learningHours: number;
  departmentRank: string;
  skills: Array<{ name: string; score: number; color: string }>;
  badges: Array<{ icon: string; title: string; desc: string }>;
  completedCourses: Array<{
    course_id: number;
    title: string;
    department: string;
    score: number;
    completed_at: string;
    status: string;
  }>;
}

const fallbackReport: ProgressReport = {
  overallScore: 0,
  coursesDone: 0,
  learningHours: 0,
  departmentRank: "-",
  skills: [],
  badges: [],
  completedCourses: [],
};

const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4, delay, ease: "easeOut" },
});

const MyProgress: React.FC = () => {
  const [report, setReport] = useState<ProgressReport>(fallbackReport);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchReport = async () => {
      setLoading(true);
      try {
        const data = await apiGet<ProgressReport>("/api/progress-report");
        setReport(data);
      } catch (error) {
        setReport(fallbackReport);
      } finally {
        setLoading(false);
      }
    };
    void fetchReport();
  }, []);

  return (
    <div className="pb-20 max-w-[1280px] mx-auto px-6">
      <header className="mb-12 pt-6">
        <div className="text-[10px] text-slate-400 font-bold uppercase tracking-[0.25em] mb-6 flex items-center gap-2">
          Performance Analytics <ChevronRight className="w-3 h-3" /> <span className="text-slate-800 font-black">Growth Intelligence</span>
        </div>
        <div>
          <h1 className="text-4xl font-bold text-slate-900 mb-4 tracking-tight">Performance Portfolio</h1>
          <p className="text-lg text-slate-500 font-medium max-w-3xl leading-relaxed">
            Audit your institutional competency accretion, milestone achievements, and professional ranking.
          </p>
        </div>
      </header>

      {/* Primary KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
        {[
          { icon: <Target className="w-6 h-6" />, label: "Competency Index", value: `${report.overallScore}%`, color: "text-[#FF7033]", bg: "bg-amber-50", border: "border-amber-100" },
          { icon: <CheckCircle2 className="w-6 h-6" />, label: "Modules Cleared", value: String(report.coursesDone), color: "text-emerald-600", bg: "bg-emerald-50", border: "border-emerald-100" },
          { icon: <Clock className="w-6 h-6" />, label: "Investment Hours", value: `${report.learningHours}H`, color: "text-slate-700", bg: "bg-slate-50", border: "border-slate-100" },
          { icon: <TrendingUp className="w-6 h-6" />, label: "Department Rank", value: report.departmentRank, color: "text-slate-900", bg: "bg-slate-100", border: "border-slate-200" },
        ].map((s, i) => (
          <motion.div 
            key={i} 
            {...fadeUp(i * 0.05)}
            className="bg-white border border-slate-100 rounded-2xl p-8 flex flex-col items-center text-center group hover:border-amber-200/50 hover:shadow-xl hover:shadow-amber-900/5 transition-all"
          >
            <div className={`w-14 h-14 rounded-xl flex items-center justify-center mb-6 ${s.bg} ${s.color} border ${s.border} shadow-sm group-hover:scale-105 transition-transform`}>
              {s.icon}
            </div>
            <div className="text-[11px] text-slate-400 font-bold uppercase tracking-widest mb-2">{s.label}</div>
            <div className={`text-3xl font-bold tracking-tight text-slate-900`}>{loading ? "..." : s.value}</div>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_400px] gap-10 mb-10">
        {/* Growth Matrix */}
        <motion.div {...fadeUp(0.2)} className="bg-white border border-slate-100 rounded-3xl p-10 relative shadow-sm">
          <div className="absolute top-0 right-0 w-32 h-32 bg-amber-50/20 blur-3xl rounded-full" />
          <div className="flex items-center justify-between mb-10">
            <div className="flex items-center gap-3">
              <div className="w-1.5 h-6 bg-amber-400 rounded-full" />
              <h2 className="text-lg font-bold text-slate-800 tracking-tight">Competency Matrix</h2>
            </div>
            <BarChart3 className="w-5 h-5 text-slate-200" />
          </div>
          
          <div className="space-y-8">
            { (report?.skills?.length ?? 0) === 0 ? (
              <div className="py-24 text-center border-2 border-dashed border-slate-50 rounded-2xl bg-slate-50/30">
                <Zap className="w-10 h-10 text-slate-100 mx-auto mb-4" />
                <p className="text-[12px] text-slate-400 font-medium">No skill data identified yet. Engage modules to initialize.</p>
              </div>
            ) : (
              (report?.skills ?? []).map((s, i) => (
                <div key={i} className="group/skill">
                  <div className="flex items-center justify-between text-[11px] font-bold uppercase tracking-widest mb-2.5">
                    <span className="text-slate-500 group-hover/skill:text-amber-600 transition-colors">{s.name}</span>
                    <span className="text-slate-300">{s.score}%</span>
                  </div>
                  <div className="h-2 bg-slate-50 rounded-full overflow-hidden p-0.5 border border-slate-100 shadow-inner">
                    <motion.div 
                      initial={{ width: 0 }}
                      animate={{ width: `${s.score}%` }}
                      transition={{ duration: 1.5, delay: i * 0.1 }}
                      className="h-full rounded-full transition-all brand-gradient"
                    />
                  </div>
                </div>
              ))
            )}
          </div>
        </motion.div>

        {/* Badges */}
        <motion.div {...fadeUp(0.25)} className="bg-white border border-slate-100 rounded-3xl p-10 shadow-sm relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-amber-50/10 blur-3xl rounded-full" />
          <div className="flex items-center justify-between mb-10">
            <div className="flex items-center gap-3">
              <div className="w-1.5 h-6 bg-slate-800 rounded-full" />
              <h2 className="text-lg font-bold text-slate-800 tracking-tight">Milestone Vault</h2>
            </div>
            <Award className="w-5 h-5 text-slate-200" />
          </div>

          <div className="grid grid-cols-1 gap-4">
            {(report?.badges?.length ?? 0) === 0 ? (
              <div className="py-24 text-center border-2 border-dashed border-slate-50 rounded-2xl bg-slate-50/30">
                <Medal className="w-10 h-10 text-slate-100 mx-auto mb-4" />
                <p className="text-[12px] text-slate-400 font-medium">Badge protocols not yet fulfilled.</p>
              </div>
            ) : (
              (report?.badges ?? []).map((b, i) => (
                <div key={i} className="flex items-center gap-5 p-5 rounded-2xl border border-slate-50 bg-slate-50/30 hover:bg-white hover:border-amber-100 hover:shadow-lg hover:shadow-amber-900/5 transition-all group">
                  <div className="w-14 h-14 rounded-xl bg-white border border-slate-100 flex items-center justify-center text-3xl shadow-sm group-hover:scale-110 transition-transform">
                    {b.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-[14px] font-bold text-slate-800 group-hover:text-amber-600 transition-colors">{b.title}</div>
                    <div className="text-[11px] text-slate-400 font-medium leading-relaxed mt-0.5">{b.desc}</div>
                  </div>
                </div>
              ))
            )}
          </div>
        </motion.div>
      </div>

      {/* History Table */}
      <motion.div {...fadeUp(0.3)} className="bg-white border border-slate-100 rounded-3xl p-10 relative overflow-hidden shadow-sm">
        <div className="flex items-center justify-between mb-10">
          <div className="flex items-center gap-3">
            <div className="w-1.5 h-6 bg-slate-900 rounded-full" />
            <h2 className="text-lg font-bold text-slate-800 tracking-tight">Operational Archives</h2>
          </div>
          <Activity className="w-5 h-5 text-slate-200" />
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-50">
                <th className="pb-5 text-left text-[11px] font-bold text-slate-400 uppercase tracking-widest">Asset Designation</th>
                <th className="pb-5 text-left text-[11px] font-bold text-slate-400 uppercase tracking-widest">Department</th>
                <th className="pb-5 text-left text-[11px] font-bold text-slate-400 uppercase tracking-widest">Proficiency</th>
                <th className="pb-5 text-left text-[11px] font-bold text-slate-400 uppercase tracking-widest">Completed On</th>
                <th className="pb-5"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50/50">
              { (report?.completedCourses?.length ?? 0) === 0 ? (
                <tr>
                  <td colSpan={5} className="py-20 text-center text-slate-300 font-medium text-[13px]">
                    No strategic records identified in current directory.
                  </td>
                </tr>
              ) : (
                (report?.completedCourses ?? []).map((course, i) => (
                  <tr key={i} className="group hover:bg-slate-50/50 transition-all cursor-pointer">
                    <td className="py-7 font-bold text-[15px] text-slate-800 group-hover:text-amber-600 transition-colors tracking-tight">{course.title}</td>
                    <td className="py-7 text-[12px] font-semibold text-slate-500">{course.department}</td>
                    <td className="py-7">
                      <div className="flex items-center gap-4">
                         <div className="text-sm font-bold text-emerald-600">{course.score}%</div>
                         <div className="w-24 h-1.5 bg-slate-50 rounded-full overflow-hidden border border-slate-100 shadow-inner">
                           <div className="h-full bg-emerald-500 rounded-full shadow-sm" style={{ width: `${course.score}%` }} />
                         </div>
                      </div>
                    </td>
                    <td className="py-7 text-[12px] font-semibold text-slate-400">{new Date(course.completed_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}</td>
                    <td className="py-7 text-right">
                       <button className="w-9 h-9 rounded-xl border border-slate-100 text-slate-200 hover:text-amber-500 hover:border-amber-200 hover:shadow-lg transition-all flex items-center justify-center bg-white">
                          <ChevronRight className="w-4 h-4" />
                       </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </motion.div>
    </div>
  );
};

export default MyProgress;
