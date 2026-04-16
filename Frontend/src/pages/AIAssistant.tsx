import React, { useEffect, useRef, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { apiPost } from "@/lib/api";

interface Message {
  text: string;
  type: "bot" | "user";
  time: string;
}

type ChatMode = "sop" | "calendar";

const promptMap: Record<ChatMode, string[]> = {
  sop: [
    "What's the VIP Darshan SOP?",
    "How do I file an insurance claim?",
    "Recommend courses for me",
    "How should I handle a leave approval request?",
  ],
  calendar: [
    "What meetings do I have this week?",
    "Show my leave status",
    "Can you help schedule a team sync tomorrow?",
    "What calendar items need manager attention?",
  ],
};

const AIAssistant: React.FC = () => {
  const { user } = useAuth();
  const isAdmin = user?.role === "Admin";
  const [mode, setMode] = useState<ChatMode>("sop");
  const [messages, setMessages] = useState<Message[]>([
    {
      text: "Jai Shri Ram 🙏 Choose SOP Assistant or Calendar Manager and ask your question.",
      type: "bot",
      time: "Just now",
    },
  ]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const messagesRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (messagesRef.current) {
      messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
    }
  }, [messages]);

  const pushBotMessage = (text: string) => {
    const botTime = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    setMessages((prev) => [...prev, { text, type: "bot", time: botTime }]);
  };

  const sendMessage = async (text: string) => {
    if (!text.trim() || isSending) return;

    const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    setMessages((prev) => [...prev, { text, type: "user", time: now }]);
    setInput("");
    setIsSending(true);

    try {
      if (mode === "sop") {
        const data = await apiPost<{
          answer?: string;
          escalation?: string;
        }>("/api/ai/chat", {
          query: text,
          department: isAdmin ? undefined : user?.department,
          employeeName: user?.name,
        });

        pushBotMessage(
          data?.answer ||
            data?.escalation ||
            "I could not find a strong SOP match yet. Please add the department, task, and blocker in one sentence.",
        );
      } else {
        const data = await apiPost<{ reply?: string }>("/api/agent", {
          message: text,
          employee_id: user?.id,
        });

        pushBotMessage(
          data?.reply || "Calendar Manager could not answer that yet. Try asking about meetings, leave, or scheduling.",
        );
      }
    } catch (error) {
      console.error("AI chat failed:", error);
      pushBotMessage("I hit a problem while processing your request. Please try again in a moment.");
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div>
      <div className="mb-5">
        <div className="text-[11px] text-muted-foreground mb-2">
          Home <span className="text-saffron">/ AI Assistant</span>
        </div>
        <h1 className="text-xl font-bold mb-1">AI Assistant</h1>
        <p className="text-[13px] text-muted-foreground">
          Switch between SOP guidance and calendar operations without leaving the chatbox.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3.5">
        <div className="border border-border rounded-xl overflow-hidden flex flex-col h-[460px]">
          <div className="px-4 py-3 bg-deep flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-saffron to-gold flex items-center justify-center text-base">
              🤖
            </div>
            <div>
              <div className="text-sm font-semibold text-primary-foreground">Naman AI</div>
              <div className="text-[11px] text-primary-foreground/60">
                {mode === "sop" ? "AIChat SOP assistant" : "Calendar manager agent"}
              </div>
            </div>
            <div className="ml-auto flex gap-1 rounded-full bg-white/10 p-1">
              <button
                onClick={() => setMode("sop")}
                className={`px-3 py-1 rounded-full text-[11px] font-semibold ${
                  mode === "sop" ? "bg-white text-foreground" : "text-primary-foreground/70"
                }`}
              >
                SOP
              </button>
              <button
                onClick={() => setMode("calendar")}
                className={`px-3 py-1 rounded-full text-[11px] font-semibold ${
                  mode === "calendar" ? "bg-white text-foreground" : "text-primary-foreground/70"
                }`}
              >
                Calendar
              </button>
            </div>
          </div>

          <div ref={messagesRef} className="flex-1 overflow-y-auto p-3.5 flex flex-col gap-2.5 bg-secondary">
            {messages.map((message, index) => (
              <div
                key={index}
                className={`max-w-[78%] px-3.5 py-2.5 rounded-xl text-[13px] leading-relaxed ${
                  message.type === "bot"
                    ? "bg-card border border-border self-start rounded-bl-sm"
                    : "bg-saffron text-primary-foreground self-end rounded-br-sm"
                }`}
              >
                {message.text.split("\n").map((line, lineIndex) => (
                  <React.Fragment key={lineIndex}>
                    {line}
                    <br />
                  </React.Fragment>
                ))}
                <div className="text-[10px] opacity-60 mt-1">{message.time}</div>
              </div>
            ))}
          </div>

          <div className="flex flex-wrap gap-1.5 px-3.5 py-2 bg-secondary">
            {promptMap[mode].map((prompt) => (
              <button
                key={prompt}
                onClick={() => void sendMessage(prompt)}
                className="text-[11px] px-2.5 py-1 bg-card border border-border rounded-full hover:border-saffron hover:text-saffron transition-all"
              >
                {prompt}
              </button>
            ))}
          </div>

          <div className="flex gap-2 p-3 bg-card border-t border-border">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && void sendMessage(input)}
              placeholder={mode === "sop" ? "Ask about SOPs, policies, or courses..." : "Ask about leaves, meetings, or scheduling..."}
              className="flex-1 px-3 py-2 border-[1.5px] border-border rounded-full text-[13px] outline-none focus:border-saffron"
            />
            <button
              onClick={() => void sendMessage(input)}
              disabled={isSending}
              className="w-9 h-9 bg-saffron rounded-full flex items-center justify-center text-base flex-shrink-0 text-primary-foreground disabled:opacity-60"
            >
              {isSending ? "…" : "↑"}
            </button>
          </div>
        </div>

        <div className="flex flex-col gap-3">
          <div className="bg-card border border-border rounded-xl p-[18px]">
            <div className="text-sm font-semibold mb-3.5 flex items-center gap-2">
              <span className="text-base">🎯</span> Mode Guide
            </div>
            <div className="space-y-3 text-[12px] text-muted-foreground">
              <div>
                <div className="font-semibold text-foreground">SOP Assistant</div>
                <div>Uses `AIChat.py` to answer from original SOP PDFs and the SOP knowledge base.</div>
              </div>
              <div>
                <div className="font-semibold text-foreground">Calendar Manager</div>
                <div>Uses `calendar_manager.py` to answer questions about meetings, leave, and scheduling flow.</div>
              </div>
            </div>
          </div>

          <div className="bg-card border border-border rounded-xl p-[18px]">
            <div className="text-sm font-semibold mb-3.5 flex items-center gap-2">
              <span className="text-base">🧠</span> End-to-End
            </div>
            <div className="space-y-2 text-[12px] text-muted-foreground">
              <p>`SOP` mode calls `/api/ai/chat` on the Python backend.</p>
              <p>`Calendar` mode calls `/api/agent` on the same backend.</p>
              <p>
                Your identity is always sent, and admins search globally instead of being locked to one department.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AIAssistant;
