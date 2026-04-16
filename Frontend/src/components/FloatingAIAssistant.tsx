import React, { useEffect, useRef, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { apiPost } from "@/lib/api";

interface Message {
  text: string;
  type: "bot" | "user";
  time: string;
}

type ChatMode = "sop" | "calendar";

const quickPrompts: Record<ChatMode, string[]> = {
  sop: [
    "What's the VIP Darshan SOP?",
    "How should I handle a leave approval request?",
    "Customer needs quick operations guidance",
  ],
  calendar: [
    "What meetings do I have today?",
    "What is my leave status?",
    "Can you help with scheduling?",
  ],
};

const FloatingAIAssistant: React.FC = () => {
  const { user } = useAuth();
  const isAdmin = user?.role === "Admin";
  const [mode, setMode] = useState<ChatMode>("sop");
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      text: "Jai Shri Ram 🙏 Ask your SOP or workflow question and I’ll guide you.",
      type: "bot",
      time: "Now",
    },
  ]);
  const messagesRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (messagesRef.current) {
      messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
    }
  }, [messages, isOpen]);

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
        const data = await apiPost<{ answer?: string; escalation?: string }>("/api/ai/chat", {
          query: text,
          department: isAdmin ? undefined : user?.department,
          employeeName: user?.name,
        });
        pushBotMessage(
          data?.answer ||
            data?.escalation ||
            "I could not find the right SOP match yet. Try adding the department, task, and blocker.",
        );
      } else {
        const data = await apiPost<{ reply?: string }>("/api/agent", {
          message: text,
          employee_id: user?.id,
        });
        pushBotMessage(
          data?.reply || "Calendar Manager could not answer that yet. Try asking about meetings or leave.",
        );
      }
    } catch (error) {
      console.error("Floating AI chat failed:", error);
      pushBotMessage("I hit a problem while checking that. Please try again in a moment.");
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="fixed right-6 bottom-6 z-50 flex flex-col items-end gap-3">
      {isOpen && (
        <div className="w-[360px] max-w-[calc(100vw-2rem)] rounded-2xl border border-border bg-card shadow-2xl overflow-hidden">
          <div className="px-4 py-3 bg-deep flex items-center gap-2.5 text-primary-foreground">
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-saffron to-gold flex items-center justify-center text-base">
              🤖
            </div>
            <div className="flex-1">
              <div className="text-sm font-semibold">Naman AI</div>
              <div className="text-[11px] text-primary-foreground/60">
                {mode === "sop" ? "SOP assistant" : "Calendar manager"}
              </div>
            </div>
            <div className="flex gap-1 rounded-full bg-white/10 p-1">
              <button
                onClick={() => setMode("sop")}
                className={`px-2 py-1 rounded-full text-[10px] font-semibold ${
                  mode === "sop" ? "bg-white text-foreground" : "text-primary-foreground/70"
                }`}
              >
                SOP
              </button>
              <button
                onClick={() => setMode("calendar")}
                className={`px-2 py-1 rounded-full text-[10px] font-semibold ${
                  mode === "calendar" ? "bg-white text-foreground" : "text-primary-foreground/70"
                }`}
              >
                Calendar
              </button>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="w-8 h-8 rounded-full bg-white/10 hover:bg-white/20 transition-colors text-sm"
              aria-label="Close AI assistant"
            >
              ✕
            </button>
          </div>

          <div ref={messagesRef} className="h-[320px] overflow-y-auto bg-secondary p-3 flex flex-col gap-2.5">
            {messages.map((message, index) => (
              <div
                key={index}
                className={`max-w-[82%] px-3 py-2.5 rounded-xl text-[13px] leading-relaxed ${
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

          <div className="flex flex-wrap gap-1.5 px-3 py-2 bg-secondary border-t border-border">
            {quickPrompts[mode].map((prompt) => (
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
              placeholder={mode === "sop" ? "Ask a workflow or SOP question..." : "Ask about meetings or leave..."}
              className="flex-1 px-3 py-2 border-[1.5px] border-border rounded-full text-[13px] outline-none focus:border-saffron"
            />
            <button
              onClick={() => void sendMessage(input)}
              disabled={isSending}
              className="w-9 h-9 bg-saffron rounded-full flex items-center justify-center text-base text-primary-foreground disabled:opacity-60"
            >
              {isSending ? "…" : "↑"}
            </button>
          </div>
        </div>
      )}

      <button
        onClick={() => setIsOpen((value) => !value)}
        className="flex items-center gap-2 rounded-full bg-deep text-primary-foreground px-4 py-3 shadow-lg hover:translate-y-[-1px] transition-transform"
      >
        <span className="w-8 h-8 rounded-full bg-gradient-to-br from-saffron to-gold flex items-center justify-center text-base">
          🤖
        </span>
        <span className="text-sm font-semibold">AI Assistant</span>
      </button>
    </div>
  );
};

export default FloatingAIAssistant;
