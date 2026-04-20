import React, { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useAuth } from "@/contexts/AuthContext";
import { apiGet, apiPost } from "@/lib/api";
import {
  Trophy,
  TrendingUp,
  Users,
  Target,
  Award,
  BarChart3,
  ChevronDown,
  ChevronUp,
  X,
  Pencil,
  CheckCircle2,
  AlertTriangle,
  Clock,
  BookOpen,
  Star,
  Activity,
  Building2,
  ChevronRight,
  Flame,
  Zap,
  RefreshCw,
} from "lucide-react";
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

// ─── Types ────────────────────────────────────────────────────────────────────

interface KPIScores {
  learning: number;
  attendance: number;
  work_output: number;
  growth: number;
}

interface EmployeeKPI {
  employee_id: string;
  employee_name: string;
  department: string;
  month: string;
  scores: KPIScores;
  overall: number;
  rating: string;
  badges: string[];
  streak: number;
  level: string;
  leave_days: number;
  courses_done: number;
  avg_quiz_score: number;
  work_target: number;
  work_actual: number;
  work_rating_notes: string;
  work_rating_carried_forward: boolean;
}

interface DepartmentKPI {
  department: string;
  month: string;
  dept_avg: number;
  dept_rating: string;
  employees: EmployeeKPI[];
}

interface OrgKPI {
  month: string;
  org_avg: number;
  org_rating: string;
  departments: {
    department: string;
    dept_avg: number;
    dept_rating: string;
    employee_count: number;
    month: string;
  }[];
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const CURRENT_MONTH = new Date().toISOString().slice(0, 7); // "YYYY-MM"

const PILLAR_META = [
  { key: "learning",    label: "Learning",    color: "#FF7033", icon: <BookOpen className="w-3.5 h-3.5" /> },
  { key: "attendance",  label: "Attendance",  color: "#10b981", icon: <Clock className="w-3.5 h-3.5" /> },
  { key: "work_output", label: "Work Output", color: "#6366f1", icon: <Target className="w-3.5 h-3.5" /> },
  { key: "growth",      label: "Growth",      color: "#f59e0b", icon: <TrendingUp className="w-3.5 h-3.5" /> },
];

function ratingColor(rating: string): string {
  if (rating.includes("Exceptional")) return "text-emerald-500";
  if (rating.includes("Excellent"))   return "text-amber-500";
  if (rating.includes("Good"))        return "text-blue-500";
  if (rating.includes("Developing"))  return "text-orange-400";
  return "text-rose-500";
}

function scoreRingStyle(score: number) {
  const pct = Math.min(100, Math.max(0, score));
  const circum = 2 * Math.PI * 30; // radius 30
  const dash = (pct / 100) * circum;
  const gap  = circum - dash;
  return { dash, gap, circum };
}

const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.45, delay, ease: "easeOut" },
});

// ─── Score Ring ───────────────────────────────────────────────────────────────

const ScoreRing: React.FC<{ score: number; color: string; label: string; small?: boolean }> = ({
  score, color, label, small,
}) => {
  const r = small ? 22 : 30;
  const size = small ? 56 : 76;
  const circum = 2 * Math.PI * r;
  const dash = (Math.min(100, score) / 100) * circum;

  return (
    <div className="flex flex-col items-center gap-1.5">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#f1f5f9" strokeWidth={small ? 4 : 5} />
          <motion.circle
            cx={size / 2} cy={size / 2} r={r}
            fill="none"
            stroke={color}
            strokeWidth={small ? 4 : 5}
            strokeLinecap="round"
            strokeDasharray={`${dash} ${circum - dash}`}
            initial={{ strokeDasharray: `0 ${circum}` }}
            animate={{ strokeDasharray: `${dash} ${circum - dash}` }}
            transition={{ duration: 1.2, ease: "easeOut", delay: 0.3 }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={`font-bold text-slate-800 ${small ? "text-[11px]" : "text-[13px]"}`}>
            {Math.round(score)}
          </span>
        </div>
      </div>
      <span className="text-[9px] font-bold text-slate-400 uppercase tracking-widest text-center">{label}</span>
    </div>
  );
};

// ─── KPI Card (Employee self-view) ────────────────────────────────────────────

const PersonalKPICard: React.FC<{ kpi: EmployeeKPI }> = ({ kpi }) => {
  const radarData = PILLAR_META.map(p => ({
    pillar: p.label,
    score: kpi.scores[p.key as keyof KPIScores],
    fullMark: 100,
  }));

  return (
    <div className="space-y-6">
      {/* Header Hero */}
      <motion.div {...fadeUp(0)}
        className="bg-white border border-slate-100 rounded-[2rem] p-10 shadow-sm relative overflow-hidden"
      >
        <div className="absolute top-0 right-0 w-[350px] h-[350px] bg-amber-50/40 blur-[80px] -mr-32 -mt-32 rounded-full" />
        <div className="relative z-10">
          <div className="flex flex-col md:flex-row md:items-center gap-8">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-4">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em]">
                  {kpi.department} · {kpi.month}
                </span>
                {kpi.work_rating_carried_forward && (
                  <span className="text-[9px] font-bold bg-amber-50 text-amber-600 border border-amber-100 px-2 py-0.5 rounded-full">
                    Work target carried forward
                  </span>
                )}
              </div>
              <h1 className="text-4xl font-bold text-slate-900 mb-2 tracking-tight">
                Your KPI Report
              </h1>
              <p className="text-slate-500 text-base font-medium mb-6">{kpi.employee_name}</p>

              {/* Overall Score */}
              <div className="flex items-center gap-6">
                <div className="relative w-28 h-28">
                  <svg width="112" height="112" style={{ transform: "rotate(-90deg)" }}>
                    <circle cx="56" cy="56" r="48" fill="none" stroke="#f1f5f9" strokeWidth="8" />
                    <motion.circle
                      cx="56" cy="56" r="48"
                      fill="none"
                      stroke="#FF7033"
                      strokeWidth="8"
                      strokeLinecap="round"
                      strokeDasharray={`${(kpi.overall / 100) * (2 * Math.PI * 48)} ${2 * Math.PI * 48}`}
                      initial={{ strokeDasharray: `0 ${2 * Math.PI * 48}` }}
                      animate={{ strokeDasharray: `${(kpi.overall / 100) * (2 * Math.PI * 48)} ${2 * Math.PI * 48}` }}
                      transition={{ duration: 1.4, ease: "easeOut" }}
                    />
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="text-2xl font-bold text-slate-900">{Math.round(kpi.overall)}</span>
                    <span className="text-[9px] text-slate-400 font-bold uppercase">Overall</span>
                  </div>
                </div>
                <div>
                  <div className={`text-2xl font-bold mb-1 ${ratingColor(kpi.rating)}`}>{kpi.rating}</div>
                  <div className="flex items-center gap-2 text-sm text-slate-500">
                    <Flame className="w-4 h-4 text-orange-400" /> {kpi.streak} day streak
                  </div>
                  <div className="flex items-center gap-2 text-sm text-slate-500 mt-1">
                    <Zap className="w-4 h-4 text-amber-400" /> Level: {kpi.level}
                  </div>
                </div>
              </div>
            </div>

            {/* Radar Chart */}
            <div className="w-full md:w-[280px] h-[220px]">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData}>
                  <PolarGrid stroke="#e2e8f0" />
                  <PolarAngleAxis dataKey="pillar" tick={{ fontSize: 10, fontWeight: 600, fill: "#94a3b8" }} />
                  <Radar
                    name="Score"
                    dataKey="score"
                    stroke="#FF7033"
                    fill="#FF7033"
                    fillOpacity={0.12}
                    strokeWidth={2}
                  />
                  <Tooltip
                    contentStyle={{ borderRadius: "12px", border: "1px solid #f1f5f9", fontSize: "12px" }}
                    formatter={(val: number) => [`${val}%`, "Score"]}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Pillar Breakdown */}
      <motion.div {...fadeUp(0.1)} className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {PILLAR_META.map((p, i) => {
          const score = kpi.scores[p.key as keyof KPIScores];
          return (
            <motion.div
              key={p.key}
              {...fadeUp(0.1 + i * 0.05)}
              className="bg-white border border-slate-100 rounded-2xl p-6 flex flex-col items-center gap-3 shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="w-8 h-8 rounded-xl flex items-center justify-center" style={{ background: `${p.color}15`, color: p.color }}>
                {p.icon}
              </div>
              <ScoreRing score={score} color={p.color} label={p.label} />
              <div className="text-center">
                <div className="text-[11px] font-bold text-slate-400 uppercase tracking-widest">{p.label}</div>
                <div className="text-[10px] text-slate-300 mt-0.5">
                  {p.key === "learning"    && `${kpi.courses_done} courses · ${kpi.avg_quiz_score}% avg`}
                  {p.key === "attendance"  && `${kpi.leave_days} leave day${kpi.leave_days !== 1 ? "s" : ""}`}
                  {p.key === "work_output" && `${kpi.work_actual}/${kpi.work_target} target`}
                  {p.key === "growth"      && `${kpi.badges.length} badge${kpi.badges.length !== 1 ? "s" : ""}`}
                </div>
              </div>
            </motion.div>
          );
        })}
      </motion.div>

      {/* Badges */}
      {kpi.badges.length > 0 && (
        <motion.div {...fadeUp(0.25)} className="bg-white border border-slate-100 rounded-2xl p-8 shadow-sm">
          <div className="flex items-center gap-2 mb-5">
            <Award className="w-5 h-5 text-amber-500" />
            <h3 className="text-sm font-bold text-slate-800">Earned Badges</h3>
          </div>
          <div className="flex flex-wrap gap-2">
            {kpi.badges.map((b, i) => (
              <span key={i} className="px-4 py-2 bg-amber-50 border border-amber-100 text-amber-700 text-sm font-semibold rounded-xl">
                {b}
              </span>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  );
};

// ─── Rating Target Modal ──────────────────────────────────────────────────────

const RatingModal: React.FC<{
  employee: EmployeeKPI;
  month: string;
  onClose: () => void;
  onSave: () => void;
}> = ({ employee, month, onClose, onSave }) => {
  const [target, setTarget]   = useState<string>(String(employee.work_target || 100));
  const [actual, setActual]   = useState<string>(String(employee.work_actual || 0));
  const [notes, setNotes]     = useState<string>(employee.work_rating_notes || "");
  const [saving, setSaving]   = useState(false);
  const [error, setError]     = useState("");

  const handleSave = async () => {
    const t = parseFloat(target);
    const a = parseFloat(actual);
    if (isNaN(t) || t <= 0) { setError("Target must be a positive number"); return; }
    if (isNaN(a) || a < 0)  { setError("Actual must be a non-negative number"); return; }
    setSaving(true);
    try {
      await apiPost("/api/kpi/rate", {
        employee_id: employee.employee_id,
        department:  employee.department,
        month,
        work_target: t,
        work_actual: a,
        notes,
      });
      onSave();
      onClose();
    } catch {
      setError("Failed to save rating.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className="fixed inset-0 z-[100] flex items-center justify-center p-6 bg-slate-900/40 backdrop-blur-sm"
    >
      <motion.div
        initial={{ scale: 0.95, y: 20 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.95, y: 20 }}
        className="bg-white rounded-3xl w-full max-w-md p-8 shadow-2xl"
      >
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-lg font-bold text-slate-900">Set Work Rating</h2>
            <p className="text-[12px] text-slate-400 mt-0.5">{employee.employee_name} · {month}</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-slate-50 rounded-xl transition-colors">
            <X className="w-5 h-5 text-slate-400" />
          </button>
        </div>

        <div className="space-y-5">
          <div>
            <label className="text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-2 block">
              Work Target (units / tasks / %)
            </label>
            <input
              type="number" value={target} onChange={e => setTarget(e.target.value)}
              className="w-full bg-slate-50 border border-slate-100 rounded-xl px-4 py-3 text-sm font-semibold text-slate-900 outline-none focus:border-amber-300 transition-all"
              placeholder="100"
            />
          </div>
          <div>
            <label className="text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-2 block">
              Work Actual (achieved)
            </label>
            <input
              type="number" value={actual} onChange={e => setActual(e.target.value)}
              className="w-full bg-slate-50 border border-slate-100 rounded-xl px-4 py-3 text-sm font-semibold text-slate-900 outline-none focus:border-amber-300 transition-all"
              placeholder="0"
            />
          </div>
          <div>
            <label className="text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-2 block">
              Notes (optional)
            </label>
            <textarea
              value={notes} onChange={e => setNotes(e.target.value)}
              rows={2}
              className="w-full bg-slate-50 border border-slate-100 rounded-xl px-4 py-3 text-sm font-medium text-slate-600 outline-none focus:border-amber-300 transition-all resize-none"
              placeholder="Add notes for this employee..."
            />
          </div>
          {actual && target && parseFloat(target) > 0 && (
            <div className="bg-slate-50 border border-slate-100 rounded-xl px-4 py-3 flex items-center gap-3">
              <div className="text-[11px] text-slate-400 font-bold uppercase tracking-widest">Work Score</div>
              <div className="text-lg font-bold text-slate-900">
                {Math.min(100, Math.round((parseFloat(actual) / parseFloat(target)) * 100))}%
              </div>
            </div>
          )}
          {error && <p className="text-sm text-rose-500 font-medium">{error}</p>}
        </div>

        <div className="flex gap-3 mt-8">
          <button onClick={onClose} className="flex-1 py-3 rounded-xl border border-slate-100 text-sm font-bold text-slate-400 hover:bg-slate-50 transition-all">
            Cancel
          </button>
          <button
            disabled={saving}
            onClick={handleSave}
            className="flex-1 py-3 rounded-xl bg-[#30231D] text-white text-sm font-bold shadow-md hover:brightness-110 transition-all"
          >
            {saving ? "Saving…" : "Save Rating"}
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
};

// ─── Employee Row (Manager View) ──────────────────────────────────────────────

const EmployeeKPIRow: React.FC<{
  kpi: EmployeeKPI;
  month: string;
  onRate: (emp: EmployeeKPI) => void;
  index: number;
}> = ({ kpi, month, onRate, index }) => {
  const [expanded, setExpanded] = useState(false);

  const radarData = PILLAR_META.map(p => ({
    pillar: p.label,
    score: kpi.scores[p.key as keyof KPIScores],
    fullMark: 100,
  }));

  return (
    <motion.div {...fadeUp(0.05 + index * 0.04)} className="bg-white border border-slate-100 rounded-2xl overflow-hidden shadow-sm hover:shadow-md transition-shadow">
      {/* Row Header */}
      <div
        className="flex items-center gap-5 p-5 cursor-pointer group"
        onClick={() => setExpanded(e => !e)}
      >
        <div className="w-10 h-10 rounded-xl bg-[#30231D] text-white flex items-center justify-center text-sm font-bold flex-shrink-0">
          {index + 1}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h4 className="text-[14px] font-bold text-slate-800 truncate group-hover:text-[#FF7033] transition-colors">
              {kpi.employee_name}
            </h4>
            <span className={`text-[11px] font-bold ${ratingColor(kpi.rating)}`}>{kpi.rating}</span>
          </div>
          {/* Mini score bars */}
          <div className="flex items-center gap-3">
            {PILLAR_META.map(p => (
              <div key={p.key} className="flex items-center gap-1.5">
                <div className="w-12 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full rounded-full"
                    style={{ background: p.color }}
                    initial={{ width: 0 }}
                    animate={{ width: `${kpi.scores[p.key as keyof KPIScores]}%` }}
                    transition={{ duration: 0.8, delay: 0.2 + index * 0.04 }}
                  />
                </div>
                <span className="text-[9px] text-slate-400 font-bold">{Math.round(kpi.scores[p.key as keyof KPIScores])}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-4 flex-shrink-0">
          <div className="text-center hidden sm:block">
            <div className="text-2xl font-bold text-slate-900">{Math.round(kpi.overall)}</div>
            <div className="text-[9px] text-slate-400 font-bold uppercase tracking-widest">Overall</div>
          </div>
          <button
            onClick={e => { e.stopPropagation(); onRate(kpi); }}
            className="p-2 bg-indigo-50 text-indigo-600 rounded-xl hover:bg-indigo-600 hover:text-white transition-all"
            title="Set work rating"
          >
            <Pencil className="w-4 h-4" />
          </button>
          <div className="text-slate-200">
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </div>
        </div>
      </div>

      {/* Expanded Detail */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <div className="border-t border-slate-50 p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Stats */}
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  {PILLAR_META.map(p => (
                    <div key={p.key} className="bg-slate-50 rounded-xl p-4 text-center">
                      <ScoreRing score={kpi.scores[p.key as keyof KPIScores]} color={p.color} label={p.label} small />
                    </div>
                  ))}
                </div>
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div className="bg-slate-50 rounded-xl p-3">
                    <div className="text-[11px] text-slate-400 font-bold uppercase tracking-widest">Courses</div>
                    <div className="text-lg font-bold text-slate-800">{kpi.courses_done}</div>
                  </div>
                  <div className="bg-slate-50 rounded-xl p-3">
                    <div className="text-[11px] text-slate-400 font-bold uppercase tracking-widest">Streak</div>
                    <div className="text-lg font-bold text-orange-500">{kpi.streak}d</div>
                  </div>
                  <div className="bg-slate-50 rounded-xl p-3">
                    <div className="text-[11px] text-slate-400 font-bold uppercase tracking-widest">Leaves</div>
                    <div className="text-lg font-bold text-slate-800">{kpi.leave_days}</div>
                  </div>
                </div>
                {kpi.work_rating_notes && (
                  <div className="bg-amber-50 border border-amber-100 rounded-xl p-3 text-[12px] text-amber-700 font-medium">
                    📝 {kpi.work_rating_notes}
                  </div>
                )}
                {kpi.work_rating_carried_forward && (
                  <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
                    <RefreshCw className="w-3 h-3" /> Work target carried forward from previous month
                  </div>
                )}
              </div>

              {/* Radar */}
              <div className="h-[200px]">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={radarData}>
                    <PolarGrid stroke="#e2e8f0" />
                    <PolarAngleAxis dataKey="pillar" tick={{ fontSize: 9, fontWeight: 600, fill: "#94a3b8" }} />
                    <Radar dataKey="score" stroke="#FF7033" fill="#FF7033" fillOpacity={0.1} strokeWidth={2} />
                    <Tooltip contentStyle={{ borderRadius: "10px", border: "1px solid #f1f5f9", fontSize: "11px" }} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

// ─── Department View (Manager) ────────────────────────────────────────────────

const DepartmentView: React.FC<{ month: string }> = ({ month }) => {
  const [data, setData]         = useState<DepartmentKPI | null>(null);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState<string | null>(null);
  const [ratingTarget, setRatingTarget] = useState<EmployeeKPI | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    apiGet<DepartmentKPI>(`/api/kpi/department?month=${month}`)
      .then(setData)
      .catch((err) => {
        console.error(err);
        setError(err?.message || "Failed to load department KPI data");
      })
      .finally(() => setLoading(false));
  }, [month]);

  useEffect(() => { load(); }, [load]);

  if (loading) return (
    <div className="flex items-center justify-center py-32">
      <div className="w-8 h-8 border-4 border-amber-200 border-t-amber-500 rounded-full animate-spin" />
    </div>
  );

  if (error || !data) return (
    <div className="py-20 text-center">
      <AlertTriangle className="w-10 h-10 text-amber-400 mx-auto mb-4" />
      <p className="text-slate-500 text-sm font-medium mb-4">{error || "No department KPI data available."}</p>
      <button onClick={load} className="px-5 py-2.5 bg-[#30231D] text-white text-sm font-bold rounded-xl hover:brightness-110 transition-all inline-flex items-center gap-2">
        <RefreshCw className="w-4 h-4" /> Retry
      </button>
    </div>
  );

  return (
    <>
      <AnimatePresence>
        {ratingTarget && (
          <RatingModal
            employee={ratingTarget}
            month={month}
            onClose={() => setRatingTarget(null)}
            onSave={load}
          />
        )}
      </AnimatePresence>

      {/* Dept Header */}
      <motion.div {...fadeUp(0)} className="bg-white border border-slate-100 rounded-2xl p-8 mb-6 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em] mb-2">{month}</div>
            <h2 className="text-2xl font-bold text-slate-900">{data.department}</h2>
            <p className="text-slate-400 text-sm mt-1">{data.employees.length} employee{data.employees.length !== 1 ? "s" : ""}</p>
          </div>
          <div className="text-center">
            <div className="text-4xl font-bold text-slate-900">{Math.round(data.dept_avg)}</div>
            <div className={`text-sm font-bold mt-1 ${ratingColor(data.dept_rating)}`}>{data.dept_rating}</div>
            <div className="text-[10px] text-slate-400 uppercase tracking-widest mt-0.5">Dept Average</div>
          </div>
        </div>

        {/* Dept pillar averages */}
        {data.employees.length > 0 && (
          <div className="mt-6 grid grid-cols-4 gap-3">
            {PILLAR_META.map(p => {
              const avg = Math.round(data.employees.reduce((s, e) => s + e.scores[p.key as keyof KPIScores], 0) / data.employees.length);
              return (
                <div key={p.key} className="bg-slate-50 rounded-xl p-3 text-center">
                  <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-1">{p.label}</div>
                  <div className="h-1.5 bg-white rounded-full overflow-hidden mb-1.5">
                    <motion.div className="h-full rounded-full" style={{ background: p.color, width: `${avg}%` }}
                      initial={{ width: 0 }} animate={{ width: `${avg}%` }} transition={{ duration: 0.8 }}
                    />
                  </div>
                  <div className="text-sm font-bold text-slate-800">{avg}%</div>
                </div>
              );
            })}
          </div>
        )}
      </motion.div>

      {/* Employee rows */}
      {data.employees.length === 0 ? (
        <div className="py-20 text-center border-2 border-dashed border-slate-100 rounded-2xl text-slate-300 text-sm">
          No employees found in this department.
        </div>
      ) : (
        <div className="space-y-3">
          {data.employees.map((emp, i) => (
            <EmployeeKPIRow key={emp.employee_id} kpi={emp} month={month} onRate={setRatingTarget} index={i} />
          ))}
        </div>
      )}
    </>
  );
};

// ─── Org View (Admin) ─────────────────────────────────────────────────────────

const OrgView: React.FC<{ month: string }> = ({ month }) => {
  const [data, setData]       = useState<OrgKPI | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);
  const [drillDept, setDrillDept] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    apiGet<OrgKPI>(`/api/kpi/org?month=${month}`)
      .then(setData)
      .catch((err) => {
        console.error(err);
        setError(err?.message || "Failed to load org KPI data");
      })
      .finally(() => setLoading(false));
  }, [month]);

  useEffect(() => { load(); }, [load]);

  if (loading) return (
    <div className="flex items-center justify-center py-32">
      <div className="w-8 h-8 border-4 border-amber-200 border-t-amber-500 rounded-full animate-spin" />
    </div>
  );

  if (drillDept) {
    return (
      <div>
        <button
          onClick={() => setDrillDept(null)}
          className="mb-6 flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-slate-800 transition-colors"
        >
          ← Back to Org Overview
        </button>
        <DepartmentView month={month} />
      </div>
    );
  }

  if (error || !data) return (
    <div className="py-20 text-center">
      <AlertTriangle className="w-10 h-10 text-amber-400 mx-auto mb-4" />
      <p className="text-slate-500 text-sm font-medium mb-4">{error || "No organisation KPI data available."}</p>
      <button onClick={load} className="px-5 py-2.5 bg-[#30231D] text-white text-sm font-bold rounded-xl hover:brightness-110 transition-all inline-flex items-center gap-2">
        <RefreshCw className="w-4 h-4" /> Retry
      </button>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Org Header */}
      <motion.div {...fadeUp(0)} className="bg-white border border-slate-100 rounded-2xl p-8 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em] mb-2">Organisation · {month}</div>
            <h2 className="text-3xl font-bold text-slate-900">KPI Leaderboard</h2>
            <p className="text-slate-400 text-sm mt-1">{data.departments.length} departments</p>
          </div>
          <div className="text-center">
            <div className="text-4xl font-bold text-slate-900">{Math.round(data.org_avg)}</div>
            <div className={`text-sm font-bold mt-1 ${ratingColor(data.org_rating)}`}>{data.org_rating}</div>
            <div className="text-[10px] text-slate-400 uppercase tracking-widest mt-0.5">Org Average</div>
          </div>
        </div>
      </motion.div>

      {/* Department Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {data.departments.map((dept, i) => (
          <motion.div
            key={dept.department}
            {...fadeUp(0.05 + i * 0.04)}
            onClick={() => setDrillDept(dept.department)}
            className="bg-white border border-slate-100 rounded-2xl p-6 shadow-sm hover:shadow-lg hover:border-amber-100 cursor-pointer transition-all group"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-center">
                  <Building2 className="w-5 h-5 text-slate-400 group-hover:text-[#FF7033] transition-colors" />
                </div>
                <div>
                  <h3 className="text-[14px] font-bold text-slate-800 group-hover:text-[#FF7033] transition-colors">
                    {dept.department}
                  </h3>
                  <p className="text-[11px] text-slate-400">{dept.employee_count} employees</p>
                </div>
              </div>
              <ChevronRight className="w-4 h-4 text-slate-200 group-hover:text-amber-400 group-hover:translate-x-1 transition-all" />
            </div>

            <div className="flex items-end gap-3">
              <div className="flex-1">
                <div className="h-2 bg-slate-50 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full rounded-full bg-gradient-to-r from-amber-400 to-[#FF7033]"
                    initial={{ width: 0 }}
                    animate={{ width: `${dept.dept_avg}%` }}
                    transition={{ duration: 0.8, delay: 0.1 + i * 0.04 }}
                  />
                </div>
              </div>
              <div className="text-right flex-shrink-0">
                <div className="text-xl font-bold text-slate-900">{Math.round(dept.dept_avg)}</div>
                <div className={`text-[10px] font-bold ${ratingColor(dept.dept_rating)}`}>{dept.dept_rating}</div>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

// ─── Main KPI Manager Page ────────────────────────────────────────────────────

const KPIManager: React.FC = () => {
  const { user } = useAuth();
  const role = user?.role ?? "Employee";
  const isManager = role === "Manager" || role === "Admin";
  const isAdmin   = role === "Admin";

  const [month, setMonth]   = useState(CURRENT_MONTH);
  const [myKpi, setMyKpi]   = useState<EmployeeKPI | null>(null);
  const [myLoading, setMyLoading] = useState(true);
  const [myError, setMyError]     = useState<string | null>(null);

  // Always fetch own KPI for employees; managers/admins also see dept/org view
  const loadMyKpi = useCallback(() => {
    if (!isManager) {
      setMyLoading(true);
      setMyError(null);
      apiGet<EmployeeKPI>("/api/kpi/me")
        .then(setMyKpi)
        .catch((err) => {
          console.error(err);
          setMyError(err?.message || "Failed to load your KPI data");
        })
        .finally(() => setMyLoading(false));
    } else {
      setMyLoading(false);
    }
  }, [isManager]);

  useEffect(() => { loadMyKpi(); }, [loadMyKpi]);

  return (
    <div className="pb-20 max-w-[1280px] mx-auto px-4 md:px-6">
      {/* Page Header */}
      <motion.div {...fadeUp(0)} className="mb-8 pt-6">
        <div className="text-[10px] text-slate-400 font-bold uppercase tracking-[0.25em] flex items-center gap-2 mb-6">
          Main <ChevronRight className="w-3 h-3" /> <span className="text-slate-800 font-black">KPI Manager</span>
        </div>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 tracking-tight">
              Performance <span className="text-[#FF7033]">KPI Manager</span>
            </h1>
            <p className="text-slate-400 text-sm mt-1.5 font-medium">
              {isAdmin   && "Organisation-wide performance tracking"}
              {role === "Manager" && !isAdmin && `${user?.department} department performance`}
              {role === "Employee" && "Your personal performance report"}
            </p>
          </div>

          {/* Month Picker */}
          {isManager && (
            <div className="flex items-center gap-3">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-widest">Month</span>
              <input
                type="month"
                value={month}
                onChange={e => setMonth(e.target.value)}
                className="bg-slate-50 border border-slate-100 rounded-xl px-4 py-2 text-sm font-semibold text-slate-800 outline-none focus:border-amber-300 transition-all"
              />
            </div>
          )}
        </div>
      </motion.div>

      {/* Role-switched views */}
      {role === "Employee" && (
        myLoading ? (
          <div className="flex items-center justify-center py-32">
            <div className="w-8 h-8 border-4 border-amber-200 border-t-amber-500 rounded-full animate-spin" />
          </div>
        ) : myError ? (
          <div className="py-20 text-center">
            <AlertTriangle className="w-10 h-10 text-amber-400 mx-auto mb-4" />
            <p className="text-slate-500 text-sm font-medium mb-4">{myError}</p>
            <button onClick={loadMyKpi} className="px-5 py-2.5 bg-[#30231D] text-white text-sm font-bold rounded-xl hover:brightness-110 transition-all inline-flex items-center gap-2">
              <RefreshCw className="w-4 h-4" /> Retry
            </button>
          </div>
        ) : myKpi ? (
          <PersonalKPICard kpi={myKpi} />
        ) : (
          <div className="py-24 text-center text-slate-400">
            No KPI data available yet. Complete a course to get started!
          </div>
        )
      )}

      {role === "Manager" && !isAdmin && (
        <DepartmentView month={month} />
      )}

      {isAdmin && (
        <OrgView month={month} />
      )}
    </div>
  );
};

export default KPIManager;
