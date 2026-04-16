import React, { useCallback, useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Link } from "react-router-dom";
import { apiGet, apiPost } from "@/lib/api";

type UpdateCategory =
  | "Achievement"
  | "Policy"
  | "Event"
  | "Announcement"
  | "Training"
  | "Other";

interface WhatsNewUpdate {
  id: number;
  author_id: string;
  author_name: string;
  author_role: string;
  department: string;
  category: UpdateCategory;
  title: string;
  body: string;
  status: "pending" | "approved" | "rejected";
  created_at: string;
  approved_at?: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const CATEGORY_META: Record<
  UpdateCategory,
  { icon: string; bg: string; text: string }
> = {
  Achievement: { icon: "🏆", bg: "bg-amber-100 dark:bg-amber-900/30", text: "text-amber-700 dark:text-amber-300" },
  Policy:      { icon: "📋", bg: "bg-blue-100 dark:bg-blue-900/30",   text: "text-blue-700 dark:text-blue-300" },
  Event:       { icon: "🗓️", bg: "bg-purple-100 dark:bg-purple-900/30", text: "text-purple-700 dark:text-purple-300" },
  Announcement:{ icon: "📢", bg: "bg-saffron/10",                      text: "text-saffron" },
  Training:    { icon: "🎓", bg: "bg-green-100 dark:bg-green-900/30",  text: "text-green-700 dark:text-green-300" },
  Other:       { icon: "💡", bg: "bg-secondary",                       text: "text-muted-foreground" },
};

const CATEGORIES: UpdateCategory[] = [
  "Achievement", "Policy", "Event", "Announcement", "Training", "Other",
];

// ─── Helpers ──────────────────────────────────────────────────────────────────

const timeAgo = (dateStr: string) => {
  const diff = Date.now() - new Date(dateStr).getTime();
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString();
};

// ─── Components ───────────────────────────────────────────────────────────────

const SectionHeader: React.FC<{
  title: string;
  linkTo?: string;
  linkLabel?: string;
  action?: React.ReactNode;
}> = ({ title, linkTo, linkLabel, action }) => (
  <div className="flex items-center justify-between mb-3">
    <div className="text-sm font-semibold">{title}</div>
    <div className="flex items-center gap-2">
      {action}
      {linkTo && (
        <Link to={linkTo} className="text-[11px] font-semibold text-saffron hover:underline">
          {linkLabel ?? "View all →"}
        </Link>
      )}
    </div>
  </div>
);

const EmptyState: React.FC<{ message: string }> = ({ message }) => (
  <div className="text-[13px] text-muted-foreground py-4 text-center">{message}</div>
);

const UpdateCard: React.FC<{
  update: WhatsNewUpdate;
  isAdmin: boolean;
  onApprove?: (id: number) => void;
  onReject?: (id: number) => void;
}> = ({ update, isAdmin, onApprove, onReject }) => {
  const meta = CATEGORY_META[update.category] ?? CATEGORY_META.Other;
  const isPending = update.status === "pending";

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className={`rounded-xl border p-3.5 transition-all ${
        isPending
          ? "border-amber-300/60 bg-amber-50/40 dark:bg-amber-950/10"
          : "border-border bg-secondary/30"
      }`}
    >
      <div className="flex items-start gap-3">
        {/* Category icon */}
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center text-lg flex-shrink-0 ${meta.bg}`}>
          {meta.icon}
        </div>

        <div className="flex-1 min-w-0">
          {/* Header row */}
          <div className="flex items-center gap-2 flex-wrap mb-0.5">
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${meta.bg} ${meta.text}`}>
              {update.category}
            </span>
            {isPending && (
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
                Pending
              </span>
            )}
            <span className="text-[10px] text-muted-foreground ml-auto">{timeAgo(update.created_at)}</span>
          </div>

          {/* Title + body */}
          <div className="text-[13px] font-semibold leading-snug mb-1">{update.title}</div>
          <div className="text-[12px] text-muted-foreground leading-relaxed mb-2">{update.body}</div>

          {/* Author */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <div className="w-5 h-5 rounded-full bg-gradient-to-br from-saffron to-gold flex items-center justify-center text-white text-[9px] font-bold flex-shrink-0">
                {update.author_name.charAt(0).toUpperCase()}
              </div>
              <span className="text-[11px] text-muted-foreground">
                {update.author_name} · {update.department}
              </span>
            </div>

            {/* Admin approve/reject */}
            {isAdmin && isPending && (
              <div className="flex gap-1.5 ml-2">
                <button
                  onClick={() => onApprove?.(update.id)}
                  className="text-[11px] font-semibold px-2.5 py-1 rounded-lg bg-green-100 text-green-700 hover:bg-green-200 dark:bg-green-900/30 dark:text-green-300 transition"
                >
                  ✓ Approve
                </button>
                <button
                  onClick={() => onReject?.(update.id)}
                  className="text-[11px] font-semibold px-2.5 py-1 rounded-lg bg-red-100 text-red-700 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-300 transition"
                >
                  ✕ Reject
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
};

// ─── Main Component ────────────────────────────────────────────────────────────

interface WhatsNewSectionProps {
  isAdmin: boolean;
  currentUser: { id?: string; name?: string; role?: string; department?: string } | null;
  onOpenComposer: () => void;
}

export const WhatsNewSection: React.FC<WhatsNewSectionProps> = ({ isAdmin, currentUser, onOpenComposer }) => {
  const [updates, setUpdates] = useState<WhatsNewUpdate[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | UpdateCategory>("all");

  const fetchUpdates = useCallback(async () => {
    try {
      // Admins see all (pending + approved); others see only approved
      const endpoint = isAdmin
        ? "/api/whats-new?include_pending=true"
        : "/api/whats-new";
      const data = await apiGet<WhatsNewUpdate[]>(endpoint);
      setUpdates(data ?? []);
    } catch {
      setUpdates([]);
    } finally {
      setLoading(false);
    }
  }, [isAdmin]);

  useEffect(() => { fetchUpdates(); }, [fetchUpdates]);

  const handleApprove = async (id: number) => {
    try {
      await apiPost(`/api/whats-new/${id}/approve`, {});
      setUpdates((prev) =>
        prev.map((u) => (u.id === id ? { ...u, status: "approved" } : u))
      );
    } catch { /* ignore */ }
  };

  const handleReject = async (id: number) => {
    try {
      await apiPost(`/api/whats-new/${id}/reject`, {});
      setUpdates((prev) => prev.filter((u) => u.id !== id));
    } catch { /* ignore */ }
  };

  const pendingCount = updates.filter((u) => u.status === "pending").length;

  const filtered = useMemo(() => {
    // Admin sees pending first, then approved. Others see newest approved first.
    const sorted = isAdmin
      ? [...updates].sort((a, b) => {
          if (a.status === "pending" && b.status !== "pending") return -1;
          if (b.status === "pending" && a.status !== "pending") return 1;
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        })
      : [...updates].sort(
          (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        );

    if (filter === "all") return sorted;
    return sorted.filter((u) => u.category === filter);
  }, [updates, filter, isAdmin]);

  return (
    <motion.div className="bg-card border border-border rounded-xl p-[18px]">
      <SectionHeader
        title={
          isAdmin && pendingCount > 0
            ? `What's New · ${pendingCount} pending`
            : "What's New ✨"
        }
        action={
          <button
            onClick={onOpenComposer}
            className="flex items-center gap-1 text-[11px] font-semibold px-2.5 py-1 rounded-lg bg-saffron/10 text-saffron border border-saffron/20 hover:bg-saffron/20 transition"
          >
            + Post Update
          </button>
        }
      />

      {/* Category filter chips */}
      {updates.length > 0 && (
        <div className="flex gap-1.5 flex-wrap mb-3">
          <button
            onClick={() => setFilter("all")}
            className={`text-[10px] font-semibold px-2.5 py-1 rounded-full border transition
              ${filter === "all"
                ? "bg-saffron text-white border-saffron"
                : "bg-secondary text-muted-foreground border-border hover:border-saffron/40"
              }`}
          >
            All
          </button>
          {CATEGORIES.filter((c) => updates.some((u) => u.category === c)).map((cat) => {
            const m = CATEGORY_META[cat];
            return (
              <button
                key={cat}
                onClick={() => setFilter(cat)}
                className={`text-[10px] font-semibold px-2.5 py-1 rounded-full border transition
                  ${filter === cat
                    ? `${m.bg} ${m.text} border-current`
                    : "bg-secondary text-muted-foreground border-border hover:border-saffron/40"
                  }`}
              >
                {m.icon} {cat}
              </button>
            );
          })}
        </div>
      )}

      {/* Feed */}
      {loading ? (
        <EmptyState message="Loading updates…" />
      ) : filtered.length === 0 ? (
        <EmptyState message="No updates yet — be the first to post!" />
      ) : (
        <div className="flex flex-col gap-2.5 max-h-[460px] overflow-y-auto pr-0.5">
          <AnimatePresence mode="popLayout">
            {filtered.map((update) => (
              <UpdateCard
                key={update.id}
                update={update}
                isAdmin={isAdmin}
                onApprove={handleApprove}
                onReject={handleReject}
              />
            ))}
          </AnimatePresence>
        </div>
      )}
    </motion.div>
  );
};