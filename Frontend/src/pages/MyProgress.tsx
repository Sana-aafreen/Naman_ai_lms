import React from "react";

const MyProgress: React.FC = () => {
  const skills = [
    { name: "Customer Communication", score: 87, color: "bg-saffron" },
    { name: "Temple Protocols", score: 72, color: "bg-gold" },
    { name: "CRM Operations", score: 45, color: "bg-nd-blue" },
    { name: "SOP Compliance", score: 90, color: "bg-nd-green" },
    { name: "Crisis Management", score: 68, color: "bg-teal" },
    { name: "Team Collaboration", score: 82, color: "bg-saffron-mid" },
  ];

  const badges = [
    { icon: "🏆", title: "SOP Master", desc: "Completed all Sewa SOPs" },
    { icon: "⭐", title: "Fast Learner", desc: "5 courses completed in Q1" },
    { icon: "🎯", title: "Streak King", desc: "14-day learning streak" },
    { icon: "🤝", title: "Team Player", desc: "Helped 8 colleagues this month" },
  ];

  return (
    <div>
      <div className="mb-5">
        <div className="text-[11px] text-muted-foreground mb-2">Home <span className="text-saffron">/ My Progress</span></div>
        <h1 className="text-xl font-bold mb-1">My Progress</h1>
        <p className="text-[13px] text-muted-foreground">Track your learning journey, skills, and achievements</p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
        {[
          { label: "Overall Score", value: "87%", color: "text-saffron" },
          { label: "Courses Done", value: "5/8", color: "text-nd-green" },
          { label: "Learning Hours", value: "42h", color: "text-nd-blue" },
          { label: "Dept Rank", value: "#3", color: "text-gold" },
        ].map((s, i) => (
          <div key={i} className="bg-card border border-border rounded-xl p-4">
            <div className="text-[11px] text-muted-foreground font-medium mb-1.5">{s.label}</div>
            <div className={`text-[26px] font-bold leading-none ${s.color}`}>{s.value}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3.5 mb-3.5">
        <div className="bg-card border border-border rounded-xl p-[18px]">
          <div className="text-sm font-semibold mb-3.5 flex items-center gap-2">📊 Skill Assessment</div>
          {skills.map((s, i) => (
            <div key={i} className="flex items-center gap-3 py-2.5 border-b border-border last:border-b-0">
              <div className="w-40 flex-shrink-0 text-[13px]">{s.name}</div>
              <div className="flex-1 h-1.5 bg-border rounded-full overflow-hidden">
                <div className={`h-full rounded-full ${s.color}`} style={{ width: `${s.score}%` }} />
              </div>
              <div className="w-9 text-right text-xs font-semibold">{s.score}%</div>
            </div>
          ))}
        </div>

        <div className="bg-card border border-border rounded-xl p-[18px]">
          <div className="text-sm font-semibold mb-3.5 flex items-center gap-2">🏅 Badges & Achievements</div>
          <div className="grid grid-cols-2 gap-2.5">
            {badges.map((b, i) => (
              <div key={i} className="p-3 bg-saffron-light rounded-xl text-center">
                <div className="text-[28px]">{b.icon}</div>
                <div className="text-xs font-semibold mt-1.5">{b.title}</div>
                <div className="text-[10px] text-muted-foreground mt-0.5">{b.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default MyProgress;
