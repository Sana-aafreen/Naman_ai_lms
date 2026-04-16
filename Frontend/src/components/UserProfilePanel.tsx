/**
 * UserProfilePanel.tsx
 * Slide-out panel for viewing and editing user profile.
 * Supports avatar upload (base64 stored in backend), bio, skills, and goals.
 */

import React, { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useAuth } from "@/contexts/AuthContext";
import { apiGet, apiPost } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────────

interface UserProfile {
  user_id:       string;
  display_name:  string;
  bio:           string;
  avatar_url:    string;   // base64 data-uri or hosted URL
  skills:        string[]; // comma-separated tags
  goals:         string;
  phone:         string;
  linkedin:      string;
  joined_date:   string;
  courses_done:  number;
  avg_score:     number;
}

interface SavedCourse {
  id: string;
  title: string;
  department: string;
  generated_at: string;
  htmlContent: string;
}

interface Props {
  open:    boolean;
  onClose: () => void;
}

// ── Component ─────────────────────────────────────────────────────────────────

const UserProfilePanel: React.FC<Props> = ({ open, onClose }) => {
  const { user } = useAuth();

  const [profile,  setProfile]  = useState<UserProfile | null>(null);
  const [loading,  setLoading]  = useState(false);
  const [saving,   setSaving]   = useState(false);
  const [saved,    setSaved]    = useState(false);
  const [tab,      setTab]      = useState<"profile" | "stats" | "goals" | "saved">("profile");
  const [savedCourses, setSavedCourses] = useState<SavedCourse[]>([]);

  // Editable fields
  const [bio,          setBio]          = useState("");
  const [phone,        setPhone]        = useState("");
  const [linkedin,     setLinkedin]     = useState("");
  const [goals,        setGoals]        = useState("");
  const [skillInput,   setSkillInput]   = useState("");
  const [skills,       setSkills]       = useState<string[]>([]);
  const [avatarPreview, setAvatarPreview] = useState<string>("");

  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── Fetch profile on open ─────────────────────────────────────────────────

  useEffect(() => {
    if (!open || !user?.id) return;
    setLoading(true);
    try {
      const courses = JSON.parse(localStorage.getItem(`saved-courses-${user.id}`) || '[]');
      setSavedCourses(courses);
    } catch(e) {}

    apiGet<UserProfile>(`/api/profile/${user.id}`)
      .then((data) => {
        setProfile(data);
        setBio(data.bio ?? "");
        setPhone(data.phone ?? "");
        setLinkedin(data.linkedin ?? "");
        setGoals(data.goals ?? "");
        setSkills(data.skills ?? []);
        setAvatarPreview(data.avatar_url ?? "");
      })
      .catch(() => {
        // New user — empty profile
        setProfile(null);
      })
      .finally(() => setLoading(false));
  }, [open, user?.id]);

  // ── Avatar upload ─────────────────────────────────────────────────────────

  const handleAvatarChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) {
      alert("Image must be under 2 MB");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => setAvatarPreview(reader.result as string);
    reader.readAsDataURL(file);
  };

  // ── Skills ────────────────────────────────────────────────────────────────

  const addSkill = () => {
    const s = skillInput.trim();
    if (s && !skills.includes(s) && skills.length < 10) {
      setSkills((prev) => [...prev, s]);
      setSkillInput("");
    }
  };

  const removeSkill = (skill: string) =>
    setSkills((prev) => prev.filter((s) => s !== skill));

  // ── Save ──────────────────────────────────────────────────────────────────

  const handleSave = async () => {
    if (!user?.id) return;
    setSaving(true);
    try {
      await apiPost(`/api/profile/${user.id}`, {
        bio,
        phone,
        linkedin,
        goals,
        skills,
        avatar_url: avatarPreview,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (err) {
      console.error("Profile save failed", err);
    } finally {
      setSaving(false);
    }
  };

  // ── Initials fallback ─────────────────────────────────────────────────────

  const initials = user?.name
    ? user.name.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase()
    : "U";

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/30 backdrop-blur-[2px] z-[60]"
          />

          {/* Panel */}
          <motion.aside
            key="panel"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 28, stiffness: 280 }}
            className="fixed right-0 top-0 bottom-0 w-[420px] max-w-full bg-white z-[70]
              flex flex-col shadow-2xl border-l border-border/60 overflow-hidden"
            style={{ fontFamily: "'DM Sans', system-ui, sans-serif" }}
          >
            {/* ── Top gradient bar ── */}
            <div className="h-[3px] bg-gradient-to-r from-saffron via-gold to-saffron flex-shrink-0" />

            {/* ── Header ── */}
            <div className="relative px-6 pt-6 pb-4 border-b border-border/50 flex-shrink-0
              bg-gradient-to-br from-saffron/5 via-white to-gold/5">
              <button
                onClick={onClose}
                className="absolute top-5 right-5 w-8 h-8 rounded-full bg-secondary/80
                  flex items-center justify-center text-muted-foreground
                  hover:bg-secondary hover:text-foreground transition-all text-sm"
              >
                ✕
              </button>

              {/* Avatar section */}
              <div className="flex items-center gap-4">
                <div className="relative">
                  <div
                    onClick={() => fileInputRef.current?.click()}
                    className="w-20 h-20 rounded-2xl overflow-hidden cursor-pointer
                      ring-2 ring-saffron/20 hover:ring-saffron/50 transition-all
                      group relative shadow-md"
                  >
                    {avatarPreview ? (
                      <img
                        src={avatarPreview}
                        alt="Avatar"
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full bg-gradient-to-br from-saffron to-gold
                        flex items-center justify-center text-2xl font-bold text-white">
                        {initials}
                      </div>
                    )}
                    {/* Overlay on hover */}
                    <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100
                      transition-opacity flex items-center justify-center">
                      <span className="text-white text-lg">📷</span>
                    </div>
                  </div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={handleAvatarChange}
                  />
                  {/* Camera badge */}
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-saffron
                      flex items-center justify-center text-[11px] shadow-md hover:bg-gold transition-colors"
                  >
                    📷
                  </button>
                </div>

                <div className="min-w-0 flex-1">
                  <div className="text-lg font-bold text-foreground tracking-tight truncate">
                    {user?.name}
                  </div>
                  <div className="flex items-center gap-2 mt-1 flex-wrap">
                    <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full
                      ${user?.role === "Admin"   ? "bg-red-100 text-red-600" :
                        user?.role === "Manager" ? "bg-blue-100 text-blue-600" :
                                                   "bg-saffron/10 text-saffron"}`}>
                      {user?.role}
                    </span>
                    <span className="text-[12px] text-muted-foreground">{user?.department}</span>
                  </div>
                  <div className="text-[11px] text-muted-foreground/70 mt-1">{user?.email}</div>
                </div>
              </div>

              {/* Tab switcher */}
              <div className="flex gap-1 mt-4 bg-secondary/50 p-1 rounded-xl">
                {(["profile", "stats", "goals", "saved"] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => setTab(t)}
                    className={`flex-1 py-1.5 text-[12px] font-semibold rounded-lg capitalize transition-all
                      ${tab === t
                        ? "bg-white shadow-sm text-saffron"
                        : "text-muted-foreground hover:text-foreground"}`}
                  >
                    {t === "profile" ? "👤 Profile" : t === "stats" ? "📊 Stats" : t === "goals" ? "🎯 Goals" : "📥 Saved"}
                  </button>
                ))}
              </div>
            </div>

            {/* ── Body ── */}
            <div className="flex-1 overflow-y-auto">
              {loading ? (
                <div className="flex items-center justify-center h-40 text-muted-foreground text-sm">
                  Loading profile…
                </div>
              ) : (
                <div className="p-6 space-y-5">

                  {/* ── PROFILE TAB ── */}
                  {tab === "profile" && (
                    <>
                      {/* Bio */}
                      <div>
                        <label className="text-[12px] font-semibold text-foreground mb-1.5 block">
                          About Me
                        </label>
                        <textarea
                          value={bio}
                          onChange={(e) => setBio(e.target.value)}
                          placeholder="Write a short bio about yourself…"
                          rows={3}
                          maxLength={300}
                          className="w-full px-3 py-2.5 bg-secondary/40 border border-border/60 rounded-xl
                            text-[13px] text-foreground placeholder:text-muted-foreground/60
                            outline-none focus:border-saffron/40 focus:bg-white focus:shadow-sm
                            transition-all resize-none"
                        />
                        <div className="text-right text-[10px] text-muted-foreground mt-1">
                          {bio.length}/300
                        </div>
                      </div>

                      {/* Phone */}
                      <div>
                        <label className="text-[12px] font-semibold text-foreground mb-1.5 block">
                          📞 Phone
                        </label>
                        <input
                          type="tel"
                          value={phone}
                          onChange={(e) => setPhone(e.target.value)}
                          placeholder="+91 98765 43210"
                          className="w-full px-3 py-2.5 bg-secondary/40 border border-border/60 rounded-xl
                            text-[13px] placeholder:text-muted-foreground/60 outline-none
                            focus:border-saffron/40 focus:bg-white focus:shadow-sm transition-all"
                        />
                      </div>

                      {/* LinkedIn */}
                      <div>
                        <label className="text-[12px] font-semibold text-foreground mb-1.5 block">
                          🔗 LinkedIn
                        </label>
                        <input
                          type="url"
                          value={linkedin}
                          onChange={(e) => setLinkedin(e.target.value)}
                          placeholder="https://linkedin.com/in/your-name"
                          className="w-full px-3 py-2.5 bg-secondary/40 border border-border/60 rounded-xl
                            text-[13px] placeholder:text-muted-foreground/60 outline-none
                            focus:border-saffron/40 focus:bg-white focus:shadow-sm transition-all"
                        />
                      </div>

                      {/* Skills */}
                      <div>
                        <label className="text-[12px] font-semibold text-foreground mb-1.5 block">
                          🏷️ Skills & Expertise
                        </label>
                        <div className="flex gap-2 mb-2">
                          <input
                            type="text"
                            value={skillInput}
                            onChange={(e) => setSkillInput(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addSkill())}
                            placeholder="Add a skill…"
                            className="flex-1 px-3 py-2 bg-secondary/40 border border-border/60 rounded-xl
                              text-[13px] placeholder:text-muted-foreground/60 outline-none
                              focus:border-saffron/40 focus:bg-white transition-all"
                          />
                          <button
                            onClick={addSkill}
                            className="px-3 py-2 bg-saffron text-white rounded-xl text-[12px] font-semibold
                              hover:bg-gold transition-colors flex-shrink-0"
                          >
                            Add
                          </button>
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {skills.map((skill) => (
                            <span
                              key={skill}
                              className="flex items-center gap-1 text-[11px] font-medium px-2.5 py-1
                                bg-saffron/10 text-saffron border border-saffron/20 rounded-full"
                            >
                              {skill}
                              <button
                                onClick={() => removeSkill(skill)}
                                className="hover:text-red-500 transition-colors ml-0.5 text-[10px]"
                              >
                                ✕
                              </button>
                            </span>
                          ))}
                          {skills.length === 0 && (
                            <span className="text-[12px] text-muted-foreground">No skills added yet</span>
                          )}
                        </div>
                      </div>
                    </>
                  )}

                  {/* ── STATS TAB ── */}
                  {tab === "stats" && (
                    <div className="space-y-4">
                      <div className="text-[12px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                        Learning Overview
                      </div>

                      {[
                        { label: "Courses Completed", value: profile?.courses_done ?? 0, icon: "✅", color: "text-nd-green" },
                        { label: "Average Quiz Score", value: `${profile?.avg_score ?? 0}%`, icon: "🎯", color: "text-saffron" },
                        { label: "Member Since", value: profile?.joined_date ?? "—", icon: "📅", color: "text-nd-blue" },
                      ].map((stat) => (
                        <div
                          key={stat.label}
                          className="flex items-center gap-3 rounded-xl border border-border/60
                            bg-secondary/30 px-4 py-3"
                        >
                          <span className="text-xl">{stat.icon}</span>
                          <div className="flex-1">
                            <div className="text-[11px] text-muted-foreground">{stat.label}</div>
                            <div className={`text-lg font-bold ${stat.color}`}>{stat.value}</div>
                          </div>
                        </div>
                      ))}

                      {/* Department info */}
                      <div className="rounded-xl border border-border/60 bg-gradient-to-br from-saffron/5 to-gold/5 px-4 py-4 mt-2">
                        <div className="text-[12px] font-semibold text-muted-foreground mb-2">Department</div>
                        <div className="text-[15px] font-bold text-foreground">{user?.department}</div>
                        <div className="text-[12px] text-muted-foreground mt-0.5">{user?.role}</div>
                      </div>
                    </div>
                  )}

                  {/* ── GOALS TAB ── */}
                  {tab === "goals" && (
                    <div className="space-y-5">
                      <div className="rounded-xl bg-gradient-to-br from-violet-50 to-indigo-50
                        border border-violet-100 px-4 py-3 flex items-start gap-3">
                        <span className="text-xl mt-0.5">✨</span>
                        <div>
                          <div className="text-[12px] font-semibold text-indigo-700">Monitoring AI Tip</div>
                          <div className="text-[12px] text-indigo-600/80 mt-0.5">
                            Set clear learning goals and your personal AI will track your progress
                            and send personalized nudges to keep you on track.
                          </div>
                        </div>
                      </div>

                      <div>
                        <label className="text-[12px] font-semibold text-foreground mb-1.5 block">
                          🎯 My Learning Goals
                        </label>
                        <textarea
                          value={goals}
                          onChange={(e) => setGoals(e.target.value)}
                          placeholder="e.g. Complete 5 courses this quarter, improve quiz scores above 90%, master compliance training…"
                          rows={6}
                          maxLength={600}
                          className="w-full px-3 py-2.5 bg-secondary/40 border border-border/60 rounded-xl
                            text-[13px] text-foreground placeholder:text-muted-foreground/60
                            outline-none focus:border-violet-300 focus:bg-white focus:shadow-sm
                            transition-all resize-none"
                        />
                        <div className="text-right text-[10px] text-muted-foreground mt-1">
                          {goals.length}/600
                        </div>
                      </div>

                      <div className="rounded-xl border border-border/60 bg-secondary/30 px-4 py-3 text-[12px] text-muted-foreground">
                        💡 Your goals are shared with <strong className="text-foreground">Monitoring AI</strong> to generate
                        personalized growth suggestions, weekly check-ins, and course recommendations.
                      </div>
                    </div>
                  )}

                  {/* ── SAVED TAB ── */}
                  {tab === "saved" && (
                    <div className="space-y-4">
                      <div className="text-[12px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                        Downloaded Courses
                      </div>
                      {savedCourses.length === 0 ? (
                        <div className="text-[13px] text-muted-foreground text-center py-6">
                          No courses downloaded yet.
                        </div>
                      ) : (
                        savedCourses.map((c) => (
                          <div key={c.id} className="bg-card border border-border/60 rounded-xl p-4">
                            <div className="text-[10px] font-bold text-saffron uppercase mb-1">{c.department}</div>
                            <div className="text-[14px] font-bold text-foreground leading-tight mb-2">{c.title}</div>
                            <div className="text-[11px] text-muted-foreground mb-3">
                              Generated: {new Date(c.generated_at).toLocaleDateString()}
                            </div>
                            <button
                              onClick={() => {
                                try {
                                  const htmlStr = decodeURIComponent(escape(window.atob(c.htmlContent)));
                                  const newWindow = window.open("", "_blank");
                                  if (newWindow) {
                                    newWindow.document.write(htmlStr);
                                    newWindow.document.close();
                                  } else {
                                    alert("Please allow popups to view the course HTML.");
                                  }
                                } catch (e) {
                                  console.error("View failed", e);
                                }
                              }}
                              className="text-[12px] font-semibold text-nd-blue border border-nd-blue/30 bg-nd-blue/5 px-3 py-1.5 rounded-lg hover:bg-nd-blue/10 transition"
                            >
                              View Course HTML
                            </button>
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* ── Footer ── */}
            <div className="px-6 py-4 border-t border-border/50 flex gap-3 flex-shrink-0 bg-white">
              <button
                onClick={onClose}
                className="flex-1 py-2.5 rounded-xl border border-border/60 text-[13px]
                  font-semibold text-muted-foreground hover:bg-secondary/60 transition-all"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex-1 py-2.5 rounded-xl bg-gradient-to-r from-saffron to-gold
                  text-white text-[13px] font-semibold shadow-sm
                  hover:shadow-md hover:-translate-y-0.5 active:translate-y-0
                  transition-all duration-200 disabled:opacity-60 disabled:cursor-not-allowed
                  flex items-center justify-center gap-2"
              >
                {saving ? (
                  <>
                    <span className="w-3 h-3 rounded-full border-2 border-white/40 border-t-white animate-spin" />
                    Saving…
                  </>
                ) : saved ? (
                  <>✅ Saved!</>
                ) : (
                  <>💾 Save Profile</>
                )}
              </button>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
};

export default UserProfilePanel;