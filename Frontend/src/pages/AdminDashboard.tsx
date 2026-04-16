import React, { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Link } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { API_BASE_URL, apiGet, apiPost } from "@/lib/api";
import { WhatsNewSection } from "@/components/WhatsNewSection";
import { Sparkles, Trophy, BookOpen, ExternalLink, ChevronRight, List, ShieldCheck } from "lucide-react";

// ─── What's New Types ─────────────────────────────────────────────────────────

type UpdateCategory =
  | "Achievement"
  | "Policy"
  | "Event"
  | "Announcement"
  | "Training"
  | "Other";

const CATEGORIES: UpdateCategory[] = [
  "Achievement", "Policy", "Event", "Announcement", "Training", "Other",
];

const CATEGORY_META: Record<
  UpdateCategory,
  { icon: string; bg: string; text: string }
> = {
  Achievement: { icon: "🏆", bg: "bg-amber-100 dark:bg-amber-900/30", text: "text-amber-700 dark:text-amber-300" },
  Policy:      { icon: "📋", bg: "bg-blue-100 dark:bg-blue-900/30",   text: "text-blue-700 dark:text-blue-300" },
  Event:       { icon: "🗓️", bg: "bg-purple-100 dark:bg-purple-900/30", text: "text-purple-700 dark:text-purple-300" },
  Announcement:{ icon: "📢", bg: "bg-saffron/10",                      text: "text-saffron" },
  Training:    { icon: "🎓", bg: "bg-green-100 dark:bg-green-900/30",  text: "text-green-700 dark:text-green-300" },
  Other:       { icon: "💡", bg: "bg-secondary",                       text: "text-muted-foreground" },
};

interface EmployeeRecord {
  id: number | string;
  userId: string;
  userName: string;
  name?: string;
  department: string;
  role: string;
  status: string;
}

interface LessonExplanation {
  lesson_title: string;
  body: string;
  key_points: string[];
  real_world_example: string;
  do_and_dont: { do?: string[]; dont?: string[] };
}

interface ModuleBookletRef {
  module_index: number;
  module_id: string;
  module_title: string;
  pdf_path: string;
  pdf_filename: string;
  pdf_url: string;
  introduction?: string;
  why_it_matters?: string;
  duration?: string;
  goals?: string[];
  lesson_explanations?: LessonExplanation[];
  practice_activities?: string[];
  sop_checkpoints?: string[];
  module_recap?: string;
  whats_next?: string;
  html_path?: string;
  html_filename?: string;
  html_url?: string;
}

interface ModuleMCQ {
  module_index: number;
  module_title: string;
  generated_by: string;
  questions: Array<{
    id: string;
    question: string;
    options: string[];
    correctOptionIndex: number;
    explanation: string;
  }>;
}

interface GeneratedCourseResponse {
  success: boolean;
  department: string;
  title: string;
  summary: string;
  audience?: string;
  generated_at: string;
  source_notes?: string[];
  prerequisites?: string[];
  learning_objectives?: string[];
  modules?: Array<Record<string, unknown>>;
  quiz_questions?: Array<Record<string, unknown>>;
  // v3 package fields
  index_pdf?: { pdf_path: string; pdf_filename: string; pdf_url: string };
  index_html?: { html_path: string; html_filename: string; html_url: string };
  module_booklets?: ModuleBookletRef[];
  module_mcqs?: ModuleMCQ[];
  // legacy single-PDF fields
  pdf_path?: string;
  pdf_filename?: string;
  pdf_url?: string;
  html_url?: string;
}

interface ProgressOverviewRow {
  employeeId: string;
  employeeName: string;
  department: string;
  role: string;
  coursesCompleted: number;
  averageScore: number;
  latestScore: number;
  latestCompletedAt: string;
  completedCourses: Array<{
    title: string;
    department: string;
    score: number;
    completedAt: string;
    status: string;
  }>;
}

interface ProgressOverview {
  title: string;
  subtitle: string;
  rows: ProgressOverviewRow[];
}

function getIndexPdfUrl(course: GeneratedCourseResponse, base: string): string {
  if (course.index_pdf?.pdf_url) return `${base}${course.index_pdf.pdf_url}`;
  if (course.pdf_url) return `${base}${course.pdf_url}`;
  return "";
}

function getIndexHtmlUrl(course: GeneratedCourseResponse, base: string): string {
  if (course.index_html?.html_url) return `${base}${course.index_html.html_url}`;
  if (course.html_url) return `${base}${course.html_url}`;
  return "";
}

// ─── Update Composer Modal ────────────────────────────────────────────────────

const UpdateComposerModal: React.FC<{
  open: boolean;
  onClose: () => void;
  onSubmit: (data: { title: string; body: string; category: UpdateCategory }) => Promise<void>;
}> = ({ open, onClose, onSubmit }) => {
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [category, setCategory] = useState<UpdateCategory>("Announcement");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  const reset = () => {
    setTitle(""); setBody(""); setCategory("Announcement");
    setSubmitting(false); setDone(false);
  };

  const handleClose = () => { reset(); onClose(); };

  const handleSubmit = async () => {
    if (!title.trim() || !body.trim()) return;
    setSubmitting(true);
    try {
      await onSubmit({ title: title.trim(), body: body.trim(), category });
      setDone(true);
      setTimeout(handleClose, 1800);
    } catch {
      setSubmitting(false);
    }
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          {/* Backdrop */}
          <motion.div
            className="absolute inset-0 bg-black/40 backdrop-blur-sm"
            onClick={handleClose}
          />

          {/* Panel */}
          <motion.div
            className="relative z-10 w-full max-w-lg bg-card border border-border rounded-2xl shadow-2xl p-6"
            initial={{ opacity: 0, y: 40, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.97 }}
            transition={{ type: "spring", stiffness: 340, damping: 28 }}
          >
            {done ? (
              <div className="py-8 text-center">
                <div className="text-5xl mb-3">✅</div>
                <div className="text-base font-semibold mb-1">Update Submitted!</div>
                <div className="text-[13px] text-muted-foreground">
                  Pending Admin approval — it'll appear in What's New once approved.
                </div>
              </div>
            ) : (
              <>
                <div className="flex items-center justify-between mb-5">
                  <div>
                    <div className="text-base font-semibold">Post an Update</div>
                    <div className="text-[12px] text-muted-foreground mt-0.5">
                      Submitted for Admin approval before going live
                    </div>
                  </div>
                  <button
                    onClick={handleClose}
                    className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center text-muted-foreground hover:text-foreground transition"
                  >
                    ✕
                  </button>
                </div>

                {/* Category picker */}
                <div className="mb-4">
                  <div className="text-[11px] font-semibold text-muted-foreground mb-2 uppercase tracking-wide">
                    Category
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {CATEGORIES.map((cat) => {
                      const m = CATEGORY_META[cat];
                      return (
                        <button
                          key={cat}
                          onClick={() => setCategory(cat)}
                          className={`flex items-center gap-1 text-[11px] font-semibold px-2.5 py-1 rounded-full border transition-all
                            ${category === cat
                              ? `${m.bg} ${m.text} border-current`
                              : "bg-secondary text-muted-foreground border-border hover:border-saffron/40"
                            }`}
                        >
                          {m.icon} {cat}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Title */}
                <div className="mb-3">
                  <input
                    type="text"
                    placeholder="Update title…"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    maxLength={100}
                    className="w-full bg-secondary border border-border rounded-xl px-4 py-2.5 text-sm font-medium placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-saffron/40 transition"
                  />
                </div>

                {/* Body */}
                <div className="mb-5">
                  <textarea
                    placeholder="Share what's happening… (keep it concise)"
                    value={body}
                    onChange={(e) => setBody(e.target.value)}
                    maxLength={500}
                    rows={3}
                    className="w-full bg-secondary border border-border rounded-xl px-4 py-2.5 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-saffron/40 transition resize-none"
                  />
                  <div className="text-[10px] text-muted-foreground text-right mt-0.5">
                    {body.length}/500
                  </div>
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={handleClose}
                    className="flex-1 py-2.5 rounded-xl border border-border text-sm font-semibold text-muted-foreground hover:bg-secondary transition"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSubmit}
                    disabled={submitting || !title.trim() || !body.trim()}
                    className="flex-1 py-2.5 rounded-xl bg-saffron text-white text-sm font-semibold hover:opacity-90 transition disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {submitting ? "Submitting…" : "Submit for Review"}
                  </button>
                </div>
              </>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

const AdminDashboard: React.FC = () => {
  const { user } = useAuth();
  const tabs = ["Employees", "Progress Reports", "Calendar Access", "Course Generator", "What's New", "LMS Analytics"];
  const [activeTab, setActiveTab] = useState("Employees");

  // ── employee state ────────────────────────────────────────────────────
  const [employees, setEmployees] = useState<EmployeeRecord[]>([]);
  const [loadingEmployees, setLoadingEmployees] = useState(true);
  const [employeeError, setEmployeeError] = useState("");

  // ── progress state ────────────────────────────────────────────────────
  const [progressOverview, setProgressOverview] = useState<ProgressOverview | null>(null);
  const [loadingProgress, setLoadingProgress] = useState(true);
  const [progressError, setProgressError] = useState("");

  // ── course generator state ────────────────────────────────────────────
  const [courseDepartment, setCourseDepartment] = useState(user?.department || "Sales");
  const [courseQueries, setCourseQueries] = useState("");
  const [generatingCourse, setGeneratingCourse] = useState(false);
  const [generatedCourse, setGeneratedCourse] = useState<GeneratedCourseResponse | null>(null);
  const [publishingCourse, setPublishingCourse] = useState(false);
  const [publishMessage, setPublishMessage] = useState("");
  const [courseError, setCourseError] = useState("");

  // ── what's new state ──────────────────────────────────────────────────
  const [composerOpen, setComposerOpen] = useState(false);

  // ── module viewer state ───────────────────────────────────────────────
  const [selectedBooklet, setSelectedBooklet] = useState<ModuleBookletRef | null>(null);
  const [selectedMCQModule, setSelectedMCQModule] = useState<ModuleMCQ | null>(null);
  const [bookletView, setBookletView] = useState<"list" | "pdf" | "mcq">("list");

  const courseIndexUrl = generatedCourse ? getIndexPdfUrl(generatedCourse, API_BASE_URL) : "";

  // ── data fetching ─────────────────────────────────────────────────────
  useEffect(() => {
    const fetchEmployees = async () => {
      setLoadingEmployees(true);
      setEmployeeError("");
      try {
        const data = await apiGet<EmployeeRecord[]>("/api/employees");
        setEmployees(Array.isArray(data) ? data : []);
      } catch (error) {
        console.error("Failed to load employees:", error);
        setEmployeeError("Unable to load employee records from the backend right now.");
      } finally {
        setLoadingEmployees(false);
      }
    };

    const fetchProgressOverview = async () => {
      setLoadingProgress(true);
      setProgressError("");
      try {
        const data = await apiGet<ProgressOverview>("/api/progress-overview");
        setProgressOverview(data);
      } catch (error) {
        console.error("Failed to load progress overview:", error);
        setProgressError("Unable to load progress reports right now.");
      } finally {
        setLoadingProgress(false);
      }
    };

    void fetchEmployees();
    void fetchProgressOverview();
  }, []);

  // ── derived employee data ─────────────────────────────────────────────
  const visibleEmployees = useMemo(() => {
    if (user?.role === "Manager") {
      return employees.filter((e) => e.role === "Employee" && e.department === user.department);
    }
    return employees;
  }, [employees, user?.department, user?.role]);

  const employeeStats = useMemo(() => {
    const total = visibleEmployees.length;
    const active = visibleEmployees.filter((e) => e.status === "Active").length;
    const admins = visibleEmployees.filter((e) => e.role === "Admin").length;
    const managers = visibleEmployees.filter((e) => e.role === "Manager").length;
    return [
      { icon: "👥", label: "Visible Team", value: String(total), color: "text-saffron" },
      { icon: "✅", label: "Active Today", value: String(active), color: "text-nd-green" },
      { icon: "🧭", label: "Managers", value: String(managers), color: "text-gold" },
      { icon: "🛡️", label: "Admins", value: String(admins), color: "text-nd-blue" },
    ];
  }, [visibleEmployees]);

  const departments = useMemo(
    () => Array.from(new Set(visibleEmployees.map((e) => e.department))).filter(Boolean).sort(),
    [visibleEmployees],
  );

  const groupedHeadcount = useMemo(() => {
    const grouped = new Map<string, { employees: number; managers: number }>();
    visibleEmployees.forEach((e) => {
      const cur = grouped.get(e.department) ?? { employees: 0, managers: 0 };
      if (e.role === "Manager") cur.managers += 1;
      else if (e.role === "Employee") cur.employees += 1;
      grouped.set(e.department, cur);
    });
    return Array.from(grouped.entries()).map(([department, counts]) => ({ department, ...counts }));
  }, [visibleEmployees]);

  useEffect(() => {
    if (!courseDepartment && departments.length > 0) setCourseDepartment(departments[0]);
  }, [courseDepartment, departments]);

  // ── course generation ─────────────────────────────────────────────────
  const handleGenerateCourse = async () => {
    if (!courseDepartment) return;
    setGeneratingCourse(true);
    setCourseError("");
    setPublishMessage("");
    setGeneratedCourse(null);
    setSelectedBooklet(null);
    setSelectedMCQModule(null);
    setBookletView("list");

    try {
      const relatedQueries = courseQueries.split("\n").map((q) => q.trim()).filter(Boolean);
      const data = await apiPost<GeneratedCourseResponse>("/api/course-generator", {
        department: courseDepartment,
        relatedQueries,
      });
      setGeneratedCourse(data);
      
      // Auto-open the HTML course after generation
      const realHtmlUrl = getIndexHtmlUrl(data, API_BASE_URL);
      if (realHtmlUrl) {
        window.open(realHtmlUrl, "_blank");
      }
    } catch (error) {
      console.error("Course generation failed:", error);
      setCourseError(error instanceof Error ? error.message : "Course generation failed");
    } finally {
      setGeneratingCourse(false);
    }
  };

  const handlePublishCourse = async () => {
    if (!generatedCourse) return;
    setPublishingCourse(true);
    setCourseError("");
    setPublishMessage("");
    try {
      await apiPost("/api/generated-courses/publish", generatedCourse);
      setPublishMessage(`Published to ${generatedCourse.department} successfully.`);
    } catch (error) {
      console.error("Course publish failed:", error);
      setCourseError(error instanceof Error ? error.message : "Course publish failed");
    } finally {
      setPublishingCourse(false);
    }
  };

  const handleViewHTML = async () => {
    if (generatedCourse) {
      const realHtmlUrl = getIndexHtmlUrl(generatedCourse, API_BASE_URL);
      if (realHtmlUrl) {
        window.open(realHtmlUrl, "_blank");
        return;
      }
    }
    
    // If not generated yet or url missing, prompt to generate
    if (!generatingCourse) {
      if (confirm("Course HTML is not yet available. Would you like to generate the course package now?")) {
        await handleGenerateCourse();
      }
    }
  };

  // ── booklet helpers ───────────────────────────────────────────────────
  const openBookletPdf = (booklet: ModuleBookletRef) => {
    setSelectedBooklet(booklet);
    setSelectedMCQModule(null);
    setBookletView("pdf");
  };

  const openBookletMCQ = (booklet: ModuleBookletRef) => {
    const mcq = generatedCourse?.module_mcqs?.find((m) => m.module_index === booklet.module_index) ?? null;
    setSelectedBooklet(booklet);
    setSelectedMCQModule(mcq);
    setBookletView("mcq");
  };

  const mcqGeneratorBadge = (by: string) => {
    const map: Record<string, { label: string; classes: string }> = {
      groq_key2: { label: "Groq AI", classes: "bg-purple-50 text-purple-700 border-purple-200" },
      gemini: { label: "Gemini AI", classes: "bg-blue-50 text-blue-700 border-blue-200" },
      static_fallback: { label: "Static", classes: "bg-gray-100 text-gray-500 border-gray-200" },
    };
    const b = map[by] ?? { label: by, classes: "bg-gray-100 text-gray-500 border-gray-200" };
    return (
      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${b.classes}`}>
        {b.label}
      </span>
    );
  };

  // ════════════════════════════════════════════════════════════════════════
  return (
    <div>
      {/* ── page header ── */}
      <div className="mb-5">
        <div className="text-[11px] text-muted-foreground mb-2">
          Home <span className="text-saffron">/ {user?.role === "Manager" ? "Manager" : "Admin"}</span>
        </div>
        <h1 className="text-xl font-bold mb-1">
          {user?.role === "Manager" ? "Manager Dashboard" : "Admin Dashboard"}
        </h1>
        <p className="text-[13px] text-muted-foreground">
          Role-based oversight for employee records, progress reports, calendar access, and department course publishing
        </p>
      </div>

      {/* ── tab bar ── */}
      <div className="flex flex-wrap gap-0.5 bg-secondary rounded-lg p-[3px] w-fit mb-5">
        {tabs.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-[7px] text-xs rounded-[7px] font-medium transition-all ${activeTab === tab ? "bg-card shadow-sm" : "text-muted-foreground"
              }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* ══════════════════════════════════════════════════════════════════
          EMPLOYEES TAB
      ══════════════════════════════════════════════════════════════════ */}
      {activeTab === "Employees" && (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
            {employeeStats.map((stat, i) => (
              <div key={i} className="bg-card border border-border rounded-xl p-4">
                <div className="text-xl mb-2">{stat.icon}</div>
                <div className="text-[11px] text-muted-foreground mb-1">{stat.label}</div>
                <div className={`text-[26px] font-bold ${stat.color}`}>
                  {loadingEmployees ? "-" : stat.value}
                </div>
              </div>
            ))}
          </div>

          <div className="bg-card border border-border rounded-xl p-[18px]">
            <div className="text-sm font-semibold mb-3.5">
              {user?.role === "Manager" ? "Department Employees" : "All Employees"}
            </div>
            {loadingEmployees && <div className="text-[13px] text-muted-foreground">Loading employee records...</div>}
            {employeeError && <div className="text-[13px] text-red-600">{employeeError}</div>}
            {!loadingEmployees && !employeeError && visibleEmployees.length > 0 && (
              <table className="w-full text-[13px]">
                <thead>
                  <tr className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide">
                    <th className="text-left p-2.5 bg-secondary rounded-l-md">User ID</th>
                    <th className="text-left p-2.5 bg-secondary">Name</th>
                    <th className="text-left p-2.5 bg-secondary">Department</th>
                    <th className="text-left p-2.5 bg-secondary">Role</th>
                    <th className="text-left p-2.5 bg-secondary rounded-r-md">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleEmployees.map((e, i) => (
                    <tr key={`${e.department}-${e.userId}-${e.role}-${e.id}-${i}`}
                      className="border-b border-border last:border-b-0 hover:bg-secondary/50">
                      <td className="p-2.5 font-medium">{e.userId}</td>
                      <td className="p-2.5">{e.userName || e.name}</td>
                      <td className="p-2.5">{e.department}</td>
                      <td className="p-2.5">{e.role}</td>
                      <td className="p-2.5">
                        <span className="text-[10px] px-2 py-0.5 rounded-full font-medium bg-nd-green-light text-nd-green">
                          {e.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}

      {/* ══════════════════════════════════════════════════════════════════
          PROGRESS REPORTS TAB
      ══════════════════════════════════════════════════════════════════ */}
      {activeTab === "Progress Reports" && (
        <div className="grid grid-cols-1 lg:grid-cols-[1.05fr_0.95fr] gap-3.5">
          <div className="bg-card border border-border rounded-xl p-[18px]">
            <div className="text-sm font-semibold mb-1">{progressOverview?.title || "Progress Reports"}</div>
            <div className="text-[13px] text-muted-foreground mb-4">{progressOverview?.subtitle}</div>
            {loadingProgress && <div className="text-[13px] text-muted-foreground">Loading progress report...</div>}
            {progressError && <div className="text-[13px] text-red-600">{progressError}</div>}
            {!loadingProgress && !progressError && progressOverview && (
              <div className="overflow-x-auto">
                <table className="w-full text-[13px]">
                  <thead>
                    <tr className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide">
                      <th className="text-left p-2.5 bg-secondary rounded-l-md">Name</th>
                      <th className="text-left p-2.5 bg-secondary">Role</th>
                      <th className="text-left p-2.5 bg-secondary">Courses</th>
                      <th className="text-left p-2.5 bg-secondary">Avg Score</th>
                      <th className="text-left p-2.5 bg-secondary rounded-r-md">Latest</th>
                    </tr>
                  </thead>
                  <tbody>
                    {progressOverview.rows.map((row, i) => (
                      <tr key={`${row.employeeId}-${row.role}-${i}`}
                        className="border-b border-border last:border-b-0 hover:bg-secondary/50">
                        <td className="p-2.5">
                          <div className="font-medium">{row.employeeName}</div>
                          <div className="text-[11px] text-muted-foreground">{row.department}</div>
                        </td>
                        <td className="p-2.5">{row.role}</td>
                        <td className="p-2.5">{row.coursesCompleted}</td>
                        <td className="p-2.5">{row.averageScore}%</td>
                        <td className="p-2.5">{row.latestScore ? `${row.latestScore}%` : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="bg-card border border-border rounded-xl p-[18px]">
            <div className="text-sm font-semibold mb-3.5">Latest Completion Detail</div>
            <div className="space-y-3">
              {(progressOverview?.rows || []).map((row) => (
                <div key={`${row.employeeId}-${row.role}`}
                  className="rounded-lg border border-border bg-secondary/30 px-4 py-3">
                  <div className="font-medium">{row.employeeName}</div>
                  <div className="text-[12px] text-muted-foreground mt-1">
                    {row.role} · {row.department} · {row.coursesCompleted} course{row.coursesCompleted === 1 ? "" : "s"} completed
                  </div>
                  {row.completedCourses[0] && (
                    <div className="text-[12px] text-muted-foreground mt-2">
                      Latest: {row.completedCourses[0].title} · {row.completedCourses[0].score}%
                      · {new Date(row.completedCourses[0].completedAt).toLocaleDateString()}
                    </div>
                  )}
                </div>
              ))}
              {progressOverview && progressOverview.rows.length === 0 && (
                <div className="text-[13px] text-muted-foreground">No course completions recorded yet.</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════
          CALENDAR ACCESS TAB
      ══════════════════════════════════════════════════════════════════ */}
      {activeTab === "Calendar Access" && (
        <div className="grid grid-cols-1 lg:grid-cols-[1.1fr_0.9fr] gap-3.5">
          <div className="bg-card border border-border rounded-xl p-[18px]">
            <div className="text-sm font-semibold mb-3.5">
              {user?.role === "Manager" ? "Manager Calendar Views" : "Admin Calendar Views"}
            </div>
            <div className="space-y-3 text-[13px] text-muted-foreground">
              {[
                { title: "Employee Calendar", desc: user?.role === "Manager" ? "Shows your department employee meetings and leave entries." : "Shows all employee meetings and leave entries." },
                { title: "Manager Calendar", desc: user?.role === "Manager" ? "Shows your own manager calendar activity." : "Shows all managers and their calendar activity by department." },
                { title: "My Daily Calendar", desc: "Shows your own meetings and personal leave." },
              ].map((item) => (
                <div key={item.title} className="rounded-lg border border-border bg-secondary/30 px-4 py-3">
                  <div className="font-semibold text-foreground">{item.title}</div>
                  <div>{item.desc}</div>
                </div>
              ))}
            </div>
            <Link to="/holidays" className="inline-flex mt-4 px-4 py-2 rounded-lg bg-saffron text-white text-sm font-semibold hover:opacity-90 transition">
              Open Daily Calendar
            </Link>
          </div>

          <div className="bg-card border border-border rounded-xl p-[18px]">
            <div className="text-sm font-semibold mb-3.5">Department Coverage</div>
            <div className="space-y-2.5">
              {groupedHeadcount.map((group) => (
                <div key={group.department} className="rounded-lg border border-border bg-secondary/30 px-4 py-3">
                  <div className="font-medium">{group.department}</div>
                  <div className="text-[12px] text-muted-foreground mt-1">
                    Employees: {group.employees} · Managers: {group.managers}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════
          COURSE GENERATOR TAB
      ══════════════════════════════════════════════════════════════════ */}
      {activeTab === "Course Generator" && (
        <div className="space-y-3.5">

          {/* ── top row: generator form + course summary ── */}
          <div className="grid grid-cols-1 lg:grid-cols-[1fr_0.95fr] gap-3.5">

            {/* left: form */}
            <div className="bg-card border border-border rounded-xl p-[18px]">
              <div className="text-sm font-semibold mb-3.5">Generate Department Course Package</div>
              <div className="space-y-3">
                <div>
                  <label className="text-[11px] text-muted-foreground uppercase font-semibold">Department</label>
                  <select
                    value={courseDepartment}
                    onChange={(e) => setCourseDepartment(e.target.value)}
                    className="w-full mt-1 p-2 text-sm border border-border rounded-lg bg-secondary"
                  >
                    {departments.map((d) => (
                      <option key={d} value={d}>{d}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-[11px] text-muted-foreground uppercase font-semibold">
                    Related Queries
                    <span className="ml-1 font-normal normal-case">(one per line, optional)</span>
                  </label>
                  <textarea
                    rows={4}
                    value={courseQueries}
                    onChange={(e) => setCourseQueries(e.target.value)}
                    placeholder={"sales training best practices\ncustomer handling for spiritual services"}
                    className="w-full mt-1 p-2 text-sm border border-border rounded-lg bg-secondary resize-none"
                  />
                </div>

                <button
                  onClick={handleGenerateCourse}
                  disabled={generatingCourse}
                  className="px-4 py-2 rounded-lg bg-emerald-600 text-white text-sm font-semibold hover:opacity-90 transition disabled:opacity-50 flex items-center gap-2"
                >
                  {generatingCourse && (
                    <svg className="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                  )}
                  {generatingCourse ? "Generating package…" : "Generate Course Package"}
                </button>

                {courseError && <div className="text-[13px] text-red-600">{courseError}</div>}
              </div>
            </div>

            {/* right: course summary / index PDF */}
            <div className="bg-card border border-border rounded-xl p-[18px]">
              <div className="text-sm font-semibold mb-3.5">Course Overview</div>

              {!generatedCourse ? (
                <div className="text-[13px] text-muted-foreground">
                  Generate a course package to see the overview, browse module booklets, preview assessments, and publish to the department.
                </div>
              ) : (
                <div className="space-y-3 text-[13px]">
                  <div>
                    <div className="font-semibold text-[15px]">{generatedCourse.title}</div>
                    <div className="text-muted-foreground mt-1 text-[12px] leading-relaxed">{generatedCourse.summary}</div>
                  </div>

                  <div className="grid grid-cols-3 gap-2 text-[11px]">
                    <div className="bg-secondary/50 rounded-lg p-2.5 text-center">
                      <div className="font-bold text-[18px] text-saffron">
                        {generatedCourse.module_booklets?.length ?? generatedCourse.modules?.length ?? 0}
                      </div>
                      <div className="text-muted-foreground mt-0.5">Modules</div>
                    </div>
                    <div className="bg-secondary/50 rounded-lg p-2.5 text-center">
                      <div className="font-bold text-[18px] text-nd-green">
                        {generatedCourse.module_mcqs?.reduce((s, m) => s + m.questions.length, 0)
                          ?? generatedCourse.quiz_questions?.length ?? 0}
                      </div>
                      <div className="text-muted-foreground mt-0.5">MCQs</div>
                    </div>
                    <div className="bg-secondary/50 rounded-lg p-2.5 text-center">
                      <div className="font-bold text-[18px] text-nd-blue">
                        {generatedCourse.module_booklets?.length ?? 0}
                      </div>
                      <div className="text-muted-foreground mt-0.5">Booklets</div>
                    </div>
                  </div>

                  {courseIndexUrl && (
                    <div className="rounded-lg overflow-hidden border border-border">
                      <iframe
                        src={courseIndexUrl}
                        title={`${generatedCourse.title} — Index`}
                        className="w-full h-44 bg-white"
                      />
                    </div>
                  )}

                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={handlePublishCourse}
                      disabled={publishingCourse}
                      className="px-5 py-2.5 rounded-xl bg-emerald-600 text-white text-[13px] font-bold uppercase tracking-wider hover:brightness-105 active:scale-95 transition-all shadow-md disabled:opacity-50 flex items-center gap-2"
                    >
                      <Sparkles className="w-4 h-4" />
                      {publishingCourse ? "Publishing…" : `Publish to ${generatedCourse.department}`}
                    </button>
                    <button
                      onClick={handleViewHTML}
                      className="px-4 py-2 rounded-lg border border-border bg-white text-foreground text-sm font-semibold hover:bg-secondary/40 transition flex items-center gap-2"
                    >
                      Generate & View HTML Course
                    </button>
                    {courseIndexUrl && (
                      <a href={courseIndexUrl} target="_blank" rel="noreferrer"
                        className="px-4 py-2 rounded-lg border border-border text-sm font-semibold hover:bg-secondary/40 transition">
                        Open Index PDF
                      </a>
                    )}
                  </div>

                  {publishMessage && <div className="text-[13px] text-nd-green">{publishMessage}</div>}
                </div>
              )}
            </div>
          </div>

          {/* ── module booklets section ── */}
          {generatedCourse && (generatedCourse.module_booklets?.length ?? 0) > 0 && (
            <div className="bg-card border border-border rounded-xl p-[18px]">

              {/* section header with sub-nav */}
              <div className="flex items-center justify-between mb-4">
                <div>
                  <div className="text-sm font-semibold">Module Booklets</div>
                  <div className="text-[12px] text-muted-foreground mt-0.5">
                    Each module has a detailed PDF booklet and an AI-generated assessment
                  </div>
                </div>
                {bookletView !== "list" && (
                  <button
                    onClick={() => { setBookletView("list"); setSelectedBooklet(null); setSelectedMCQModule(null); }}
                    className="text-[12px] text-muted-foreground hover:text-foreground flex items-center gap-1 transition"
                  >
                    ← All modules
                  </button>
                )}
              </div>

              {/* ── LIST VIEW ─────────────────────────────────────────────── */}
              {bookletView === "list" && (
                <div className="space-y-2">
                  {(generatedCourse.module_booklets ?? []).map((booklet) => {
                    const mcq = generatedCourse.module_mcqs?.find((m) => m.module_index === booklet.module_index);
                    return (
                      <div key={booklet.module_id}
                        className="flex items-center gap-3 rounded-lg border border-border bg-secondary/20 px-4 py-3">

                        {/* index bubble */}
                        <div className="w-9 h-9 rounded-lg bg-saffron/10 border border-saffron/20 flex items-center justify-center text-saffron font-bold text-sm flex-shrink-0">
                          {booklet.module_index}
                        </div>

                        {/* title + meta */}
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-[13px] truncate">{booklet.module_title}</div>
                          <div className="text-[11px] text-muted-foreground mt-0.5 flex items-center gap-2">
                            <span>{booklet.module_id}</span>
                            {mcq && (
                              <>
                                <span>·</span>
                                <span>{mcq.questions.length} MCQs</span>
                                <span>·</span>
                                {mcqGeneratorBadge(mcq.generated_by)}
                              </>
                            )}
                          </div>
                        </div>

                        {/* actions */}
                        <div className="flex items-center gap-2 flex-shrink-0">
                          <button
                            onClick={() => openBookletPdf(booklet)}
                            className="text-[12px] px-3 py-1.5 rounded-md border border-border hover:bg-secondary/60 transition font-medium"
                          >
                            Booklet PDF
                          </button>
                          {booklet.html_url && (
                            <a
                              href={`${API_BASE_URL}${booklet.html_url}`}
                              target="_blank"
                              rel="noreferrer"
                              className="text-[12px] px-3 py-1.5 rounded-md bg-nd-blue-light border border-nd-blue/20 text-nd-blue hover:bg-nd-blue/20 transition font-medium"
                            >
                              Interactive HTML
                            </a>
                          )}
                          {mcq && (
                            <button
                              onClick={() => openBookletMCQ(booklet)}
                              className="text-[12px] px-3 py-1.5 rounded-md bg-saffron/10 border border-saffron/20 text-saffron hover:bg-saffron/20 transition font-medium"
                            >
                              Preview MCQs
                            </button>
                          )}
                          <a
                            href={`${API_BASE_URL}${booklet.pdf_url}`}
                            target="_blank"
                            rel="noreferrer"
                            className="text-[12px] px-2 py-1.5 rounded-md border border-border hover:bg-secondary/60 transition text-muted-foreground"
                            title="Download booklet PDF"
                          >
                            ↓
                          </a>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* ── PDF VIEW ──────────────────────────────────────────────── */}
              {bookletView === "pdf" && selectedBooklet && (
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-saffron/10 border border-saffron/20 flex items-center justify-center text-saffron font-bold text-sm flex-shrink-0">
                      {selectedBooklet.module_index}
                    </div>
                    <div>
                      <div className="font-semibold text-[14px]">{selectedBooklet.module_title}</div>
                      <div className="text-[11px] text-muted-foreground">{selectedBooklet.module_id}</div>
                    </div>
                    <a
                      href={`${API_BASE_URL}${selectedBooklet.pdf_url}`}
                      target="_blank"
                      rel="noreferrer"
                      className="ml-auto text-[12px] px-3 py-1.5 rounded-md border border-border hover:bg-secondary/60 transition font-medium"
                    >
                      Open in new tab ↗
                    </a>
                  </div>

                  <div className="rounded-lg overflow-hidden border border-border bg-white">
                    <iframe
                      src={`${API_BASE_URL}${selectedBooklet.pdf_url}`}
                      title={selectedBooklet.module_title}
                      className="w-full"
                      style={{ height: "70vh" }}
                    />
                  </div>

                  {/* preview MCQ if available */}
                  {generatedCourse.module_mcqs?.find((m) => m.module_index === selectedBooklet.module_index) && (
                    <button
                      onClick={() => openBookletMCQ(selectedBooklet)}
                      className="text-[13px] px-4 py-2 rounded-lg bg-saffron/10 border border-saffron/20 text-saffron hover:bg-saffron/20 transition font-medium"
                    >
                      Preview this module's MCQs →
                    </button>
                  )}
                </div>
              )}

              {/* ── MCQ PREVIEW VIEW ──────────────────────────────────────── */}
              {bookletView === "mcq" && selectedBooklet && selectedMCQModule && (
                <div className="space-y-4">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-saffron/10 border border-saffron/20 flex items-center justify-center text-saffron font-bold text-sm flex-shrink-0">
                      {selectedBooklet.module_index}
                    </div>
                    <div className="flex-1">
                      <div className="font-semibold text-[14px]">{selectedBooklet.module_title} — Assessment Preview</div>
                      <div className="text-[11px] text-muted-foreground flex items-center gap-2 mt-0.5">
                        <span>{selectedMCQModule.questions.length} questions</span>
                        <span>·</span>
                        {mcqGeneratorBadge(selectedMCQModule.generated_by)}
                        <span>·</span>
                        <span>Pass mark: 70%</span>
                      </div>
                    </div>
                  </div>

                  <div className="rounded-lg border border-border bg-secondary/10 px-4 py-3 text-[12px] text-muted-foreground">
                    This is a read-only preview of the assessment. Employees take the live quiz on the Learning Portal after reading the module booklet.
                  </div>

                  <div className="space-y-4">
                    {selectedMCQModule.questions.map((q, qi) => (
                      <div key={q.id} className="rounded-lg border border-border bg-card p-4">
                        <div className="text-[11px] text-muted-foreground uppercase font-semibold mb-1.5 tracking-wide">
                          Question {qi + 1}
                        </div>
                        <div className="text-[14px] font-medium mb-3 leading-snug">{q.question}</div>

                        <div className="space-y-2">
                          {q.options.map((opt, oi) => (
                            <div
                              key={oi}
                              className={`flex items-start gap-2.5 rounded-lg px-3 py-2.5 text-[13px] border ${oi === q.correctOptionIndex
                                ? "bg-nd-green-light border-nd-green/30 text-nd-green font-medium"
                                : "bg-secondary/30 border-border text-muted-foreground"
                                }`}
                            >
                              <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[11px] font-bold flex-shrink-0 mt-0.5 ${oi === q.correctOptionIndex
                                ? "bg-nd-green text-white"
                                : "bg-border text-muted-foreground"
                                }`}>
                                {String.fromCharCode(65 + oi)}
                              </span>
                              <span>{opt}</span>
                            </div>
                          ))}
                        </div>

                        {q.explanation && (
                          <div className="mt-3 px-3 py-2 rounded-md bg-blue-50 border border-blue-100 text-[12px] text-blue-700 leading-relaxed">
                            <span className="font-semibold">Explanation: </span>{q.explanation}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>

                  <button
                    onClick={() => openBookletPdf(selectedBooklet)}
                    className="text-[13px] px-4 py-2 rounded-lg border border-border hover:bg-secondary/40 transition font-medium"
                  >
                    ← View Module Booklet PDF
                  </button>
                </div>
              )}
            </div>
          )}

          {/* ── legacy: single-PDF course (v2 fallback) ── */}
          {generatedCourse && !generatedCourse.module_booklets?.length && generatedCourse.pdf_url && (
            <div className="bg-card border border-border rounded-xl p-[18px]">
              <div className="text-sm font-semibold mb-3.5">Course PDF</div>
              <div className="rounded-lg overflow-hidden border border-border">
                <iframe
                  src={`${API_BASE_URL}${generatedCourse.pdf_url}`}
                  title={generatedCourse.title}
                  className="w-full h-72 bg-white"
                />
              </div>
              <div className="mt-2 text-[12px] text-muted-foreground break-all">{generatedCourse.pdf_path}</div>
            </div>
          )}

        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════
          LMS ANALYTICS TAB
      ══════════════════════════════════════════════════════════════════ */}
      {activeTab === "LMS Analytics" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3.5">
          <div className="bg-card border border-border rounded-xl p-[18px]">
            <div className="text-sm font-semibold mb-3.5">Department Headcount</div>
            <div className="space-y-2">
              {groupedHeadcount.map((group) => (
                <div key={group.department} className="flex items-center gap-3">
                  <div className="w-36 text-[13px]">{group.department}</div>
                  <div className="flex-1 h-2 bg-border rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full bg-saffron"
                      style={{ width: `${Math.min((group.employees + group.managers) * 10, 100)}%` }}
                    />
                  </div>
                  <div className="w-10 text-right text-xs font-semibold">
                    {group.employees + group.managers}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-card border border-border rounded-xl p-[18px]">
            <div className="text-sm font-semibold mb-3.5">Quick Actions</div>
            <div className="space-y-2 text-[13px]">
              <Link to="/holidays" className="block rounded-lg border border-border bg-secondary/30 px-4 py-3 hover:bg-secondary/50">
                Open Daily Calendar
              </Link>
              <Link to="/training" className="block rounded-lg border border-border bg-secondary/30 px-4 py-3 hover:bg-secondary/50">
                Open Training Material
              </Link>
              <Link to="/sop" className="block rounded-lg border border-border bg-secondary/30 px-4 py-3 hover:bg-secondary/50">
                Open SOP Library
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════
          WHAT'S NEW TAB
      ══════════════════════════════════════════════════════════════════ */}
      {activeTab === "What's New" && (
        <div className="max-w-2xl">
          <WhatsNewSection
            isAdmin={true}
            currentUser={user}
            onOpenComposer={() => setComposerOpen(true)}
          />

          {/* Update Composer Modal */}
          <UpdateComposerModal
            open={composerOpen}
            onClose={() => setComposerOpen(false)}
            onSubmit={async (data) => {
              await apiPost("/api/whats-new", {
                author_id: user?.id,
                author_name: user?.name,
                author_role: user?.role,
                department: user?.department,
                ...data,
              });
            }}
          />
        </div>
      )}
    </div>
  );
};

export default AdminDashboard;