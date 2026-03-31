import React from "react";

const coverage = [
  { label: "Hospitalization", amount: "₹3,00,000", color: "text-nd-green" },
  { label: "Day Care Procedures", amount: "₹50,000", color: "text-nd-green" },
  { label: "OPD (Outpatient)", amount: "₹10,000", color: "text-nd-blue" },
  { label: "Dental (Basic)", amount: "₹5,000", color: "text-nd-blue" },
  { label: "Maternity Benefit", amount: "₹30,000", color: "text-saffron" },
];

const claims = [
  { date: "Jan 10", type: "OPD Consultation", amount: "₹800", status: "Reimbursed", statusClass: "bg-nd-green-light text-nd-green" },
  { date: "Feb 5", type: "Lab Tests", amount: "₹2,200", status: "Reimbursed", statusClass: "bg-nd-green-light text-nd-green" },
  { date: "Mar 18", type: "Hospitalization", amount: "₹18,500", status: "Under Review", statusClass: "bg-gold-light text-gold" },
];

const wellness = [
  { icon: "🧘", title: "Meditation & Mindfulness", sub: "5 guided sessions available", bg: "bg-saffron-light" },
  { icon: "🍱", title: "Nutrition Guidance", sub: "Sattvic diet resources", bg: "bg-teal-light" },
  { icon: "📞", title: "Employee Helpline", sub: "1800-XXX-XXXX · 24×7", bg: "bg-nd-blue-light" },
];

const Medical: React.FC = () => {
  return (
    <div>
      <div className="mb-5">
        <div className="text-[11px] text-muted-foreground mb-2">Home <span className="text-saffron">/ Medical & Insurance</span></div>
        <h1 className="text-xl font-bold mb-1">Medical Assistance & Insurance</h1>
        <p className="text-[13px] text-muted-foreground">Your health coverage details, claim status and wellness resources</p>
      </div>

      {/* Insurance Card */}
      <div className="bg-gradient-to-br from-deep to-deep-3 text-primary-foreground rounded-xl p-5 mb-4">
        <div className="flex items-center gap-3.5 mb-4">
          <div className="w-11 h-11 rounded-xl bg-primary-foreground/10 flex items-center justify-center text-[22px]">🏥</div>
          <div>
            <div className="text-base font-bold">NamanDarshan Group Health Policy</div>
            <div className="text-xs opacity-60">Policy No: NDH-2025-03847 · United India Insurance</div>
          </div>
        </div>
        <div className="grid grid-cols-3 sm:grid-cols-6 gap-3">
          {[
            { label: "Insured", value: "Priya Sharma" },
            { label: "Sum Assured", value: "₹3,00,000" },
            { label: "Valid Till", value: "Mar 31, 2026" },
            { label: "Cashless", value: "1,200+ Network" },
            { label: "Coverage", value: "Individual + Family" },
            { label: "Dependents", value: "Spouse + 2 Children" },
          ].map((item, i) => (
            <div key={i}>
              <div className="text-[10px] uppercase opacity-50 tracking-wide mb-0.5">{item.label}</div>
              <div className="text-sm font-medium">{item.value}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3.5 mb-3.5">
        <div className="bg-card border border-border rounded-xl p-[18px]">
          <div className="text-sm font-semibold mb-3.5">💊 Coverage Details</div>
          <div className="flex flex-col gap-2">
            {coverage.map((c, i) => (
              <div key={i} className={`flex justify-between p-2 rounded-lg ${i === coverage.length - 1 ? 'bg-saffron-light' : 'bg-secondary'}`}>
                <span className="text-[13px]">{c.label}</span>
                <span className={`text-[13px] font-semibold ${c.color}`}>{c.amount}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-card border border-border rounded-xl p-[18px]">
          <div className="text-sm font-semibold mb-3.5">📋 Claim Status</div>
          <table className="w-full text-[13px]">
            <thead>
              <tr className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide">
                <th className="text-left p-2 bg-secondary rounded-l-md">Date</th>
                <th className="text-left p-2 bg-secondary">Type</th>
                <th className="text-left p-2 bg-secondary">Amount</th>
                <th className="text-left p-2 bg-secondary rounded-r-md">Status</th>
              </tr>
            </thead>
            <tbody>
              {claims.map((c, i) => (
                <tr key={i} className="border-b border-border last:border-b-0">
                  <td className="p-2">{c.date}</td>
                  <td className="p-2">{c.type}</td>
                  <td className="p-2">{c.amount}</td>
                  <td className="p-2"><span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${c.statusClass}`}>{c.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="mt-3.5 p-3 bg-teal-light rounded-lg text-xs text-teal">
            💬 <strong>AI Assist:</strong> Use the AI Assistant and type "Help me file an insurance claim" for step-by-step guidance.
          </div>
        </div>
      </div>

      <div className="bg-card border border-border rounded-xl p-[18px]">
        <div className="text-sm font-semibold mb-3.5">🌿 Wellness Resources</div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {wellness.map((w, i) => (
            <div key={i} className={`p-3.5 ${w.bg} rounded-xl text-center cursor-pointer hover:opacity-80 transition-opacity`}>
              <div className="text-[28px]">{w.icon}</div>
              <div className="text-[13px] font-semibold mt-2">{w.title}</div>
              <div className="text-[11px] text-muted-foreground mt-1">{w.sub}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Medical;
