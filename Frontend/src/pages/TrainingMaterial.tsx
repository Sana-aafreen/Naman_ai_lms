import React from "react";

const videoGuides = [
  { title: "VIP Darshan Escort Walkthrough", meta: "14 min · Ops Dept" },
  { title: "Live Puja Streaming Setup", meta: "22 min · Puja Dept" },
  { title: "WhatsApp CRM for Sales Team", meta: "18 min · Sales Dept" },
  { title: "Shraddha Box Packing Standards", meta: "11 min · Logistics" },
];

const documents = [
  { title: "Complete SOP Handbook v2.1", meta: "PDF · All Depts · Updated Mar 2025" },
  { title: "Puja Sankalp Form Guide", meta: "PDF · Sewa & Puja · 8 pages" },
  { title: "Char Dham Temple Entry Matrix", meta: "PDF · Ops · 12 pages" },
  { title: "GST & Compliance Guide FY25", meta: "PDF · Finance · 20 pages" },
];

const webResources = [
  { title: "Kedarnath Temple Page", meta: "namandarshan.com/kedarnath" },
  { title: "Puja Booking Flow", meta: "namandarshan.com/book-puja" },
  { title: "Live Darshan Schedule", meta: "namandarshan.com/live-darshan" },
  { title: "About NamanDarshan", meta: "namandarshan.com/about" },
];

const TrainingMaterial: React.FC = () => {
  return (
    <div>
      <div className="mb-5">
        <div className="text-[11px] text-muted-foreground mb-2">Home <span className="text-saffron">/ Training Material</span></div>
        <h1 className="text-xl font-bold mb-1">Training Resources</h1>
        <p className="text-[13px] text-muted-foreground">Guides, videos, and reference documents — all from namandarshan.com</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3.5">
        <div className="bg-card border border-border rounded-xl overflow-hidden">
          <div className="h-[3px] bg-saffron" />
          <div className="p-[18px]">
            <div className="text-sm font-semibold mb-3.5">📹 Video Guides</div>
            <div className="flex flex-col gap-2">
              {videoGuides.map((v, i) => (
                <div key={i} className="flex items-center gap-2.5 p-2 bg-secondary rounded-lg cursor-pointer hover:bg-saffron-light transition-colors">
                  <span className="text-[22px]">🎬</span>
                  <div>
                    <div className="text-xs font-medium">{v.title}</div>
                    <div className="text-[11px] text-muted-foreground">{v.meta}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="bg-card border border-border rounded-xl overflow-hidden">
          <div className="h-[3px] bg-teal" />
          <div className="p-[18px]">
            <div className="text-sm font-semibold mb-3.5">📄 SOPs & Documents</div>
            <div className="flex flex-col gap-2">
              {documents.map((d, i) => (
                <div key={i} className="flex items-center gap-2.5 p-2 bg-secondary rounded-lg cursor-pointer hover:bg-teal-light transition-colors">
                  <span className="text-[22px]">📋</span>
                  <div>
                    <div className="text-xs font-medium">{d.title}</div>
                    <div className="text-[11px] text-muted-foreground">{d.meta}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="bg-card border border-border rounded-xl overflow-hidden">
          <div className="h-[3px] bg-nd-blue" />
          <div className="p-[18px]">
            <div className="text-sm font-semibold mb-3.5">🔗 From NamanDarshan.com</div>
            <div className="flex flex-col gap-2">
              {webResources.map((w, i) => (
                <div key={i} className="flex items-center gap-2.5 p-2 bg-secondary rounded-lg cursor-pointer hover:bg-nd-blue-light transition-colors">
                  <span className="text-[22px]">🌐</span>
                  <div>
                    <div className="text-xs font-medium">{w.title}</div>
                    <div className="text-[11px] text-muted-foreground">{w.meta}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TrainingMaterial;
