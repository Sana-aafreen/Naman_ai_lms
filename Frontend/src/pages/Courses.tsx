import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { useAuth } from "@/contexts/AuthContext";
import { API_BASE_URL, apiGet } from "@/lib/api";
import { 
  ChevronRight, 
  Clock, 
  Trophy, 
  FileText, 
  ExternalLink,
  Sparkles,
  ShieldCheck,
  Filter
} from "lucide-react";

interface Course {
  id: number | string;
  title: string;
  dept: string;
  dur: string;
  level: string;
  progress: number;
  status: string;
  icon?: string;
  bg?: string;
  publishedCourseId?: string;
  pdf_url?: string;
  index_html_url?: string;
  summary?: string;
}

const fadeUp = (delay: number) => ({
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.5, delay, ease: [0.21, 0.45, 0.32, 0.9] }
});

const Courses: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeDept, setActiveDept] = useState("Finance");
  const [completedCourseIds, setCompletedCourseIds] = useState<string[]>([]);

  const departments = ["Finance", "Sales", "HR", "Operations", "Legal", "General"];

  const sopPdfs = [
    { title: "Standard Operating Procedures", filename: "comprehensive_sop.pdf", href: "/sops/comprehensive_sop.pdf" },
    { title: "Governance Framework", filename: "governance_v2.pdf", href: "/sops/comprehensive_sop.pdf" }
  ];

  const sopEntries = [
    { title: "Operational Excellence", steps: ["Strategic Alignment", "Resource Optimization", "Quality Control"] },
    { title: "Incident Response", steps: ["Detection", "Containment", "Remediation", "Post-Mortem"] }
  ];

  useEffect(() => {
    const loadInitialData = async () => {
      setLoading(true);
      try {
        const [courseData, progressData] = await Promise.all([
          apiGet<Course[]>(`/api/courses?department=${activeDept}`),
          apiGet<{ completedCourseIds: string[] }>("/api/growth-tracker/progress")
        ]);
        setCourses(courseData);
        setCompletedCourseIds(progressData.completedCourseIds || []);
      } catch (err) {
        console.error("Failed to load layout data:", err);
      } finally {
        setLoading(false);
      }
    };
    loadInitialData();
  }, [activeDept]);

  const coursesWithCompletion = useMemo(() => courses.map(course => {
    const isCompleted = completedCourseIds.includes(course.publishedCourseId || "");
    return isCompleted ? { ...course, status: "Completed", progress: 100 } : course;
  }), [completedCourseIds, courses]);

  const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
    const colors: Record<string, string> = {
      "Completed": "bg-emerald-50 text-emerald-600 border-emerald-100",
      "In Progress": "bg-amber-50 text-amber-600 border-amber-100",
      "Assigned": "bg-slate-50 text-slate-600 border-slate-100",
    };
    return <span className={`text-[10px] font-bold px-3 py-1 rounded-lg border shadow-sm ${colors[status] || "bg-slate-50 text-slate-400"}`}>{status}</span>;
  };

  return (
    <div className="pb-20 max-w-[1280px] mx-auto px-6">
      <header className="mb-12 pt-6">
        <div className="text-[10px] text-slate-400 font-bold uppercase tracking-[0.25em] mb-6 flex items-center gap-2">
          Knowledge <ChevronRight className="w-3 h-3" /> <span className="text-slate-800 font-black">Strategic Courses</span>
        </div>
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-8">
          <div>
            <h1 className="text-4xl font-bold text-slate-900 mb-4 tracking-tight">Strategic Training Hub</h1>
            <p className="text-lg text-slate-500 font-medium max-w-2xl leading-relaxed">
              Access institutional knowledge assets for the <span className="text-amber-600 font-semibold">{activeDept} Department</span>.
            </p>
          </div>
          <div className="flex flex-col sm:flex-row items-center gap-4">
            <div className="flex items-center gap-2 bg-white p-1.5 rounded-2xl border border-slate-100 shadow-sm">
               <Filter className="w-4 h-4 ml-4 text-slate-400" />
               <div className="flex gap-1 overflow-x-auto scrollbar-none max-w-[500px] pr-2 mt-0.5">
                 {departments.map((dept) => (
                   <button
                     key={dept}
                     onClick={() => setActiveDept(dept)}
                     className={`px-5 py-2 text-[11px] font-bold rounded-xl transition-all whitespace-nowrap ${activeDept === dept ? "bg-[#30231D] text-white shadow-md active:scale-95" : "text-slate-400 hover:text-slate-700 hover:bg-slate-50"}`}
                   >
                     {dept}
                   </button>
                 ))}
               </div>
            </div>
            {(user?.role === "Admin" || user?.role === "Manager") && (
              <button
                onClick={() => navigate("/admin")}
                className="px-5 py-3 rounded-2xl bg-emerald-600 text-white text-[12px] font-bold uppercase tracking-widest hover:brightness-105 transition-all shadow-md flex items-center gap-2 whitespace-nowrap shrink-0"
              >
                <Sparkles className="w-4 h-4" />
                Generate Course
              </button>
            )}
          </div>
        </div>
      </header>

      {loading ? (
        <div className="bg-white border border-slate-100 rounded-3xl p-24 flex flex-col items-center justify-center gap-6">
           <div className="w-12 h-12 border-4 border-slate-100 border-t-[#FF7033] rounded-full animate-spin" />
           <span className="text-[11px] font-bold uppercase tracking-widest text-slate-400">Loading Intelligence Assets...</span>
        </div>
      ) : (
        <div className="space-y-16">
          <section>
            <div className="flex items-center gap-3 mb-8">
              <div className="w-1.5 h-6 bg-amber-400 rounded-full" />
              <h2 className="text-lg font-bold text-slate-800 tracking-tight">Executive Modules</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
              {coursesWithCompletion.map((course, i) => (
                <motion.div
                  key={`${course.dept}-${course.id}`}
                  {...fadeUp(i * 0.05)}
                  className="bg-white border border-slate-100 rounded-3xl flex flex-col group transition-all duration-300 hover:border-amber-200/50 hover:shadow-xl hover:shadow-amber-900/5"
                >
                  <div className="h-1.5 bg-slate-50 rounded-t-3xl overflow-hidden">
                    <motion.div 
                      initial={{ width: 0 }}
                      animate={{ width: `${course.progress}%` }}
                      className="h-full brand-gradient"
                    />
                  </div>
                  <div className="p-8 flex-1 relative">
                    <div className="absolute top-0 right-0 w-24 h-24 bg-amber-50/20 blur-3xl rounded-full" />
                    <div className="flex items-start justify-between mb-6">
                        <div className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl bg-white border border-slate-100 shadow-sm group-hover:scale-110 transition-transform">
                          {course.icon || "📖"}
                        </div>
                        <StatusBadge status={course.status} />
                    </div>
                    <h3 className="text-base font-bold text-slate-900 mb-2 leading-tight line-clamp-2 tracking-tight transition-colors">{course.title}</h3>
                    <div className="flex items-center gap-4 text-[11px] font-semibold text-slate-400">
                      <span className="flex items-center gap-1.5"><Clock className="w-3.5 h-3.5 text-slate-300" /> {course.dur}</span>
                      <span className="flex items-center gap-1.5"><Trophy className="w-3.5 h-3.5 text-slate-300" /> {course.level}</span>
                    </div>
                  </div>
                  <div className="p-6 pt-0">
                    {course.index_html_url && (
                      <a
                        href={`${API_BASE_URL}${course.index_html_url}`}
                        target="_blank"
                        rel="noreferrer"
                        className="enterprise-btn-primary w-full py-4 text-[11px] font-bold uppercase tracking-widest flex items-center justify-center gap-2 shadow-none hover:shadow-lg transition-all"
                      >
                        Enter Simulation <ExternalLink className="w-3.5 h-3.5 opacity-80" />
                      </a>
                    )}
                  </div>
                </motion.div>
              ))}
            </div>
          </section>

          <section>
            <div className="flex items-center gap-3 mb-8">
              <div className="w-1.5 h-6 bg-[#30231D] rounded-full" />
              <h2 className="text-lg font-bold text-slate-800 tracking-tight">Institutional Protocols</h2>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
              <div className="bg-white border border-slate-100 rounded-3xl p-8 relative shadow-sm">
                 <div className="flex items-center justify-between mb-8">
                    <h3 className="text-[11px] font-bold text-slate-400 uppercase tracking-widest">SOP Intelligence</h3>
                    <Sparkles className="w-4 h-4 text-amber-500" />
                 </div>
                 <div className="space-y-3">
                  {sopEntries.map((entry, i) => (
                    <div key={i} className="group p-5 rounded-2xl border border-slate-50 bg-slate-50/30 hover:bg-white hover:border-amber-100 hover:shadow-lg hover:shadow-amber-900/5 transition-all cursor-pointer">
                      <div className="text-[14px] font-bold text-slate-800 mb-1.5 group-hover:text-amber-600 transition-colors">{entry.title}</div>
                      <div className="text-[11px] text-slate-400 font-medium line-clamp-1">{entry.steps?.join(" • ")}</div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="bg-white border border-slate-100 rounded-3xl p-8 shadow-sm">
                <div className="flex items-center justify-between mb-8">
                   <h3 className="text-[11px] font-bold text-slate-400 uppercase tracking-widest">Procedural Archive</h3>
                   <ShieldCheck className="w-4 h-4 text-slate-400" />
                </div>
                <div className="space-y-3">
                   {sopPdfs.map((pdf, i) => (
                     <a
                       key={i}
                       href={pdf.href}
                       target="_blank"
                       rel="noreferrer"
                       className="flex items-center gap-5 p-5 rounded-2xl border border-slate-50 bg-slate-50/30 hover:bg-white hover:border-amber-100 hover:shadow-lg hover:shadow-amber-900/5 transition-all group"
                     >
                       <div className="w-12 h-12 rounded-xl bg-slate-800 flex items-center justify-center text-white shadow-md group-hover:scale-105 transition-transform">
                         <FileText className="w-5 h-5" />
                       </div>
                       <div className="flex-1 min-w-0">
                         <div className="text-[14px] font-bold text-slate-800 transition-colors truncate">{pdf.title}</div>
                         <div className="text-[11px] text-slate-400 font-medium mt-0.5">{pdf.filename}</div>
                       </div>
                       <ExternalLink className="w-4 h-4 text-slate-200 group-hover:text-amber-500 transition-all" />
                     </a>
                   ))}
                </div>
              </div>
            </div>
          </section>
        </div>
      )}
    </div>
  );
};

export default Courses;
