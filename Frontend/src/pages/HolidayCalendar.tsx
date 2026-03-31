import React from "react";
import { HOLIDAYS } from "@/data/mockData";

const HolidayCalendar: React.FC = () => {
  const holidays = [6, 14];
  const today = 30;
  const firstDay = 2; // Apr 1 2025 = Tuesday
  const totalDays = 30;
  const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  const typeClass = (type: string) => {
    switch (type) {
      case "Festival": return "bg-gold-light text-gold";
      case "National": return "bg-nd-blue-light text-nd-blue";
      case "Optional": return "bg-nd-green-light text-nd-green";
      default: return "bg-surface3 text-muted-foreground";
    }
  };

  return (
    <div>
      <div className="mb-5">
        <div className="text-[11px] text-muted-foreground mb-2">Home <span className="text-saffron">/ Holiday Calendar</span></div>
        <h1 className="text-xl font-bold mb-1">Holiday Calendar 2025</h1>
        <p className="text-[13px] text-muted-foreground">Official NamanDarshan holiday list and Hindu festival schedule</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3.5">
        <div className="bg-card border border-border rounded-xl p-[18px]">
          <div className="text-sm font-semibold mb-3.5">📅 April 2025</div>
          <div className="grid grid-cols-7 gap-1 mb-4">
            {days.map(d => (
              <div key={d} className="text-[10px] font-semibold text-muted-foreground text-center py-1.5">{d}</div>
            ))}
            {Array.from({ length: firstDay }).map((_, i) => (
              <div key={`e${i}`} className="aspect-square" />
            ))}
            {Array.from({ length: totalDays }).map((_, i) => {
              const d = i + 1;
              const dow = (d + firstDay - 1) % 7;
              const isToday = d === today;
              const isHoliday = holidays.includes(d);
              const isWeekend = dow === 0 || dow === 6;
              return (
                <div
                  key={d}
                  className={`aspect-square flex items-center justify-center text-xs rounded-lg ${
                    isToday ? "bg-saffron text-primary-foreground font-semibold" :
                    isHoliday ? "bg-maroon-light text-maroon font-medium" :
                    isWeekend ? "text-muted-foreground" : ""
                  }`}
                >
                  {d}
                </div>
              );
            })}
          </div>
          <div className="flex gap-3 text-[11px]">
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-saffron" /> Today</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-maroon-light border border-maroon" /> Holiday</span>
          </div>
        </div>

        <div className="bg-card border border-border rounded-xl p-[18px]">
          <div className="text-sm font-semibold mb-3.5">🎉 Holiday List 2025</div>
          <table className="w-full text-[13px]">
            <thead>
              <tr className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide">
                <th className="text-left p-2.5 bg-secondary rounded-l-md">Date</th>
                <th className="text-left p-2.5 bg-secondary">Holiday</th>
                <th className="text-left p-2.5 bg-secondary rounded-r-md">Type</th>
              </tr>
            </thead>
            <tbody>
              {HOLIDAYS.map((h, i) => (
                <tr key={i} className="border-b border-border last:border-b-0">
                  <td className="p-2.5">{h.date}</td>
                  <td className="p-2.5">{h.name}</td>
                  <td className="p-2.5"><span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${typeClass(h.type)}`}>{h.type}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default HolidayCalendar;
