import React from "react";
import { motion } from "framer-motion";
import { useAuth } from "@/contexts/AuthContext";

const stats = [
  { icon: "📚", label: "Courses Enrolled", value: "8", sub: "3 in progress", color: "text-saffron", bg: "bg-saffron/10" },
  { icon: "✅", label: "Completed", value: "5", sub: "This quarter", color: "text-nd-green", bg: "bg-nd-green/10" },
  { icon: "⏱️", label: "Learning Hours", value: "42h", sub: "This month", color: "text-nd-blue", bg: "bg-nd-blue/10" },
  { icon: "📅", label: "Leave Balance", value: "12", sub: "Days remaining", color: "text-teal", bg: "bg-teal/10" },
  { icon: "🏆", label: "LMS Score", value: "87%", sub: "Dept rank: #3", color: "text-gold", bg: "bg-gold/10" },
  { icon: "🔔", label: "Pending Tasks", value: "3", sub: "2 due this week", color: "text-maroon", bg: "bg-maroon/10" },
];

const continueLearning = [
  { name: "Sankalp Confirmation Protocol", progress: 72, color: "bg-saffron", textColor: "text-saffron", icon: "📞" },
  { name: "CRM & WhatsApp Sales Ops", progress: 45, color: "bg-nd-blue", textColor: "text-nd-blue", icon: "💬" },
  { name: "Empathetic Communication", progress: 90, color: "bg-nd-green", textColor: "text-nd-green", icon: "🤝" },
  { name: "Temple Protocols & Entry", progress: 20, color: "bg-gold", textColor: "text-gold", icon: "🛕" },
];

const announcements = [
  { title: "New Course: Char Dham Yatra Ops 2025", sub: "Mandatory for all Ops team members. Deadline: Apr 15", borderColor: "border-l-saffron", bg: "bg-saffron/5" },
  { title: "Mahashivratri Surge Protocol Updated", sub: "Review updated SOP before March 2", borderColor: "border-l-teal", bg: "bg-teal/5" },
  { title: "Q1 Performance Review: Apr 1–5", sub: "Complete self-assessment by March 28", borderColor: "border-l-gold", bg: "bg-gold/5" },
  { title: "Holi Holiday: March 25–26", sub: "Office closed. Emergency line active for P1 issues", borderColor: "border-l-nd-blue", bg: "bg-nd-blue/5" },
];

const schedule = [
  { date: "Apr 1", event: "Sankalp Call Training — Live Batch", type: "Training", dept: "Sewa", status: "Upcoming", statusClass: "bg-nd-blue/10 text-nd-blue" },
  { date: "Apr 3", event: "Live Streaming Protocol Review", type: "SOP Update", dept: "Tech", status: "Pending Review", statusClass: "bg-gold/10 text-gold" },
  { date: "Apr 5", event: "Char Dham Season Briefing", type: "All-Hands", dept: "All Depts", status: "Confirmed", statusClass: "bg-nd-green/10 text-nd-green" },
  { date: "Apr 10", event: "Q1 LMS Score Review", type: "Assessment", dept: "All", status: "Scheduled", statusClass: "bg-secondary text-muted-foreground" },
];

const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const firstName = user?.name.split(" ")[0] || "User";

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-12">
      {/* Hero Section */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-saffron to-gold p-8 md:p-10 text-white shadow-lg"
      >
        <div className="relative z-10 max-w-2xl">
          <div className="text-white/80 text-sm font-medium mb-2 tracking-wide uppercase">Dashboard Overview</div>
          <h1 className="text-3xl md:text-4xl font-bold mb-3 tracking-tight">
            Welcome back, {firstName}! Elevate your skills today. 🚀
          </h1>
          <p className="text-white/90 text-[15px] md:text-base leading-relaxed mb-6">
            You are making great progress. Continue your learning journey or check out the latest SOPs to stay updated with NamanDarshan protocols.
          </p>
          <div className="flex gap-4">
            <button className="bg-white text-saffron px-6 py-2.5 rounded-full font-bold text-sm hover:shadow-md hover:scale-105 transition-all">
              Resume Learning
            </button>
            <button className="bg-black/20 backdrop-blur-md text-white px-6 py-2.5 rounded-full font-bold text-sm border border-white/30 hover:bg-black/30 transition-all">
              View Schedule
            </button>
          </div>
        </div>
        
        {/* Decorative elements */}
        <div className="absolute top-0 right-0 -translate-y-1/3 translate-x-1/3 w-96 h-96 bg-white/10 blur-3xl rounded-full pointer-events-none" />
        <div className="absolute bottom-0 right-1/4 translate-y-1/2 w-64 h-64 bg-black/5 blur-2xl rounded-full pointer-events-none" />
      </motion.div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
        {stats.map((s, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 + i * 0.05 }}
            className="premium-card-hover bg-white border border-border rounded-2xl p-5"
          >
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-xl mb-3 ${s.bg}`}>
              {s.icon}
            </div>
            <div className="text-[13px] text-muted-foreground font-medium mb-1 tracking-tight">{s.label}</div>
            <div className={`text-2xl font-bold leading-none mb-1 ${s.color}`}>{s.value}</div>
            <div className="text-[11px] text-muted-foreground">{s.sub}</div>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Continue Learning */}
        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.3 }}
          className="bg-white border border-border rounded-2xl p-6 shadow-sm"
        >
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-lg font-bold tracking-tight text-foreground flex items-center gap-2">
              <span className="text-xl">🎯</span> Continue Learning
            </h2>
            <button className="text-sm font-semibold text-primary hover:underline">View All</button>
          </div>
          
          <div className="space-y-4">
            {continueLearning.map((c, i) => (
              <div key={i} className="group p-3 rounded-xl hover:bg-secondary/50 border border-transparent hover:border-border transition-all flex items-center gap-4 cursor-pointer">
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center text-xl bg-secondary ${c.textColor} group-hover:scale-105 transition-transform`}>
                  {c.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-[14px] font-bold text-foreground truncate mb-1.5">{c.name}</div>
                  <div className="flex items-center gap-3">
                    <div className="flex-1 h-2 bg-secondary rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${c.color} transition-all duration-1000 ease-out`} style={{ width: `${c.progress}%` }} />
                    </div>
                    <div className={`w-10 text-right text-xs font-bold ${c.textColor}`}>{c.progress}%</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Recent Announcements */}
        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.4 }}
          className="bg-white border border-border rounded-2xl p-6 shadow-sm flex flex-col"
        >
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-lg font-bold tracking-tight text-foreground flex items-center gap-2">
              <span className="text-xl">📢</span> Recent Announcements
            </h2>
          </div>
          <div className="flex flex-col gap-3 flex-1">
            {announcements.map((a, i) => (
              <div key={i} className={`p-4 rounded-xl border-l-4 ${a.borderColor} ${a.bg} hover:-translate-y-0.5 transition-transform cursor-pointer`}>
                <div className="text-[14px] font-bold text-foreground mb-1">{a.title}</div>
                <div className="text-[12px] text-muted-foreground">{a.sub}</div>
              </div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Schedule */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="bg-white border border-border rounded-2xl p-6 shadow-sm overflow-hidden"
      >
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-bold tracking-tight text-foreground flex items-center gap-2">
            <span className="text-xl">📅</span> Upcoming Schedule
          </h2>
          <button className="text-sm font-semibold text-primary hover:underline">Full Calendar</button>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="text-[12px] font-bold text-muted-foreground uppercase tracking-wider border-b border-border">
                <th className="pb-3 pl-2">Date</th>
                <th className="pb-3">Event</th>
                <th className="pb-3 hidden md:table-cell">Type</th>
                <th className="pb-3 hidden sm:table-cell">Dept</th>
                <th className="pb-3 pr-2">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/50">
              {schedule.map((s, i) => (
                <tr key={i} className="hover:bg-secondary/30 transition-colors group">
                  <td className="py-3 pl-2 text-[14px] font-semibold text-foreground whitespace-nowrap">{s.date}</td>
                  <td className="py-3 text-[14px] font-medium text-foreground group-hover:text-primary transition-colors">{s.event}</td>
                  <td className="py-3 text-[13px] text-muted-foreground hidden md:table-cell">{s.type}</td>
                  <td className="py-3 text-[13px] text-muted-foreground hidden sm:table-cell">{s.dept}</td>
                  <td className="py-3 pr-2">
                    <span className={`text-[11px] px-2.5 py-1 rounded-full font-bold whitespace-nowrap ${s.statusClass}`}>
                      {s.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.div>
    </div>
  );
};

export default Dashboard;
