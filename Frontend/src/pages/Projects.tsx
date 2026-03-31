import React from "react";
import { KANBAN_DATA } from "@/data/mockData";

const colColors: Record<string, string> = {
  Backlog: "text-muted-foreground",
  "In Progress": "text-saffron",
  Review: "text-nd-blue",
  Done: "text-nd-green",
};

const Projects: React.FC = () => {
  return (
    <div>
      <div className="mb-5">
        <div className="text-[11px] text-muted-foreground mb-2">Home <span className="text-saffron">/ Projects</span></div>
        <h1 className="text-xl font-bold mb-1">Project Board</h1>
        <p className="text-[13px] text-muted-foreground">Active projects across NamanDarshan departments</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {Object.entries(KANBAN_DATA).map(([col, cards]) => (
          <div key={col} className="bg-secondary rounded-xl p-3">
            <div className={`text-xs font-semibold mb-2.5 flex items-center justify-between ${colColors[col]}`}>
              {col}
              <span className="text-[11px] px-[7px] py-0.5 rounded-full bg-border text-muted-foreground">{cards.length}</span>
            </div>
            <div className="flex flex-col gap-2">
              {cards.map((c, i) => (
                <div key={i} className="bg-card border border-border rounded-lg p-2.5 cursor-pointer hover:shadow-soft transition-shadow">
                  <div className="text-xs font-medium mb-1.5 leading-snug">{c.title}</div>
                  <div className="text-[10px] text-muted-foreground mb-1.5">{c.dept}</div>
                  <div className="flex items-center gap-1.5">
                    <div className="w-5 h-5 rounded-full bg-saffron-light flex items-center justify-center text-[9px] font-bold text-saffron">{c.who}</div>
                    <div className="text-[10px] text-muted-foreground ml-auto">Due: {c.due}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Projects;
