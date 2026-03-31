import React, { useState } from "react";
import { SOPS, DEPARTMENTS } from "@/data/mockData";

const SOPLibrary: React.FC = () => {
  const [activeDept, setActiveDept] = useState("Sales");
  const sopDepts = Object.keys(SOPS);

  return (
    <div>
      <div className="mb-5">
        <div className="text-[11px] text-muted-foreground mb-2">Home <span className="text-saffron">/ SOP Library</span></div>
        <h1 className="text-xl font-bold mb-1">SOP Library</h1>
        <p className="text-[13px] text-muted-foreground">All Standard Operating Procedures for NamanDarshan departments</p>
      </div>

      <div className="flex flex-wrap gap-1.5 mb-5">
        {sopDepts.map(d => (
          <button
            key={d}
            onClick={() => setActiveDept(d)}
            className={`px-3.5 py-[7px] text-xs border-[1.5px] rounded-full font-medium transition-all ${
              activeDept === d
                ? "bg-saffron text-primary-foreground border-saffron"
                : "bg-card text-muted-foreground border-border hover:border-saffron hover:text-saffron"
            }`}
          >
            {d}
          </button>
        ))}
      </div>

      <div className="flex flex-col gap-2.5">
        {(SOPS[activeDept] || []).map((sop, i) => (
          <SOPCard key={`${activeDept}-${i}`} sop={sop} index={i} dept={activeDept} />
        ))}
      </div>
    </div>
  );
};

const SOPCard: React.FC<{ sop: { title: string; steps: string[] }; index: number; dept: string }> = ({ sop, index, dept }) => {
  const [open, setOpen] = useState(false);

  return (
    <div className="bg-card border border-border rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full px-4 py-3 bg-secondary flex items-center gap-2.5 text-left hover:bg-saffron-light/50 transition-colors"
      >
        <div className="w-6 h-6 rounded-full bg-saffron-light flex items-center justify-center text-xs font-semibold text-saffron">
          {index + 1}
        </div>
        <div className="text-sm font-semibold flex-1">{sop.title}</div>
        <span className="text-[11px] text-saffron px-2 py-0.5 rounded-full bg-saffron-light">{dept}</span>
        <span className="text-[11px] text-muted-foreground">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="px-4 py-3.5">
          {sop.steps.map((step, j) => (
            <div key={j} className="flex gap-2 py-1.5 border-b border-border last:border-b-0">
              <div className="w-5 h-5 rounded-full border-[1.5px] border-border flex items-center justify-center text-[10px] text-muted-foreground flex-shrink-0 mt-0.5">
                {j + 1}
              </div>
              <div className="text-xs text-muted-foreground leading-relaxed">{step}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SOPLibrary;
