import React, { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { apiGet } from "@/lib/api";

interface SOPEntry {
  department: string;
  title: string;
  steps: string[];
  keywords?: string[];
  escalation?: string;
}

interface SOPPdf {
  department: string;
  title: string;
  href: string;
  filename: string;
}

interface SOPResponse {
  entries: SOPEntry[];
  pdfs: SOPPdf[];
}

const SOPLibrary: React.FC = () => {
  const { user } = useAuth();
  const [activeDept, setActiveDept] = useState(user?.department || "Sales");
  const [entries, setEntries] = useState<SOPEntry[]>([]);
  const [pdfs, setPdfs] = useState<SOPPdf[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user?.department) {
      setActiveDept(user.department);
    }
  }, [user?.department]);

  useEffect(() => {
    const fetchSops = async () => {
      setLoading(true);
      try {
        const data = await apiGet<SOPResponse>("/api/sops");
        setEntries(Array.isArray(data?.entries) ? data.entries : []);
        setPdfs(Array.isArray(data?.pdfs) ? data.pdfs : []);
      } catch (error) {
        console.error("SOP load failed:", error);
      } finally {
        setLoading(false);
      }
    };

    void fetchSops();
  }, []);

  const departments = useMemo(
    () => Array.from(new Set([...entries.map((entry) => entry.department), ...pdfs.map((pdf) => pdf.department)])).sort(),
    [entries, pdfs],
  );

  const activeEntries = entries.filter((entry) => entry.department === activeDept);
  const activePdfs = pdfs.filter((pdf) => pdf.department === activeDept);

  return (
    <div>
      <div className="mb-5">
        <div className="text-[11px] text-muted-foreground mb-2">
          Home <span className="text-saffron">/ SOP Library</span>
        </div>
        <h1 className="text-xl font-bold mb-1">SOP Library</h1>
        <p className="text-[13px] text-muted-foreground">
          Original SOP PDFs and structured operational steps from the backend knowledge base
        </p>
      </div>

      <div className="flex flex-wrap gap-1.5 mb-5">
        {departments.map((department) => (
          <button
            key={department}
            onClick={() => setActiveDept(department)}
            className={`px-3.5 py-[7px] text-xs border-[1.5px] rounded-full font-medium transition-all ${
              activeDept === department
                ? "bg-saffron text-primary-foreground border-saffron"
                : "bg-card text-muted-foreground border-border hover:border-saffron hover:text-saffron"
            }`}
          >
            {department}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="bg-card border border-border rounded-xl px-4 py-6 text-sm text-muted-foreground">
          Loading SOPs...
        </div>
      ) : (
        <div className="flex flex-col gap-2.5">
          {activePdfs.map((pdf) => (
            <div key={pdf.filename} className="bg-card border border-border rounded-xl overflow-hidden">
              <div className="w-full px-4 py-3 bg-secondary flex items-center gap-2.5 text-left">
                <div className="w-6 h-6 rounded-full bg-saffron-light flex items-center justify-center text-[10px] font-semibold text-saffron">
                  PDF
                </div>
                <div className="text-sm font-semibold flex-1">{pdf.title}</div>
                <span className="text-[11px] text-saffron px-2 py-0.5 rounded-full bg-saffron-light">{pdf.department}</span>
              </div>
              <div className="px-4 py-3.5 flex justify-end">
                <a
                  href={pdf.href}
                  target="_blank"
                  rel="noreferrer"
                  className="px-3 py-1.5 rounded-lg bg-saffron text-primary-foreground text-xs font-semibold hover:opacity-90 transition-opacity"
                >
                  Open Original PDF
                </a>
              </div>
            </div>
          ))}

          {activeEntries.map((entry, index) => (
            <SOPCard key={`${entry.department}-${entry.title}`} sop={entry} index={index} />
          ))}

          {activeEntries.length === 0 && activePdfs.length === 0 && (
            <div className="bg-card border border-dashed border-border rounded-xl px-4 py-6 text-sm text-muted-foreground">
              No SOPs or PDFs added for {activeDept} yet.
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const SOPCard: React.FC<{ sop: SOPEntry; index: number }> = ({ sop, index }) => {
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
        <span className="text-[11px] text-saffron px-2 py-0.5 rounded-full bg-saffron-light">{sop.department}</span>
        <span className="text-[11px] text-muted-foreground">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="px-4 py-3.5">
          {sop.steps.map((step, stepIndex) => (
            <div key={stepIndex} className="flex gap-2 py-1.5 border-b border-border last:border-b-0">
              <div className="w-5 h-5 rounded-full border-[1.5px] border-border flex items-center justify-center text-[10px] text-muted-foreground flex-shrink-0 mt-0.5">
                {stepIndex + 1}
              </div>
              <div className="text-xs text-muted-foreground leading-relaxed">{step}</div>
            </div>
          ))}
          {sop.escalation && (
            <div className="mt-3 rounded-lg bg-saffron/10 border border-saffron/20 px-3 py-2 text-[12px] text-muted-foreground">
              <span className="font-semibold text-foreground">Escalation:</span> {sop.escalation}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SOPLibrary;
