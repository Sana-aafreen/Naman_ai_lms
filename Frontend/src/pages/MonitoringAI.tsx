import React, { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useAuth } from "@/contexts/AuthContext";
import { apiGet, apiPost } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────────

interface Message {
  id:      string;
  role:    "user" | "assistant";
  text:    string;
  loading?: boolean;
}

interface QuickPrompt {
  icon:  string;
  label: string;
  prompt: string;
}

interface AIInsight {
  type:  "tip" | "warning" | "celebration";
  text:  string;
}

// ── Constants ──────────────────────────────────────────────────────────────────

const QUICK_PROMPTS: QuickPrompt[] = [
  { icon: "📈", label: "How am I progressing?",   prompt: "Give me a detailed analysis of my current learning progress and what I should focus on." },
  { icon: "📚", label: "Recommend courses",        prompt: "Based on my goals and department, which courses should I prioritize next?" },
  { icon: "🎯", label: "Weekly goal check-in",     prompt: "Help me review my learning goals and create an action plan for this week." },
  { icon: "💡", label: "Skill gap analysis",       prompt: "What skills am I missing for career growth in my role and department?" },
  { icon: "🏆", label: "How to rank higher?",      prompt: "What specific steps can I take to improve my department rank and quiz scores?" },
  { icon: "🧘", label: "Balanced study plan",      prompt: "Create a realistic, balanced weekly learning schedule that fits around my work." },
];

// ── Helpers ────────────────────────────────────────────────────────────────────

const uid = () => Math.random().toString(36).slice(2, 9);

// ── Component ──────────────────────────────────────────────────────────────────

const MonitoringAI: React.FC = () => {
  const { user } = useAuth();

  const [messages,  setMessages]  = useState<Message[]>([]);
  const [input,     setInput]     = useState("");
  const [sending,   setSending]   = useState(false);
  const [insights,  setInsights]  = useState<AIInsight[]>([]);
  const [loadingInsights, setLoadingInsights] = useState(true);

  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef  = useRef<HTMLTextAreaElement>(null);

  // ── Load daily insights on mount ─────────────────────────────────────────

  useEffect(() => {
    if (!user?.id) return;
    apiPost<{ insights: AIInsight[]; greeting: string }>("/api/monitoring/insights", {
      user_id: user.id,
      name: user.name,
      role: user.role,
      department: user.department,
    })
      .then((data) => {
        setInsights(data.insights ?? []);
        // Seed greeting message
        setMessages([
          {
            id: uid(),
            role: "assistant",
            text: data.greeting ??
              `Namaste ${user.name?.split(" ")[0]} 🙏 I'm your personal Monitoring AI. I know your progress, goals, and department — ask me anything about your growth journey!`,
          },
        ]);
      })
      .catch(() => {
        setMessages([
          {
            id: uid(),
            role: "assistant",
            text: `Namaste ${user?.name?.split(" ")[0] ?? "there"} 🙏 I'm your personal Monitoring AI — your dedicated growth assistant. How can I help you grow today?`,
          },
        ]);
      })
      .finally(() => setLoadingInsights(false));
  }, [user?.id, user?.name, user?.role, user?.department]);

  // ── Auto-scroll ───────────────────────────────────────────────────────────

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ── Send message ──────────────────────────────────────────────────────────

  const sendMessage = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || sending) return;

    const userMsg: Message = { id: uid(), role: "user", text: trimmed };
    const loadingMsg: Message = { id: uid(), role: "assistant", text: "", loading: true };

    setMessages((prev) => [...prev, userMsg, loadingMsg]);
    setInput("");
    setSending(true);

    try {
      const res = await apiPost<{ reply: string }>("/api/monitoring/chat", {
        user_id:    user?.id,
        name:       user?.name,
        role:       user?.role,
        department: user?.department,
        message:    trimmed,
        history:    messages.slice(-10).map((m) => ({ role: m.role, text: m.text })),
      });

      setMessages((prev) =>
        prev.map((m) =>
          m.loading ? { ...m, text: res.reply, loading: false } : m,
        ),
      );
    } catch {
      setMessages((prev) =>
        prev.map((m) =>
          m.loading
            ? { ...m, text: "Sorry, I ran into an issue. Please try again.", loading: false }
            : m,
        ),
      );
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  // ── Insight badge style ───────────────────────────────────────────────────

  const insightStyle = (type: AIInsight["type"]) => {
    if (type === "tip")         return { bg: "bg-blue-50 border-blue-100",  icon: "💡", text: "text-blue-700" };
    if (type === "warning")     return { bg: "bg-amber-50 border-amber-100", icon: "⚠️", text: "text-amber-700" };
    if (type === "celebration") return { bg: "bg-green-50 border-green-100", icon: "🎉", text: "text-green-700" };
    return { bg: "bg-secondary border-border", icon: "💬", text: "text-foreground" };
  };

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div
      className="flex flex-col h-full max-h-[calc(100vh-64px)] overflow-hidden"
      style={{ fontFamily: "'DM Sans', system-ui, sans-serif" }}
    >
      {/* ── Page Header ── */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex-shrink-0 px-6 pt-5 pb-4"
      >
        <div className="text-[11px] text-muted-foreground mb-2">
          Home <span className="text-saffron">/ Monitoring AI</span>
        </div>
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600
              flex items-center justify-center text-xl shadow-md">
              ✨
            </div>
            <div>
              <h1 className="text-xl font-bold text-foreground tracking-tight">
                Monitoring AI
              </h1>
              <p className="text-[12px] text-muted-foreground">
                Your personal growth assistant · {user?.name}
              </p>
            </div>
          </div>

          {/* Live badge */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full
            bg-green-50 border border-green-100">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <span className="text-[11px] font-semibold text-green-700">Active · Gemini AI</span>
          </div>
        </div>
      </motion.div>

      {/* ── Main content: Insights + Chat ── */}
      <div className="flex flex-1 gap-4 px-6 pb-4 overflow-hidden min-h-0">

        {/* ── LEFT: Insights sidebar ── */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
          className="w-[260px] flex-shrink-0 flex flex-col gap-3 overflow-y-auto"
        >
          {/* Daily Insights */}
          <div className="rounded-2xl border border-border/60 bg-white p-4">
            <div className="text-[12px] font-bold text-foreground mb-3 flex items-center gap-2">
              <span>🌟</span> Today's Insights
            </div>
            {loadingInsights ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-14 rounded-xl bg-secondary/60 animate-pulse" />
                ))}
              </div>
            ) : insights.length === 0 ? (
              <div className="text-[12px] text-muted-foreground text-center py-3">
                Ask me anything to get started!
              </div>
            ) : (
              <div className="space-y-2">
                {insights.map((insight, i) => {
                  const s = insightStyle(insight.type);
                  return (
                    <div key={i} className={`rounded-xl border px-3 py-2.5 ${s.bg}`}>
                      <div className="flex items-start gap-2">
                        <span className="text-[14px] flex-shrink-0 mt-0.5">{s.icon}</span>
                        <p className={`text-[12px] leading-relaxed ${s.text}`}>{insight.text}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Quick prompts */}
          <div className="rounded-2xl border border-border/60 bg-white p-4">
            <div className="text-[12px] font-bold text-foreground mb-3 flex items-center gap-2">
              <span>⚡</span> Quick Ask
            </div>
            <div className="space-y-1.5">
              {QUICK_PROMPTS.map((qp) => (
                <button
                  key={qp.label}
                  onClick={() => sendMessage(qp.prompt)}
                  disabled={sending}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-left
                    hover:bg-violet-50 hover:border-violet-100 border border-transparent
                    transition-all duration-150 group disabled:opacity-50"
                >
                  <span className="text-[14px] flex-shrink-0">{qp.icon}</span>
                  <span className="text-[12px] text-muted-foreground group-hover:text-indigo-700
                    font-medium transition-colors leading-tight">
                    {qp.label}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Profile summary card */}
          <div className="rounded-2xl border border-violet-100 bg-gradient-to-br
            from-violet-50 to-indigo-50 p-4">
            <div className="text-[12px] font-bold text-indigo-700 mb-2">Personalized For</div>
            <div className="text-[13px] font-semibold text-foreground">{user?.name}</div>
            <div className="text-[11px] text-indigo-600/70 mt-0.5">
              {user?.role} · {user?.department}
            </div>
            <div className="mt-3 text-[11px] text-indigo-600/80 leading-relaxed">
              I have access to your progress, quiz scores, leave history, and goals to give you
              truly personalized advice.
            </div>
          </div>
        </motion.div>

        {/* ── RIGHT: Chat window ── */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="flex-1 flex flex-col rounded-2xl border border-border/60 bg-white overflow-hidden min-w-0"
        >
          {/* Chat header */}
          <div className="px-5 py-3.5 border-b border-border/50 flex items-center gap-3 flex-shrink-0
            bg-gradient-to-r from-violet-50/60 to-indigo-50/40">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600
              flex items-center justify-center text-[14px] shadow-sm">
              ✨
            </div>
            <div>
              <div className="text-[13px] font-semibold text-foreground">Monitoring AI</div>
              <div className="text-[11px] text-muted-foreground">Powered by Gemini · Always learning about you</div>
            </div>
            <div className="ml-auto flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
              <span className="text-[11px] text-muted-foreground">Online</span>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
            <AnimatePresence initial={false}>
              {messages.map((msg) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.25 }}
                  className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
                >
                  {/* Avatar */}
                  {msg.role === "assistant" ? (
                    <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600
                      flex items-center justify-center text-[13px] flex-shrink-0 shadow-sm mt-0.5">
                      ✨
                    </div>
                  ) : (
                    <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-saffron to-gold
                      flex items-center justify-center text-[11px] font-bold text-white
                      flex-shrink-0 shadow-sm mt-0.5">
                      {user?.name?.charAt(0).toUpperCase() ?? "U"}
                    </div>
                  )}

                  {/* Bubble */}
                  <div
                    className={`max-w-[75%] rounded-2xl px-4 py-3 text-[13px] leading-relaxed
                      ${msg.role === "assistant"
                        ? "bg-secondary/50 border border-border/40 text-foreground rounded-tl-sm"
                        : "bg-gradient-to-br from-saffron to-gold text-white rounded-tr-sm shadow-sm"
                      }`}
                  >
                    {msg.loading ? (
                      <div className="flex items-center gap-1.5 py-1">
                        {[0, 150, 300].map((delay) => (
                          <span
                            key={delay}
                            className="w-2 h-2 rounded-full bg-muted-foreground/40 animate-bounce"
                            style={{ animationDelay: `${delay}ms` }}
                          />
                        ))}
                      </div>
                    ) : (
                      <div className="whitespace-pre-wrap">{msg.text}</div>
                    )}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
            <div ref={bottomRef} />
          </div>

          {/* Input area */}
          <div className="px-4 py-4 border-t border-border/50 flex-shrink-0">
            <div className="flex items-end gap-3 bg-secondary/40 border border-border/60
              rounded-2xl px-4 py-3 focus-within:border-violet-200 focus-within:bg-white
              focus-within:shadow-sm transition-all duration-200">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask me about your growth, courses, goals…"
                rows={1}
                className="flex-1 bg-transparent outline-none resize-none text-[13px]
                  text-foreground placeholder:text-muted-foreground/60 min-h-[22px] max-h-[100px]"
                style={{ lineHeight: "1.5" }}
              />
              <button
                onClick={() => sendMessage(input)}
                disabled={sending || !input.trim()}
                className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600
                  flex items-center justify-center text-white shadow-sm flex-shrink-0
                  hover:shadow-md hover:-translate-y-0.5 active:translate-y-0
                  transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed
                  disabled:hover:translate-y-0 disabled:hover:shadow-none"
              >
                {sending ? (
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <span className="text-[14px]">↑</span>
                )}
              </button>
            </div>
            <div className="text-[10px] text-muted-foreground text-center mt-2">
              Press Enter to send · Shift+Enter for new line
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default MonitoringAI;
