import React, { useEffect, useMemo, useState } from "react";
import { useAuth, type UserRole } from "@/contexts/AuthContext";
import { useToast } from "@/hooks/use-toast";
import { apiGet, apiPost } from "@/lib/api";
import { 
  Calendar as CalendarIcon, 
  ChevronLeft, 
  ChevronRight, 
  Clock, 
  Plus, 
  Users, 
  Sparkles,
  X,
  Link as LinkIcon,
  ChevronDown
} from "lucide-react";
import { motion } from "framer-motion";

interface HolidayEvent {
  date: string;
  name: string;
  type: "Festival" | "National" | "Optional" | string;
}

interface MeetingAttendee {
  id: number;
  name: string;
  email: string;
  rsvp?: string;
}

interface MeetingEvent {
  id: number | null;
  organizer_id?: number | string;
  title: string;
  description?: string;
  date: string;
  start_time: string;
  end_time: string;
  location?: string;
  meeting_link?: string;
  organizer_name?: string;
  attendees?: MeetingAttendee[];
}

interface LeaveEvent {
  id: number;
  employee_id?: number | string;
  employee_name: string;
  department: string;
  leave_type: string;
  start_date: string;
  end_date: string;
  status: "pending" | "approved" | "rejected";
}

interface EmployeeOption {
  id: number | string;
  name: string;
  department: string;
  role: UserRole | string;
}

interface ApiCalendarResponse {
  holidays?: HolidayEvent[];
  meetings?: MeetingEvent[];
  leaves?: LeaveEvent[];
}

type MarkerType = "holiday" | "meeting" | "leave-approved" | "leave-pending";

type DayMarker = {
  type: MarkerType;
  label: string;
};

type AgendaItem = {
  key: string;
  date: string;
  title: string;
  subtitle: string;
  type: MarkerType;
  link?: string;
};

type CalendarPanel = {
  id: string;
  title: string;
  subtitle: string;
  markers: Map<string, DayMarker[]>;
  agenda: AgendaItem[];
};

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

const markerClass: Record<MarkerType, string> = {
  holiday: "bg-orange-50 text-[#FF7033] border-orange-100",
  meeting: "bg-amber-50 text-amber-700 border-amber-100",
  "leave-approved": "bg-emerald-50 text-emerald-700 border-emerald-100",
  "leave-pending": "bg-slate-50 text-slate-400 border-slate-100",
};

const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4, delay, ease: "easeOut" } as const,
});

const toNormalizedRole = (value: string | undefined | null): UserRole => {
  const role = String(value ?? "").trim().toLowerCase();
  if (role === "admin") return "Admin";
  if (role === "manager") return "Manager";
  return "Employee";
};

const HolidayCalendar: React.FC = () => {
  const { user, hasRole } = useAuth();
  const { toast } = useToast();
  const now = new Date();

  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [holidays, setHolidays] = useState<HolidayEvent[]>([]);
  const [meetings, setMeetings] = useState<MeetingEvent[]>([]);
  const [leaves, setLeaves] = useState<LeaveEvent[]>([]);
  const [employees, setEmployees] = useState<EmployeeOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [savingMeeting, setSavingMeeting] = useState(false);
  
  const [meetingForm, setMeetingForm] = useState({
    title: "",
    date: "",
    start_time: "10:00",
    end_time: "10:30",
    location: "Corporate Hub",
    meeting_link: "",
    description: "",
    attendee_ids: [] as string[],
  });

  const firstDay = new Date(year, month - 1, 1).getDay();
  const totalDays = new Date(year, month, 0).getDate();
  const today = now.getMonth() + 1 === month && now.getFullYear() === year ? now.getDate() : -1;

  const monthLabel = new Date(year, month - 1, 1).toLocaleString("default", {
    month: "long",
    year: "numeric",
  });

  const fetchCalendar = React.useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiGet<ApiCalendarResponse>(`/api/calendar?year=${year}&month=${month}`);
      setHolidays(Array.isArray(data?.holidays) ? data.holidays : []);
      setMeetings(Array.isArray(data?.meetings) ? data.meetings : []);
      setLeaves(Array.isArray(data?.leaves) ? data.leaves : []);
    } catch (err: unknown) {
      console.error("Calendar fetch error:", err);
    } finally {
      setLoading(false);
    }
  }, [year, month]);

  useEffect(() => {
    void fetchCalendar();
  }, [fetchCalendar]);

  useEffect(() => {
    const fetchEmployees = async () => {
      try {
        const data = await apiGet<EmployeeOption[]>("/api/employees");
        setEmployees(Array.isArray(data) ? data : []);
      } catch (err: unknown) {
        console.error("Employees fetch error:", err);
      }
    };
    void fetchEmployees();
  }, []);

  const myId = String(user?.id);
  const myDepartment = user?.department ?? "";

  const roleBuckets = useMemo(() => {
    const allEmployees = employees.filter((employee) => toNormalizedRole(employee.role) === "Employee");
    const allManagers = employees.filter((employee) => toNormalizedRole(employee.role) === "Manager");
    const departmentEmployees = allEmployees.filter((employee) => employee.department === myDepartment);
    return {
      allEmployeeIds: new Set(allEmployees.map((employee) => String(employee.id))),
      allManagerIds: new Set(allManagers.map((employee) => String(employee.id))),
      departmentEmployeeIds: new Set(departmentEmployees.map((employee) => String(employee.id))),
      selfIds: new Set([myId]),
    };
  }, [employees, myDepartment, myId]);

  const buildPanel = React.useCallback((
    id: string,
    title: string,
    subtitle: string,
    relevantIds: Set<string>,
    options: { leaveMode: "self" | "named"; meetingMode: "self" | "named"; },
  ): CalendarPanel => {
    const markers = new Map<string, DayMarker[]>();
    const agenda: AgendaItem[] = [];
 
    holidays.forEach((holiday) => {
      const marker = { type: "holiday" as MarkerType, label: holiday.name };
      const current = markers.get(holiday.date) ?? [];
      current.push(marker);
      markers.set(holiday.date, current);
      agenda.push({ key: `${id}-h-${holiday.date}`, date: holiday.date, title: holiday.name, subtitle: holiday.type, type: "holiday" });
    });
 
    meetings.filter(m => {
      const oid = String(m.organizer_id);
      if (relevantIds.has(oid)) return true;
      return (m.attendees ?? []).some(a => relevantIds.has(String(a.id)));
    }).forEach(m => {
      const marker = { type: "meeting" as MarkerType, label: m.title };
      const current = markers.get(m.date) ?? [];
      current.push(marker);
      markers.set(m.date, current);
      agenda.push({ key: `${id}-m-${m.id}`, date: m.date, title: m.title, subtitle: `${m.start_time}-${m.end_time}`, type: "meeting", link: m.meeting_link });
    });
 
    leaves.filter(l => {
      const eid = String(l.employee_id);
      if (relevantIds.has(eid)) return true;
      if (options.leaveMode === "self") return l.employee_name === user?.name;
      return l.department === myDepartment;
    }).forEach(l => {
      const type = l.status === "approved" ? "leave-approved" as MarkerType : "leave-pending" as MarkerType;
      const marker = { type, label: `${l.employee_name} (${l.leave_type})` };
      
      const start = new Date(l.start_date);
      const end = new Date(l.end_date);
      for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
        if (d.getFullYear() === year && d.getMonth() + 1 === month) {
          const iso = d.toISOString().split('T')[0];
          const current = markers.get(iso) ?? [];
          current.push(marker);
          markers.set(iso, current);
        }
      }
      agenda.push({ key: `${id}-l-${l.id}`, date: l.start_date, title: `${l.employee_name} Leave`, subtitle: `${l.leave_type} | ${l.status}`, type });
    });
 
    return { id, title, subtitle, markers, agenda: agenda.sort((a,b) => a.date.localeCompare(b.date)).slice(0, 10) };
  }, [holidays, meetings, leaves, user?.name, myDepartment, year, month]);

  const panels = useMemo(() => {
    if (!user) return [];
    const role = toNormalizedRole(user.role);
    if (role === "Employee") return [buildPanel("self", "Personal Schedule", "Individual milestones and calendar oversight.", roleBuckets.selfIds, { leaveMode: "self", meetingMode: "self" })];
    if (role === "Manager") return [
      buildPanel("dept", "Team Roadmap", "Collaborative calendar for department movement.", roleBuckets.departmentEmployeeIds, { leaveMode: "named", meetingMode: "named" }),
      buildPanel("self", "Personal Agenda", "Your institutional presence and schedule.", roleBuckets.selfIds, { leaveMode: "self", meetingMode: "self" })
    ];
    return [
      buildPanel("org", "Institutional Overview", "Organization-wide movement and scheduling.", roleBuckets.allEmployeeIds, { leaveMode: "named", meetingMode: "named" }),
      buildPanel("self", "Personal Agenda", "Administrative schedule and high-priority alerts.", roleBuckets.selfIds, { leaveMode: "self", meetingMode: "self" })
    ];
  }, [user, roleBuckets, buildPanel]);

  const handleScheduleMeeting = async () => {
    if (!meetingForm.title || !meetingForm.date) return;
    setSavingMeeting(true);
    try {
      await apiPost("/api/meetings", { ...meetingForm, organizer_id: user?.id });
      setMeetingForm({ title: "", date: "", start_time: "10:00", end_time: "10:30", location: "Corporate Hub", meeting_link: "", description: "", attendee_ids: [] });
      await fetchCalendar();
      toast({ title: "Schedule Updated", description: "Successfully updated the institutional calendar." });
    } finally {
      setSavingMeeting(false);
    }
  };

  return (
    <div className="pb-20 max-w-[1280px] mx-auto px-6">
      <header className="mb-12 pt-6">
        <div className="text-[10px] text-slate-400 font-bold uppercase tracking-[0.25em] mb-6 flex items-center gap-2">
          Administration <ChevronRight className="w-3 h-3" /> <span className="text-slate-800 font-black">Temporal Hub</span>
        </div>
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-8">
          <div>
            <h1 className="text-4xl font-bold text-slate-900 mb-4 tracking-tight">Institutional Calendar</h1>
            <p className="text-lg text-slate-500 font-medium max-w-2xl leading-relaxed">
              Synchronized oversight of holidays, resource availability, and critical meeting transmissions across the ecosystem.
            </p>
          </div>
          <div className="flex items-center gap-3 bg-white p-2 rounded-2xl border border-slate-100 shadow-sm">
             <button onClick={() => { if(month === 1) { setYear(y => y-1); setMonth(12); } else setMonth(m => m-1); }} className="w-10 h-10 rounded-xl flex items-center justify-center text-slate-400 hover:bg-slate-50 hover:text-amber-600 transition-all"><ChevronLeft className="w-5 h-5" /></button>
             <div className="text-[13px] font-bold text-slate-800 min-w-[160px] text-center">{monthLabel}</div>
             <button onClick={() => { if(month === 12) { setYear(y => y+1); setMonth(1); } else setMonth(m => m+1); }} className="w-10 h-10 rounded-xl flex items-center justify-center text-slate-400 hover:bg-slate-50 hover:text-amber-600 transition-all"><ChevronRight className="w-5 h-5" /></button>
          </div>
        </div>
      </header>

      <div className={`grid gap-10 ${panels.length === 1 ? 'grid-cols-1' : 'grid-cols-1 lg:grid-cols-2'}`}>
        {panels.map((panel) => (
          <div key={panel.id} className="bg-white border border-slate-100 rounded-3xl p-10 relative shadow-sm group">
            <div className="absolute top-0 right-0 w-32 h-32 bg-amber-50/10 blur-3xl rounded-full" />
            <div className="flex items-center justify-between mb-10">
              <div>
                <h3 className="text-xl font-bold text-slate-900 tracking-tight group-hover:text-amber-600 transition-colors">{panel.title}</h3>
                <p className="text-[11px] text-slate-400 font-bold uppercase tracking-widest mt-1.5">{panel.subtitle}</p>
              </div>
              <CalendarIcon className="w-5 h-5 text-slate-200" />
            </div>

            <div className="grid grid-cols-7 gap-3 mb-12">
              {DAYS.map(d => (
                <div key={d} className="text-[10px] font-bold text-slate-400 text-center uppercase tracking-widest mb-3">{d}</div>
              ))}
              {Array.from({ length: firstDay }).map((_, i) => (
                <div key={`e-${i}`} className="aspect-square opacity-0" />
              ))}
              {Array.from({ length: totalDays }).map((_, i) => {
                const day = i + 1;
                const iso = `${year}-${String(month).padStart(2,'0')}-${String(day).padStart(2,'0')}`;
                const mks = panel.markers.get(iso) ?? [];
                const isT = day === today;
                return (
                  <div key={day} className={`aspect-square rounded-xl border p-2 flex flex-col gap-1 transition-all group/day ${isT ? 'bg-amber-500 border-transparent shadow-lg scale-105' : 'bg-slate-50/20 border-slate-100 hover:bg-white hover:border-amber-200'}`}>
                    <div className={`text-[11px] font-bold ${isT ? 'text-white' : 'text-slate-400'}`}>{day}</div>
                    <div className="flex-1 flex flex-col gap-0.5 overflow-hidden">
                      {mks.slice(0, 2).map((m, mi) => (
                        <div key={mi} className={`w-full h-1 rounded-full ${markerClass[m.type].split(' ')[0]}`} />
                      ))}
                      {mks.length > 2 && <div className="text-[8px] font-bold text-slate-300 leading-none">+{mks.length-2}</div>}
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="space-y-4">
               <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-6">Agenda Highlights</h4>
               {panel.agenda.length === 0 ? (
                 <div className="py-12 text-center border-2 border-dashed border-slate-50 rounded-2xl bg-slate-50/20 text-[12px] text-slate-300 font-medium">No schedule items identified for this cycle.</div>
               ) : (
                 <div className="space-y-2.5">
                    {panel.agenda.map(item => (
                      <div key={item.key} className="flex items-center gap-5 p-4 rounded-2xl border border-slate-50 bg-slate-50/30 hover:bg-white hover:border-amber-100 hover:shadow-lg hover:shadow-amber-900/5 transition-all group/item">
                         <div className={`w-10 h-10 rounded-xl flex items-center justify-center border shadow-sm group-hover/item:scale-105 transition-transform ${markerClass[item.type]}`}>
                            {item.type === 'holiday' ? <Sparkles className="w-4 h-4" /> : item.type === 'meeting' ? <Users className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                         </div>
                         <div className="flex-1 min-w-0">
                            <h5 className="text-[14px] font-bold text-slate-800 transition-colors truncate">{item.title}</h5>
                            <p className="text-[11px] text-slate-400 font-semibold mt-0.5 uppercase tracking-wide">{item.subtitle}</p>
                         </div>
                         {item.link && (
                           <a href={item.link} target="_blank" rel="noreferrer" className="w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center text-amber-600 hover:bg-amber-500 hover:text-white transition-all shadow-sm"><LinkIcon className="w-3.5 h-3.5" /></a>
                         )}
                      </div>
                    ))}
                 </div>
               )}
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_400px] gap-10 mt-10">
        <div className="bg-white border border-slate-100 rounded-3xl p-10 relative shadow-sm">
          <div className="flex items-center justify-between mb-10">
            <h3 className="text-xl font-bold text-slate-900 tracking-tight">Broadcast Schedule</h3>
            <Plus className="w-5 h-5 text-slate-200" />
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
             <div className="space-y-6">
                <div>
                   <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-3 block">Objective Designation</label>
                   <input value={meetingForm.title} onChange={e => setMeetingForm({...meetingForm, title: e.target.value})} type="text" placeholder="Strategic Check-in..." className="w-full bg-slate-50/50 border border-slate-100 rounded-xl px-5 py-3.5 text-sm font-semibold text-slate-800 focus:bg-white focus:border-amber-200 transition-all outline-none" />
                </div>
                <div className="grid grid-cols-2 gap-4">
                   <div>
                      <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-3 block">Deployment Date</label>
                      <input value={meetingForm.date} onChange={e => setMeetingForm({...meetingForm, date: e.target.value})} type="date" className="w-full bg-slate-50/50 border border-slate-100 rounded-xl px-5 py-3.5 text-sm font-semibold text-slate-800 focus:bg-white focus:border-amber-200 transition-all outline-none" />
                   </div>
                   <div>
                      <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-3 block">Strategic Venue</label>
                      <input value={meetingForm.location} onChange={e => setMeetingForm({...meetingForm, location: e.target.value})} type="text" placeholder="Institutional Hub" className="w-full bg-slate-50/50 border border-slate-100 rounded-xl px-5 py-3.5 text-sm font-semibold text-slate-800 focus:bg-white focus:border-amber-200 transition-all outline-none" />
                   </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                   <div>
                      <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-3 block">Commencement</label>
                      <input value={meetingForm.start_time} onChange={e => setMeetingForm({...meetingForm, start_time: e.target.value})} type="time" className="w-full bg-slate-50/50 border border-slate-100 rounded-xl px-5 py-3.5 text-sm font-semibold text-slate-800 focus:bg-white focus:border-amber-200 transition-all outline-none" />
                   </div>
                   <div>
                      <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-3 block">Termination</label>
                      <input value={meetingForm.end_time} onChange={e => setMeetingForm({...meetingForm, end_time: e.target.value})} type="time" className="w-full bg-slate-50/50 border border-slate-100 rounded-xl px-5 py-3.5 text-sm font-semibold text-slate-800 focus:bg-white focus:border-amber-200 transition-all outline-none" />
                   </div>
                </div>
             </div>
             <div className="space-y-6">
                <div>
                   <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-3 block">Digital Link</label>
                   <input value={meetingForm.meeting_link} onChange={e => setMeetingForm({...meetingForm, meeting_link: e.target.value})} type="text" placeholder="https://meet.namandarshan.com/..." className="w-full bg-slate-50/50 border border-slate-100 rounded-xl px-5 py-3.5 text-sm font-semibold text-slate-800 focus:bg-white focus:border-amber-200 transition-all outline-none" />
                </div>
                <div>
                   <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-3 block">Executive Summary</label>
                   <textarea value={meetingForm.description} onChange={e => setMeetingForm({...meetingForm, description: e.target.value})} rows={3} placeholder="Provide context for attendees..." className="w-full bg-slate-50/50 border border-slate-100 rounded-xl px-5 py-3.5 text-sm font-medium text-slate-600 focus:bg-white focus:border-amber-200 transition-all outline-none resize-none" />
                </div>
                <button onClick={handleScheduleMeeting} disabled={savingMeeting} className="enterprise-btn-primary w-full py-4 uppercase tracking-widest font-bold text-[11px]">
                   {savingMeeting ? "Broadcasting..." : "Confirm Schedule Update"}
                </button>
             </div>
          </div>
        </div>

        <div className="bg-white border border-slate-100 rounded-3xl p-10 flex flex-col shadow-sm">
          <div className="flex items-center justify-between mb-10">
            <h3 className="text-lg font-bold text-slate-800 tracking-tight">Personnel Inclusion</h3>
            <Users className="w-5 h-5 text-slate-200" />
          </div>
          <div className="flex-1 space-y-2.5 overflow-y-auto max-h-[460px] pr-2 scrollbar-none">
             {employees.filter(e => String(e.id) !== myId).map(e => (
               <label key={e.id} className="flex items-center justify-between p-4 rounded-2xl border border-slate-50 bg-slate-50/20 hover:bg-white hover:border-amber-100 transition-all cursor-pointer group">
                  <div className="flex-1">
                     <div className="text-[13px] font-bold text-slate-800 group-hover:text-amber-600 transition-colors">{e.name}</div>
                     <div className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mt-1">{e.department} · {e.role}</div>
                  </div>
                  <input type="checkbox" checked={meetingForm.attendee_ids.includes(String(e.id))} onChange={() => {
                    const ids = meetingForm.attendee_ids.includes(String(e.id)) ? meetingForm.attendee_ids.filter(id => id !== String(e.id)) : [...meetingForm.attendee_ids, String(e.id)];
                    setMeetingForm({...meetingForm, attendee_ids: ids});
                  }} className="w-5 h-5 rounded-lg border-2 border-slate-200 checked:bg-amber-500 checked:border-transparent transition-all cursor-pointer" />
               </label>
             ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default HolidayCalendar;
