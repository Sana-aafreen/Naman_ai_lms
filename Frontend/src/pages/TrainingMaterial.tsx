import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { API_BASE_URL, apiGet } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { 
  BookOpen, 
  FileText, 
  ClipboardList, 
  ExternalLink, 
  ChevronRight,
  ShieldCheck,
  Search,
  BookMarked,
  Sparkles
} from "lucide-react";
import { motion } from "framer-motion";

interface Course {
  id: number | string;
  title: string;
  dept: string;
  dur: string;
  level: string;
  summary?: string;
  pdf_url?: string;
}

interface SopEntry {
  department: string;
  title: string;
  steps?: string[];
}

interface SopPdf {
  department: string;
  title: string;
  href: string;
  filename: string;
}

interface SopResponse {
  entries: SopEntry[];
  pdfs: SopPdf[];
}

const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4, delay, ease: "easeOut" },
});

const TrainingMaterial: React.FC = () => {
  const { user } = useAuth();
  const [courses, setCourses] = useState<Course[]>([]);
  const [sopEntries, setSopEntries] = useState<SopEntry[]>([]);
  const [sopPdfs, setSopPdfs] = useState<SopPdf[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const department = user?.department;
    if (!department) {
      setLoading(false);
      return;
    }

    const fetchResources = async () => {
      setLoading(true);
      try {
        const [courseData, sopData] = await Promise.all([
          apiGet<Course[]>(`/api/courses?department=${encodeURIComponent(department)}`).catch(() => []),
          apiGet<SopResponse>(`/api/sops?department=${encodeURIComponent(department)}`).catch(() => ({ entries: [], pdfs: [] })),
        ]);

        setCourses(Array.isArray(courseData) ? courseData : []);
        setSopEntries(Array.isArray(sopData.entries) ? sopData.entries : []);
        setSopPdfs(Array.isArray(sopData.pdfs) ? sopData.pdfs : []);
      } finally {
        setLoading(false);
      }
    };

    void fetchResources();
  }, [user?.department]);

  return (
    <div className="pb-20 max-w-[1280px] mx-auto px-6">
      <header className="mb-12 pt-6">
        <div className="text-[10px] text-slate-400 font-bold uppercase tracking-[0.25em] mb-6 flex items-center gap-2">
          Knowledge Base <ChevronRight className="w-3 h-3" /> <span className="text-slate-800 font-black">Resource Repository</span>
        </div>
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-8">
          <div>
            <h1 className="text-4xl font-bold text-slate-900 mb-4 tracking-tight">Institutional Resources</h1>
            <p className="text-lg text-slate-500 font-medium max-w-2xl leading-relaxed">
              Access the verified repository of learning modules and standard operating protocols for the <span className="text-amber-600 font-semibold">{user?.department || "Operations"} Department</span>.
            </p>
          </div>
          <div className="hidden lg:flex items-center gap-3 px-5 py-2.5 bg-white border border-slate-100 rounded-2xl shadow-sm">
            <Search className="w-4 h-4 text-slate-400" />
            <input type="text" placeholder="Search repository..." className="bg-transparent text-[13px] font-medium outline-none border-none placeholder:text-slate-300 w-48 text-slate-700" />
          </div>
        </div>
      </header>

      {loading ? (
        <div className="bg-white border border-slate-100 rounded-3xl p-24 flex flex-col items-center justify-center gap-6">
           <div className="w-12 h-12 border-4 border-slate-100 border-t-[#FF7033] rounded-full animate-spin" />
           <span className="text-[11px] font-bold uppercase tracking-widest text-slate-400">Synchronizing Vault...</span>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">
          {/* Tactical Modules */}
          <motion.div {...fadeUp(0.05)} className="bg-white border border-slate-100 rounded-3xl flex flex-col group overflow-hidden shadow-sm">
            <div className="h-1.5 brand-gradient opacity-80" />
            <div className="p-8 flex-1 relative">
              <div className="flex items-center justify-between mb-8">
                 <h3 className="text-[11px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2.5">
                   <BookOpen className="w-4 h-4 text-[#FF7033]" /> Tactical Training
                 </h3>
                 <span className="text-[10px] font-bold text-slate-500 bg-slate-50 border border-slate-100 px-2.5 py-1 rounded-lg">{courses.length} ASSETS</span>
              </div>
              
              <div className="space-y-3">
                {courses.map((course, index) => (
                  <a
                    key={index}
                    href={course.pdf_url ? `${API_BASE_URL}${course.pdf_url}` : "#"}
                    target="_blank"
                    rel="noreferrer"
                    className="flex flex-col p-5 rounded-2xl border border-slate-50 bg-slate-50/20 hover:bg-white hover:border-amber-100 hover:shadow-lg hover:shadow-amber-900/5 transition-all group/item"
                  >
                    <div className="text-[14px] font-bold text-slate-800 mb-1 group-hover/item:text-amber-600 transition-colors">{course.title}</div>
                    <div className="flex items-center gap-3 text-[10px] font-semibold text-slate-400 uppercase tracking-tight">
                       <span className="flex items-center gap-1.5"><Sparkles className="w-3 h-3 text-slate-300" /> {course.dur}</span>
                       <span className="w-1 h-1 rounded-full bg-slate-200" />
                       <span>Tier: {course.level}</span>
                    </div>
                  </a>
                ))}
                {courses.length === 0 && (
                  <div className="text-center py-12">
                    <BookMarked className="w-10 h-10 text-slate-100 mx-auto mb-4" />
                    <p className="text-[11px] text-slate-300 font-medium">No training modules found.</p>
                  </div>
                )}
              </div>
            </div>
          </motion.div>

          {/* Protocols */}
          <motion.div {...fadeUp(0.1)} className="bg-white border border-slate-100 rounded-3xl flex flex-col group overflow-hidden shadow-sm">
            <div className="h-1.5 bg-slate-800 opacity-80" />
            <div className="p-8 flex-1 relative">
              <div className="flex items-center justify-between mb-8">
                 <h3 className="text-[11px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2.5">
                   <ClipboardList className="w-4 h-4 text-emerald-600" /> Standard Protocols
                 </h3>
                 <span className="text-[10px] font-bold text-slate-500 bg-slate-50 border border-slate-100 px-2.5 py-1 rounded-lg">{sopEntries.length} SOPs</span>
              </div>
              
              <div className="space-y-3">
                {sopEntries.map((entry, index) => (
                  <div key={index} className="flex flex-col p-5 rounded-2xl border border-slate-50 bg-slate-50/20 hover:bg-white hover:border-amber-100 hover:shadow-lg hover:shadow-amber-900/5 transition-all cursor-pointer group/item">
                    <div className="text-[14px] font-bold text-slate-800 mb-1 group-hover/item:text-amber-600 transition-colors">{entry.title}</div>
                    <div className="text-[11px] text-slate-400 font-medium line-clamp-1">{entry.steps?.join(" • ") || "Validated procedures."}</div>
                  </div>
                ))}
                {sopEntries.length === 0 && (
                  <div className="text-center py-12">
                    <ShieldCheck className="w-10 h-10 text-slate-100 mx-auto mb-4" />
                    <p className="text-[11px] text-slate-300 font-medium">Zero protocols defined yet.</p>
                  </div>
                )}
              </div>
            </div>
          </motion.div>

          {/* Documents */}
          <motion.div {...fadeUp(0.15)} className="bg-white border border-slate-100 rounded-3xl flex flex-col group overflow-hidden shadow-sm">
            <div className="h-1.5 bg-amber-600 opacity-80" />
            <div className="p-8 flex-1 relative">
              <div className="flex items-center justify-between mb-8">
                 <h3 className="text-[11px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2.5">
                   <FileText className="w-4 h-4 text-amber-600" /> Procedural Archive
                 </h3>
                 <Link to="/sop" className="text-[11px] font-bold text-amber-600 hover:text-amber-700 flex items-center gap-1 transition-all">
                   Full Library <ChevronRight className="w-3.5 h-3.5" />
                 </Link>
              </div>
              
              <div className="space-y-3">
                {sopPdfs.map((pdf, index) => (
                  <a
                    key={index}
                    href={pdf.href}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-4 p-4 rounded-2xl border border-slate-50 bg-slate-50/20 hover:bg-white hover:border-amber-100 hover:shadow-lg hover:shadow-amber-900/5 transition-all group/item"
                  >
                    <div className="w-11 h-11 rounded-xl bg-slate-100 flex items-center justify-center text-slate-400 shadow-sm group-hover/item:bg-slate-800 group-hover/item:text-white transition-all">
                      <FileText className="w-5 h-5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-[14px] font-bold text-slate-800 truncate group-hover/item:text-amber-600 transition-colors">{pdf.title}</div>
                      <div className="text-[10px] text-slate-400 font-medium mt-0.5 truncate">{pdf.filename}</div>
                    </div>
                    <ExternalLink className="w-3.5 h-3.5 text-slate-200 group-hover/item:text-amber-500 transition-all" />
                  </a>
                ))}
                {sopPdfs.length === 0 && (
                  <div className="text-center py-12">
                    <FileText className="w-10 h-10 text-slate-100 mx-auto mb-4" />
                    <p className="text-[11px] text-slate-300 font-medium">No documents archived.</p>
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
};

export default TrainingMaterial;
