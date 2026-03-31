import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { COURSES, DEPARTMENTS } from "@/data/mockData";
import { useAuth } from "@/contexts/AuthContext";

const allDepts = ["All", ...DEPARTMENTS];

const Courses: React.FC = () => {
  const { user } = useAuth();
  const [activeDept, setActiveDept] = useState(user?.department || "All");

  useEffect(() => {
    if (user?.department && allDepts.includes(user.department)) {
      setActiveDept(user.department);
    }
  }, [user]);

  const filtered = activeDept === "All" ? COURSES : COURSES.filter(c => c.dept === activeDept);

  const statusColor = (status: string) => {
    switch (status) {
      case "Completed": return "bg-nd-green-light text-nd-green";
      case "In Progress": return "bg-gold-light text-gold";
      case "Started": return "bg-nd-blue-light text-nd-blue";
      default: return "bg-surface3 text-muted-foreground";
    }
  };

  return (
    <div>
      <div className="mb-5">
        <div className="text-[11px] text-muted-foreground mb-2">Home <span className="text-saffron">/ Courses</span></div>
        <h1 className="text-xl font-bold mb-1">Course Library</h1>
        <p className="text-[13px] text-muted-foreground">All department-specific courses sourced from NamanDarshan operations</p>
      </div>

      <div className="flex flex-wrap gap-1.5 mb-5">
        {allDepts.map(d => (
          <button
            key={d}
            onClick={() => setActiveDept(d)}
            className={`px-3.5 py-[7px] text-xs border-[1.5px] rounded-full font-medium transition-all ${activeDept === d
                ? "bg-saffron text-primary-foreground border-saffron"
                : "bg-card text-muted-foreground border-border hover:border-saffron hover:text-saffron"
              }`}
          >
            {d === "All" ? "🛕 All Depts" : d}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3.5">
        {filtered.map((c, i) => (
          <motion.div
            key={c.id}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.04 }}
            className="bg-card border border-border rounded-xl overflow-hidden cursor-pointer hover:shadow-elevated transition-shadow"
          >
            <div className="h-20 flex items-center justify-center text-[32px]" style={{ background: c.bg }}>
              {c.icon}
            </div>
            <div className="p-3.5">
              <div className="text-[13px] font-semibold mb-1 leading-snug">{c.title}</div>
              <div className="text-[11px] text-muted-foreground mb-2">{c.dept} Dept · {c.dur}</div>
              <div className="flex items-center gap-2.5 text-[11px] text-muted-foreground">
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${statusColor(c.status)}`}>{c.status}</span>
                <span>{c.level}</span>
              </div>
              <div className="h-[3px] bg-border rounded-full mt-2 overflow-hidden">
                <div className="h-full bg-saffron rounded-full transition-all" style={{ width: `${c.progress}%` }} />
              </div>
            </div>
          </motion.div>
        ))}
        {filtered.length === 0 && (
          <div className="col-span-full text-muted-foreground text-[13px] p-5">No courses in this department yet.</div>
        )}
      </div>
    </div>
  );
};

export default Courses;
