import React, { useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { useNavigate } from "react-router-dom";
import { apiGet } from "@/lib/api";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { 
  Bell, 
  Search, 
  LogOut, 
  Sparkles, 
  Menu, 
  Calendar, 
  BookOpen, 
  ClipboardList, 
  X,
  ChevronRight,
  Clock,
  LayoutDashboard
} from "lucide-react";

interface MeetingEvent {
  id: number | null;
  title: string;
  description?: string;
  date: string;
  start_time: string;
  end_time: string;
  location?: string;
  meeting_link?: string;
}

interface CalendarResponse {
  meetings?: MeetingEvent[];
}

interface Course {
  id: number | string;
  title: string;
  dept: string;
  status: string;
}

interface SOPEntry {
  title: string;
  department: string;
}

interface SOPResponse {
  entries: SOPEntry[];
}

const Topbar: React.FC<{ onMenuClick?: () => void }> = ({ onMenuClick }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [todayMeetings, setTodayMeetings] = useState<MeetingEvent[]>([]);
  const [assignedCourses, setAssignedCourses] = useState<Course[]>([]);
  const [assignedSops, setAssignedSops] = useState<SOPEntry[]>([]);
  const notifRef = useRef<HTMLDivElement>(null);

  const handleLogout = () => { logout(); navigate("/login"); };

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node))
        setNotificationsOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  useEffect(() => {
    if (!user?.department) return;
    const today = new Date();
    const isoToday = today.toISOString().slice(0, 10);
    const year = today.getFullYear();
    const month = today.getMonth() + 1;

    const fetchNotifications = async () => {
      try {
        const [calendarData, courseData, sopData] = await Promise.all([
          apiGet<CalendarResponse>(`/api/calendar?year=${year}&month=${month}`),
          apiGet<Course[]>(`/api/courses?department=${encodeURIComponent(user.department)}`).catch(() => []),
          apiGet<SOPResponse>(`/api/sops?department=${encodeURIComponent(user.department)}`).catch(() => ({ entries: [] })),
        ]);
        setTodayMeetings((calendarData.meetings ?? []).filter((m) => m.date === isoToday));
        setAssignedCourses(Array.isArray(courseData) ? courseData.slice(0, 4) : []);
        setAssignedSops(Array.isArray(sopData.entries) ? sopData.entries.slice(0, 4) : []);
      } catch { /* silent */ }
    };

    void fetchNotifications();
  }, [user?.department]);

  const notificationCount = useMemo(
    () => todayMeetings.length + assignedCourses.length + assignedSops.length,
    [assignedCourses.length, assignedSops.length, todayMeetings.length],
  );

  const initials = user?.name
    ? user.name.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase()
    : "U";

  return (
    <header className="h-20 bg-white border-b border-slate-100 flex items-center px-4 md:px-8 gap-4 md:gap-6 z-50 sticky top-0 transition-all">
      {/* Mobile Toggle */}
      <button
        className="md:hidden p-2.5 -ml-2 text-slate-600 hover:bg-slate-50 rounded-lg transition-colors"
        onClick={onMenuClick}
      >
        <Menu className="w-5 h-5" />
      </button>

      {/* Global Search */}
      <div className="flex-1 max-w-[440px] relative hidden lg:block">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
        <input
          type="text"
          placeholder="Search learning assets..."
          className="w-full h-10 pl-11 pr-5 bg-slate-50/50 border border-slate-100/50 rounded-xl text-[13px] text-slate-900 placeholder:text-slate-400 outline-none focus:bg-white focus:border-amber-200 transition-all duration-300"
        />
      </div>

      <div className="ml-auto flex items-center gap-6">
        {/* Intelligence Action */}
        <button
          onClick={() => navigate("/monitoring")}
          className="hidden md:flex items-center gap-2.5 px-4 py-2 rounded-xl bg-slate-50 border border-slate-100 hover:border-amber-200 hover:bg-amber-50/30 transition-all group active:scale-95"
        >
          <Sparkles className="w-4 h-4 text-[#FF7033]" />
          <span className="text-[13px] font-semibold text-slate-700">Intelligence Hub</span>
        </button>

        {/* Notifications */}
        <div ref={notifRef} className="relative">
          <button
            onClick={() => setNotificationsOpen((v) => !v)}
            className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all ${notificationsOpen ? "bg-slate-100 text-slate-900 shadow-sm" : "text-slate-400 hover:bg-slate-50 hover:text-slate-600"}`}
          >
            <Bell className="w-[18px] h-[18px]" />
            {notificationCount > 0 && (
              <span className="absolute top-2 right-2 w-2 h-2 bg-[#FF7033] rounded-full border-2 border-white" />
            )}
          </button>

          {/* Notification Panel */}
          {notificationsOpen && (
            <div className="absolute right-0 top-[calc(100%+8px)] w-[360px] max-w-[calc(100vw-2rem)] bg-white border border-slate-100 rounded-2xl shadow-xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200">
              <div className="px-5 py-4 border-b border-slate-50 bg-slate-50/50 flex items-center justify-between">
                <div>
                  <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Update Center</h3>
                  <p className="text-sm font-semibold text-slate-900 mt-0.5">{notificationCount} active notifications</p>
                </div>
                <button onClick={() => setNotificationsOpen(false)} className="p-1.5 hover:bg-slate-200 rounded-lg transition-colors">
                  <X className="w-4 h-4 text-slate-400" />
                </button>
              </div>

              <div className="max-h-[400px] overflow-y-auto p-2 space-y-1">
                <NotifSection title="Schedule" icon={<Calendar className="w-3.5 h-3.5" />} count={todayMeetings.length} empty="No sessions today.">
                  {todayMeetings.map((m) => (
                    <NotifItem key={m.title} icon={<Clock className="w-3.5 h-3.5" />} title={m.title} sub={`${m.start_time} - ${m.end_time}`} />
                  ))}
                </NotifSection>

                <NotifSection title="Learning" icon={<BookOpen className="w-3.5 h-3.5" />} count={assignedCourses.length} empty="None today.">
                  {assignedCourses.map((c) => (
                    <NotifItem key={c.id} icon={<LayoutDashboard className="w-3.5 h-3.5" />} title={c.title} sub={c.dept} />
                  ))}
                </NotifSection>

                <NotifSection title="Operations" icon={<ClipboardList className="w-3.5 h-3.5" />} count={assignedSops.length} empty="None assigned.">
                  {assignedSops.map((s) => (
                    <NotifItem key={s.title} icon={<ClipboardList className="w-3.5 h-3.5" />} title={s.title} sub={s.department} />
                  ))}
                </NotifSection>
              </div>
            </div>
          )}
        </div>

        <div className="w-px h-6 bg-slate-100 mx-1" />

        {/* User Menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="flex items-center gap-3 p-1 rounded-xl hover:bg-slate-50 transition-all outline-none border border-transparent hover:border-slate-100">
              <div className="w-9 h-9 rounded-lg bg-[#30231D] flex items-center justify-center font-bold text-white shadow-md text-xs border border-white/5 opacity-90 transition-opacity group-hover:opacity-100">
                {(user as any)?.avatar_url ? (
                  <img src={(user as any).avatar_url} alt={user?.name} className="w-full h-full rounded-lg object-cover" />
                ) : initials}
              </div>
              <div className="hidden lg:block text-left">
                <p className="text-[13px] font-semibold text-slate-800 leading-none">{user?.name.split(" ")[0]}</p>
                <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mt-1.5">{user?.role}</p>
              </div>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-60 p-2 rounded-xl bg-white border-slate-100 shadow-xl">
            <DropdownMenuLabel className="px-3 py-3">
              <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">Operator Identity</p>
              <p className="text-sm font-semibold text-slate-900 mt-1">{user?.name}</p>
              <p className="text-[11px] text-slate-500 font-medium">{user?.email}</p>
            </DropdownMenuLabel>
            <DropdownMenuSeparator className="my-1 bg-slate-50" />
            <DropdownMenuItem onClick={() => navigate("/monitoring")} className="rounded-lg gap-3 py-2.5 text-[13px] font-medium text-slate-700 cursor-pointer hover:bg-slate-50">
              <Sparkles className="w-4 h-4 text-amber-500" /> Intelligence Hub
            </DropdownMenuItem>
            <DropdownMenuItem onClick={handleLogout} className="rounded-lg gap-3 py-2.5 text-[13px] font-medium text-rose-600 focus:text-rose-600 focus:bg-rose-50 cursor-pointer">
              <LogOut className="w-4 h-4" /> Terminate Session
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
};

const NotifSection: React.FC<{ title: string; icon: React.ReactNode; count: number; empty: string; children?: React.ReactNode; }> = ({ title, icon, count, empty, children }) => (
  <div className="p-1">
    <div className="flex items-center gap-2.5 mb-2 px-3">
      <span className="text-slate-300">{icon}</span>
      <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{title}</h4>
      {count > 0 && <span className="text-[10px] font-bold text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full ml-auto">{count}</span>}
    </div>
    {count === 0 ? <p className="text-[11px] text-slate-300 px-10 pb-2">{empty}</p> : <div className="space-y-0.5">{children}</div>}
  </div>
);

const NotifItem: React.FC<{ icon: React.ReactNode; title: string; sub: string; }> = ({ icon, title, sub }) => (
  <div className="flex items-center gap-3.5 p-2.5 rounded-xl hover:bg-slate-50 transition-all border border-transparent hover:border-slate-100 group cursor-pointer">
    <div className="w-9 h-9 rounded-lg bg-white border border-slate-50 flex items-center justify-center text-slate-300 group-hover:text-amber-500 transition-colors shadow-sm">{icon}</div>
    <div className="flex-1 min-w-0">
      <p className="text-[13px] font-semibold text-slate-700 truncate group-hover:text-slate-900 transition-colors tracking-tight">{title}</p>
      <p className="text-[10px] text-slate-400 font-medium mt-0.5">{sub}</p>
    </div>
    <ChevronRight className="w-3.5 h-3.5 text-slate-200 group-hover:translate-x-1 transition-all" />
  </div>
);

export default Topbar;
