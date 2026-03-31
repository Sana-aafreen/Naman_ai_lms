import React, { useState } from "react";

const employees = [
  { name: "Priya Sharma", dept: "Sewa", role: "Executive", score: "87%", courses: "5/8", status: "Active" },
  { name: "Rahul Verma", dept: "Sales & CRM", role: "Sr. Executive", score: "79%", courses: "6/9", status: "Active" },
  { name: "Anita Mishra", dept: "Ops", role: "Coordinator", score: "82%", courses: "7/10", status: "Active" },
  { name: "Vikas Pandey", dept: "Puja & Pandit", role: "Pandit Lead", score: "91%", courses: "8/8", status: "Active" },
  { name: "Sunita Rao", dept: "Logistics", role: "Executive", score: "68%", courses: "4/7", status: "On Leave" },
  { name: "Dev Chauhan", dept: "Tech & Stream", role: "Developer", score: "76%", courses: "5/8", status: "Active" },
  { name: "Meera Iyer", dept: "Content & SEO", role: "Writer", score: "85%", courses: "6/7", status: "Active" },
  { name: "Ajay Gupta", dept: "Finance", role: "Accountant", score: "72%", courses: "4/6", status: "Active" },
];

const deptProgress = [
  { dept: "Sewa", score: 84, enrolled: 12, completed: 8 },
  { dept: "Sales & CRM", score: 76, enrolled: 15, completed: 9 },
  { dept: "Ops", score: 80, enrolled: 18, completed: 12 },
  { dept: "Puja & Pandit", score: 91, enrolled: 8, completed: 8 },
  { dept: "Logistics", score: 65, enrolled: 10, completed: 5 },
  { dept: "Tech & Stream", score: 74, enrolled: 12, completed: 7 },
  { dept: "Content & SEO", score: 82, enrolled: 9, completed: 6 },
  { dept: "Finance", score: 70, enrolled: 8, completed: 4 },
];

const leaveApprovals = [
  { name: "Sunita Rao", dept: "Logistics", dates: "Apr 10–12", type: "Casual", days: 3, status: "Pending" },
  { name: "Rahul Verma", dept: "Sales", dates: "Apr 18", type: "Sick", days: 1, status: "Pending" },
  { name: "Dev Chauhan", dept: "Tech", dates: "Apr 20–21", type: "Earned", days: 2, status: "Pending" },
];

const tabs = ["Employees", "Dept Progress", "Leave Approvals", "LMS Analytics"];

const AdminDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState("Employees");

  return (
    <div>
      <div className="mb-5">
        <div className="text-[11px] text-muted-foreground mb-2">Home <span className="text-saffron">/ Admin</span></div>
        <h1 className="text-xl font-bold mb-1">Admin Dashboard</h1>
        <p className="text-[13px] text-muted-foreground">Organization-wide overview — Manager and Admin only</p>
      </div>

      <div className="flex gap-0.5 bg-secondary rounded-lg p-[3px] w-fit mb-5">
        {tabs.map(t => (
          <button
            key={t}
            onClick={() => setActiveTab(t)}
            className={`px-4 py-[7px] text-xs rounded-[7px] font-medium transition-all ${
              activeTab === t ? "bg-card shadow-sm" : "text-muted-foreground"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {activeTab === "Employees" && (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
            <div className="bg-card border border-border rounded-xl p-4"><div className="text-xl mb-2">👥</div><div className="text-[11px] text-muted-foreground mb-1">Total Employees</div><div className="text-[26px] font-bold text-saffron">42</div></div>
            <div className="bg-card border border-border rounded-xl p-4"><div className="text-xl mb-2">✅</div><div className="text-[11px] text-muted-foreground mb-1">Active Today</div><div className="text-[26px] font-bold text-nd-green">38</div></div>
            <div className="bg-card border border-border rounded-xl p-4"><div className="text-xl mb-2">📅</div><div className="text-[11px] text-muted-foreground mb-1">On Leave</div><div className="text-[26px] font-bold text-gold">4</div></div>
            <div className="bg-card border border-border rounded-xl p-4"><div className="text-xl mb-2">🎓</div><div className="text-[11px] text-muted-foreground mb-1">Avg LMS Score</div><div className="text-[26px] font-bold text-nd-blue">74%</div></div>
          </div>
          <div className="bg-card border border-border rounded-xl p-[18px]">
            <div className="text-sm font-semibold mb-3.5">👤 All Employees</div>
            <table className="w-full text-[13px]">
              <thead>
                <tr className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide">
                  <th className="text-left p-2.5 bg-secondary rounded-l-md">Name</th>
                  <th className="text-left p-2.5 bg-secondary">Department</th>
                  <th className="text-left p-2.5 bg-secondary">Role</th>
                  <th className="text-left p-2.5 bg-secondary">LMS Score</th>
                  <th className="text-left p-2.5 bg-secondary">Courses</th>
                  <th className="text-left p-2.5 bg-secondary rounded-r-md">Status</th>
                </tr>
              </thead>
              <tbody>
                {employees.map((e, i) => (
                  <tr key={i} className="border-b border-border last:border-b-0 hover:bg-secondary/50">
                    <td className="p-2.5 font-medium">{e.name}</td>
                    <td className="p-2.5">{e.dept}</td>
                    <td className="p-2.5">{e.role}</td>
                    <td className="p-2.5">{e.score}</td>
                    <td className="p-2.5">{e.courses}</td>
                    <td className="p-2.5">
                      <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${e.status === "Active" ? "bg-nd-green-light text-nd-green" : "bg-gold-light text-gold"}`}>
                        {e.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {activeTab === "Dept Progress" && (
        <div className="bg-card border border-border rounded-xl p-[18px]">
          <div className="text-sm font-semibold mb-3.5">📊 Department-wise Progress</div>
          {deptProgress.map((d, i) => (
            <div key={i} className="flex items-center gap-3 py-2.5 border-b border-border last:border-b-0">
              <div className="w-36 flex-shrink-0 text-[13px] font-medium">{d.dept}</div>
              <div className="flex-1 h-2 bg-border rounded-full overflow-hidden">
                <div className="h-full bg-saffron rounded-full" style={{ width: `${d.score}%` }} />
              </div>
              <div className="w-10 text-right text-xs font-semibold text-saffron">{d.score}%</div>
              <div className="w-24 text-right text-[11px] text-muted-foreground">{d.completed}/{d.enrolled} done</div>
            </div>
          ))}
        </div>
      )}

      {activeTab === "Leave Approvals" && (
        <div className="bg-card border border-border rounded-xl p-[18px]">
          <div className="text-sm font-semibold mb-3.5">📋 Pending Approvals</div>
          <table className="w-full text-[13px]">
            <thead>
              <tr className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide">
                <th className="text-left p-2.5 bg-secondary rounded-l-md">Name</th>
                <th className="text-left p-2.5 bg-secondary">Dept</th>
                <th className="text-left p-2.5 bg-secondary">Dates</th>
                <th className="text-left p-2.5 bg-secondary">Type</th>
                <th className="text-left p-2.5 bg-secondary">Days</th>
                <th className="text-left p-2.5 bg-secondary rounded-r-md">Actions</th>
              </tr>
            </thead>
            <tbody>
              {leaveApprovals.map((l, i) => (
                <tr key={i} className="border-b border-border last:border-b-0">
                  <td className="p-2.5 font-medium">{l.name}</td>
                  <td className="p-2.5">{l.dept}</td>
                  <td className="p-2.5">{l.dates}</td>
                  <td className="p-2.5">{l.type}</td>
                  <td className="p-2.5">{l.days}</td>
                  <td className="p-2.5 flex gap-1.5">
                    <button className="px-2.5 py-1 bg-nd-green text-primary-foreground rounded text-[11px] font-medium hover:opacity-90">Approve</button>
                    <button className="px-2.5 py-1 bg-maroon text-primary-foreground rounded text-[11px] font-medium hover:opacity-90">Reject</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === "LMS Analytics" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3.5">
          <div className="bg-card border border-border rounded-xl p-[18px]">
            <div className="text-sm font-semibold mb-3.5">📈 Monthly Active Learners</div>
            <div className="flex items-end gap-2 h-40">
              {[28, 32, 35, 38, 42, 40, 36, 41, 38, 35, 42, 45].map((v, i) => (
                <div key={i} className="flex-1 flex flex-col items-center gap-1">
                  <div className="w-full bg-saffron/80 rounded-t-sm" style={{ height: `${(v / 45) * 100}%` }} />
                  <span className="text-[9px] text-muted-foreground">{["J","F","M","A","M","J","J","A","S","O","N","D"][i]}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="bg-card border border-border rounded-xl p-[18px]">
            <div className="text-sm font-semibold mb-3.5">🎯 Course Completion Rate</div>
            <div className="flex flex-col gap-2">
              {[
                { label: "Mandatory Courses", pct: 78, color: "bg-saffron" },
                { label: "Optional Courses", pct: 45, color: "bg-nd-blue" },
                { label: "New Joinee Onboarding", pct: 92, color: "bg-nd-green" },
                { label: "Quarterly Assessments", pct: 65, color: "bg-gold" },
              ].map((c, i) => (
                <div key={i} className="flex items-center gap-3">
                  <div className="w-44 text-[13px]">{c.label}</div>
                  <div className="flex-1 h-2 bg-border rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${c.color}`} style={{ width: `${c.pct}%` }} />
                  </div>
                  <div className="w-10 text-right text-xs font-semibold">{c.pct}%</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminDashboard;
