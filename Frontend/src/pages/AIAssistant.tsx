import React, { useState, useRef, useEffect } from "react";
import { AI_RESPONSES } from "@/data/mockData";

interface Message {
  text: string;
  type: "bot" | "user";
  time: string;
}

const quickPrompts = [
  "What's the VIP Darshan SOP?",
  "How do I file an insurance claim?",
  "Recommend courses for me",
  "Char Dham season dates 2025",
];

const aiCapabilities = [
  { icon: "📋", title: "SOPs & Protocols", sub: "Step-by-step guidance for any procedure" },
  { icon: "📚", title: "Course Recommendations", sub: "Personalized by your role and gaps" },
  { icon: "🛕", title: "Temple & Ritual Knowledge", sub: "Timings, dress codes, entry rules" },
  { icon: "📅", title: "HR & Leave Policies", sub: "Leave balance, policies, claims" },
];

const AIAssistant: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    { text: "Jai Shri Ram 🙏 I'm Naman AI — your learning assistant. I can help with SOPs, course recommendations, temple protocols, HR policies, and more. What would you like to know today?", type: "bot", time: "Just now" },
  ]);
  const [input, setInput] = useState("");
  const messagesRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (messagesRef.current) {
      messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
    }
  }, [messages]);

  const sendMessage = (text: string) => {
    if (!text.trim()) return;
    const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    setMessages(prev => [...prev, { text, type: "user", time: now }]);
    setInput("");

    setTimeout(() => {
      const lower = text.toLowerCase();
      let response = AI_RESPONSES.default;
      for (const key of Object.keys(AI_RESPONSES)) {
        if (key !== "default" && lower.includes(key)) {
          response = AI_RESPONSES[key];
          break;
        }
      }
      const botTime = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      setMessages(prev => [...prev, { text: response, type: "bot", time: botTime }]);
    }, 600);
  };

  return (
    <div>
      <div className="mb-5">
        <div className="text-[11px] text-muted-foreground mb-2">Home <span className="text-saffron">/ AI Assistant</span></div>
        <h1 className="text-xl font-bold mb-1">AI Learning Assistant</h1>
        <p className="text-[13px] text-muted-foreground">Ask anything about SOPs, courses, temple procedures, or HR policies</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3.5">
        {/* Chat */}
        <div className="border border-border rounded-xl overflow-hidden flex flex-col h-[420px]">
          <div className="px-4 py-3 bg-deep flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-saffron to-gold flex items-center justify-center text-base">🤖</div>
            <div>
              <div className="text-sm font-semibold text-primary-foreground">Naman AI</div>
              <div className="text-[11px] text-primary-foreground/50">Powered by NamanDarshan LMS</div>
            </div>
            <div className="w-2 h-2 bg-nd-green rounded-full ml-auto" />
          </div>

          <div ref={messagesRef} className="flex-1 overflow-y-auto p-3.5 flex flex-col gap-2.5 bg-secondary">
            {messages.map((m, i) => (
              <div
                key={i}
                className={`max-w-[75%] px-3.5 py-2.5 rounded-xl text-[13px] leading-relaxed ${
                  m.type === "bot"
                    ? "bg-card border border-border self-start rounded-bl-sm"
                    : "bg-saffron text-primary-foreground self-end rounded-br-sm"
                }`}
              >
                {m.text.split("\n").map((line, j) => (
                  <React.Fragment key={j}>{line}<br /></React.Fragment>
                ))}
                <div className="text-[10px] opacity-60 mt-1">{m.time}</div>
              </div>
            ))}
          </div>

          <div className="flex flex-wrap gap-1.5 px-3.5 py-2 bg-secondary">
            {quickPrompts.map(q => (
              <button
                key={q}
                onClick={() => sendMessage(q)}
                className="text-[11px] px-2.5 py-1 bg-card border border-border rounded-full hover:border-saffron hover:text-saffron transition-all"
              >
                {q}
              </button>
            ))}
          </div>

          <div className="flex gap-2 p-3 bg-card border-t border-border">
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === "Enter" && sendMessage(input)}
              placeholder="Ask about SOPs, courses, HR, temple protocols…"
              className="flex-1 px-3 py-2 border-[1.5px] border-border rounded-full text-[13px] outline-none focus:border-saffron"
            />
            <button
              onClick={() => sendMessage(input)}
              className="w-9 h-9 bg-saffron rounded-full flex items-center justify-center text-base flex-shrink-0 text-primary-foreground"
            >
              ↑
            </button>
          </div>
        </div>

        {/* Right Panel */}
        <div className="flex flex-col gap-3">
          <div className="bg-card border border-border rounded-xl p-[18px]">
            <div className="text-sm font-semibold mb-3.5 flex items-center gap-2">
              <span className="text-base">🎯</span> AI Can Help With
            </div>
            <div className="flex flex-col gap-[7px]">
              {aiCapabilities.map((c, i) => (
                <div key={i} className="flex items-center gap-2.5 p-2 bg-secondary rounded-lg">
                  <span className="text-lg">{c.icon}</span>
                  <div>
                    <div className="text-xs font-medium">{c.title}</div>
                    <div className="text-[11px] text-muted-foreground">{c.sub}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="bg-card border border-border rounded-xl p-[18px]">
            <div className="text-sm font-semibold mb-3.5 flex items-center gap-2">
              <span className="text-base">📊</span> AI Usage This Month
            </div>
            {[
              { label: "SOP Queries", value: 47, pct: 65, color: "bg-saffron", textColor: "text-saffron" },
              { label: "Course Help", value: 29, pct: 40, color: "bg-nd-blue", textColor: "text-nd-blue" },
              { label: "HR Queries", value: 18, pct: 25, color: "bg-teal", textColor: "text-teal" },
            ].map((u, i) => (
              <div key={i} className="flex items-center gap-3 py-2.5 border-b border-border last:border-b-0">
                <div className="w-24 flex-shrink-0 text-[13px]">{u.label}</div>
                <div className="flex-1 h-1.5 bg-border rounded-full overflow-hidden">
                  <div className={`h-full rounded-full ${u.color}`} style={{ width: `${u.pct}%` }} />
                </div>
                <div className={`w-8 text-right text-xs font-semibold ${u.textColor}`}>{u.value}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AIAssistant;
