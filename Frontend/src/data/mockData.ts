export const DEPARTMENTS = ["Sales", "Ops", "Sewa", "Puja & Pandit", "Logistics", "Content & SEO", "Tech & Stream", "Finance"];

export const COURSES = [
  { id: 1, title: "Sankalp Confirmation Protocol", dept: "Sewa", dur: "4 hrs", level: "Intermediate", progress: 72, status: "In Progress", icon: "🙏", bg: "linear-gradient(135deg, hsl(24 88% 44%), hsl(37 86% 38%))" },
  { id: 2, title: "CRM & WhatsApp Sales Ops", dept: "Sales", dur: "6 hrs", level: "Advanced", progress: 45, status: "In Progress", icon: "📱", bg: "linear-gradient(135deg, hsl(220 72% 41%), hsl(213 73% 22%))" },
  { id: 3, title: "Empathetic Communication for Devotees", dept: "Sewa", dur: "3 hrs", level: "Beginner", progress: 90, status: "In Progress", icon: "💛", bg: "linear-gradient(135deg, hsl(37 86% 38%), hsl(24 88% 44%))" },
  { id: 4, title: "Temple Protocols & Entry Rules", dept: "Ops", dur: "5 hrs", level: "Beginner", progress: 20, status: "Started", icon: "🛕", bg: "linear-gradient(135deg, hsl(0 60% 30%), hsl(24 88% 44%))" },
  { id: 5, title: "Live Puja Streaming Setup", dept: "Tech & Stream", dur: "4 hrs", level: "Advanced", progress: 100, status: "Completed", icon: "📹", bg: "linear-gradient(135deg, hsl(163 82% 23%), hsl(220 72% 41%))" },
  { id: 6, title: "Char Dham Yatra Ops 2025", dept: "Ops", dur: "8 hrs", level: "Advanced", progress: 0, status: "Not Started", icon: "🏔️", bg: "linear-gradient(135deg, hsl(213 73% 22%), hsl(240 30% 14%))" },
  { id: 7, title: "GST & Compliance Basics", dept: "Finance", dur: "3 hrs", level: "Intermediate", progress: 100, status: "Completed", icon: "📊", bg: "linear-gradient(135deg, hsl(120 38% 30%), hsl(163 82% 23%))" },
  { id: 8, title: "Shraddha Box Packaging Standards", dept: "Logistics", dur: "2 hrs", level: "Beginner", progress: 100, status: "Completed", icon: "📦", bg: "linear-gradient(135deg, hsl(37 86% 38%), hsl(30 89% 62%))" },
  { id: 9, title: "SEO for Temple Pages", dept: "Content & SEO", dur: "4 hrs", level: "Intermediate", progress: 60, status: "In Progress", icon: "🔍", bg: "linear-gradient(135deg, hsl(220 72% 41%), hsl(163 82% 23%))" },
  { id: 10, title: "Pandit Assignment & Briefing", dept: "Puja & Pandit", dur: "3 hrs", level: "Intermediate", progress: 100, status: "Completed", icon: "🔱", bg: "linear-gradient(135deg, hsl(24 88% 44%), hsl(0 60% 30%))" },
  { id: 11, title: "VIP Darshan Day-of Execution", dept: "Ops", dur: "5 hrs", level: "Advanced", progress: 100, status: "Completed", icon: "⭐", bg: "linear-gradient(135deg, hsl(37 86% 38%), hsl(24 88% 44%))" },
  { id: 12, title: "Revenue Reconciliation Process", dept: "Finance", dur: "3 hrs", level: "Advanced", progress: 30, status: "In Progress", icon: "💰", bg: "linear-gradient(135deg, hsl(120 38% 30%), hsl(37 86% 38%))" },
];

export const SOPS: Record<string, { title: string; steps: string[] }[]> = {
  Sales: [
    { title: "Inbound Lead Handling", steps: ["Log lead in CRM within 5 min.", "Tag priority: P1 (within 7 days), P2 (7–30 days), P3 (exploratory).", "Send WhatsApp greeting within 15 min.", "Qualification call: within 2 hrs (P1) or 24 hrs (P2).", "Send customized quote with payment link.", "Follow-up cadence: +6h, +24h, +48h.", "On payment: trigger confirmation, hand off to Ops & Sewa."] },
    { title: "Upsell & Package Upgrade", steps: ["Note upsell signals during qualification.", "Present upgrades: Shraddha Box, Live Puja, helicopter, hotel.", "Use spiritual value framing — not discount pushing.", "Log in CRM. Update order value. Notify Ops."] },
  ],
  Ops: [
    { title: "VIP Darshan Day-of Execution", steps: ["Pre-day call: confirm arrival, pickup, dress code.", "1 hr before: confirm slot with on-ground partner.", "Meet devotee, verify booking ID, escort to sanctum.", "Log all exceptions immediately.", "Post-darshan: escort, confirm prasad, share feedback form."] },
    { title: "Yatra Package Logistics", steps: ["15 days before: confirm helicopter/hotel.", "3 days before: reconfirm slots, have backup.", "Confirm hotel check-in, brief local guide.", "Assign WhatsApp group, daily check-in.", "On return: collect feedback, log partner performance."] },
  ],
  Sewa: [
    { title: "Puja Sankalp Confirmation", steps: ["Within 24 hrs: schedule Sewa call (8–11 AM).", "Confirm: devotee name, gotra, names, date/time, address, live vs recorded.", "For uncommon names: ask for phonetic spelling.", "Repeat all details back, update sankalp form.", "24 hrs before: send WhatsApp reminder with link."] },
    { title: "Complaint & Grievance Handling", steps: ["Acknowledge within 1 hr.", "Classify: P1 → escalate immediately. P2 → resolve within 48 hrs.", "P1: re-service or full refund. P2: ETA + discount.", "Log: category, root cause, resolution, time."] },
  ],
  "Puja & Pandit": [
    { title: "Pandit Assignment & Briefing", steps: ["Match Pandit using expertise matrix.", "Share sankalp details 24 hrs before.", "1 hr before: Pandit confirms setup."] },
    { title: "Live Puja Streaming Protocol", steps: ["30 min before: test camera, audio, streaming link.", "Open with devotee name + gotra on stream.", "Monitor quality. If drop > 30s, switch to recorded.", "End with Aarti + prasad blessing. Share recording within 2 hrs."] },
  ],
  Logistics: [
    { title: "Dispatch & Courier Handoff", steps: ["Receive dispatch sheet from Puja team.", "Seal box, apply waterproof label, mark FRAGILE.", "Select courier based on pin code.", "Share AWB tracking within 4 hrs."] },
    { title: "Delivery Exception Handling", steps: ["7-day alert: check tracking, contact courier.", "Address issue: correct and re-dispatch within 24 hrs.", "Damaged: apologise, re-dispatch within 48 hrs.", "Unresolved > 10 days: escalate."] },
  ],
  "Content & SEO": [
    { title: "Temple Page Content Creation", steps: ["Research: history, timings, dress code, entry rules.", "Draft: About → Timings → How Naman Helps → Booking → FAQ.", "Spiritual accuracy review.", "SEO pass: keywords, meta title ≤ 60 chars.", "Publish & internal link."] },
  ],
  "Tech & Stream": [
    { title: "Live Darshan Stream Setup", steps: ["1 hr before: verify stream source, test embed.", "5 min before: activate, update page to LIVE.", "Monitor quality and viewer count.", "If drop > 10 min: notify, reschedule."] },
    { title: "Booking System Health Check", steps: ["Morning: verify booking → CRM → WhatsApp pipeline.", "Place 1 test booking, confirm WhatsApp arrives.", "Check payment gateway failure rate.", "Ensure UPI, cards, net banking functional."] },
  ],
  Finance: [
    { title: "Revenue Reconciliation", steps: ["Morning: reconcile gateway vs booking system.", "Flag mismatched payments.", "GST invoicing: SAC 999559, email within 24 hrs.", "Refunds: original method, 5–7 working days."] },
    { title: "Pandit & Partner Payouts", steps: ["Fee released after puja completion confirmed.", "Pandit: UPI/NEFT within 24 hrs. Partners: weekly Monday.", "Deduct TDS (10%) for > ₹30,000/year.", "Disputes: reviewed within 48 hrs."] },
  ],
};

export const SOP_PDFS: Record<
  string,
  { title: string; href: string }[]
> = {
  HR: [
    {
      title: "HR SOP Handbook",
      href: "/SOPs/hr-sop.pdf",
    },
  ],
  Marketing: [
    {
      title: "Marketing SOP Handbook",
      href: "/SOPs/marketing-sop.pdf",
    },
  ],
  Operations: [
    {
      title: "Operations SOP Handbook",
      href: "/SOPs/operations-sop.pdf",
    },
  ],
};

export const KANBAN_DATA: Record<string, { title: string; dept: string; due: string; who: string }[]> = {
  Backlog: [
    { title: "Kedarnath Season Briefing Deck", dept: "Ops", due: "Apr 5", who: "AM" },
    { title: "GST Invoice Template Revamp", dept: "Finance", due: "Apr 10", who: "AG" },
    { title: "Puja Video Archive Setup", dept: "Tech", due: "Apr 15", who: "DC" },
  ],
  "In Progress": [
    { title: "Char Dham SOP Update 2025", dept: "Ops", due: "Mar 31", who: "AM" },
    { title: "WhatsApp Template Library", dept: "Sales", due: "Apr 3", who: "RV" },
    { title: "Temple Page — Somnath", dept: "Content", due: "Apr 7", who: "MI" },
  ],
  Review: [
    { title: "Mahashivratri Post-event Report", dept: "Ops", due: "Mar 28", who: "AN" },
    { title: "Shraddha Box V2 Design", dept: "Logistics", due: "Mar 29", who: "SR" },
  ],
  Done: [
    { title: "Holi Campaign WhatsApp Blasts", dept: "Content", due: "Mar 13", who: "MI" },
    { title: "Booking Form UPI Bug Fix", dept: "Tech", due: "Mar 20", who: "DC" },
    { title: "Q4 Reconciliation Report", dept: "Finance", due: "Mar 22", who: "AG" },
  ],
};

export const AI_RESPONSES: Record<string, string> = {
  "vip darshan sop": "The VIP Darshan SOP has 5 steps:\n1. Pre-day call to devotee (dress code, restricted items, pickup point).\n2. Confirm slot with on-ground partner 1 hr before.\n3. Meet devotee, verify booking ID, escort to sanctum.\n4. Log all exceptions (delays, mobility issues) immediately.\n5. File ops completion report within 2 hrs post-darshan. 🙏",
  "insurance claim": "To file a health insurance claim:\n1. Visit a network hospital (cashless) or any hospital (reimbursement).\n2. For cashless: show your NamanDarshan health card at TPA desk.\n3. For reimbursement: collect all bills, discharge summary, prescriptions.\n4. Submit claim form + documents to HR within 15 days.\n5. Settlement in 7–14 working days. 💊",
  "recommend courses": "Based on your profile (Sewa dept, 87% score), I recommend:\n1. ✅ Complete 'Empathetic Communication' — you're at 90%!\n2. 📚 Start 'CRM & WhatsApp Sales Ops' — useful for cross-dept support.\n3. 🛕 'Temple Protocols & Entry Rules' — helps answer devotee questions.\nWant me to enroll you in any of these?",
  "char dham": "Char Dham Season 2025 dates:\n• Kedarnath opens: May 2, 2025\n• Badrinath opens: May 4, 2025\n• Gangotri opens: May 1, 2025\n• Yamunotri opens: May 1, 2025\nAll shrines close in November. Book helicopter slots 45 days in advance! 🚁",
  default: "I can help with SOPs, course guidance, temple protocols, HR policies, and more. Try asking:\n• 'What is the VIP Darshan SOP?'\n• 'How do I file an insurance claim?'\n• 'Recommend courses for me'\n• 'Char Dham season dates 2025'\nJai Shri Ram 🙏",
};

export const HOLIDAYS = [
  { date: "Jan 14", name: "Makar Sankranti", type: "Festival" },
  { date: "Jan 26", name: "Republic Day", type: "National" },
  { date: "Feb 26", name: "Mahashivratri", type: "Festival" },
  { date: "Mar 13", name: "Holi", type: "Festival" },
  { date: "Apr 6", name: "Ram Navami", type: "Festival" },
  { date: "Apr 14", name: "Baisakhi / Ambedkar Jayanti", type: "National" },
  { date: "Aug 15", name: "Independence Day", type: "National" },
  { date: "Aug 16", name: "Janmashtami", type: "Festival" },
  { date: "Oct 2", name: "Gandhi Jayanti", type: "National" },
  { date: "Oct 2–5", name: "Navratri (early close)", type: "Festival" },
  { date: "Oct 23", name: "Dussehra", type: "Festival" },
  { date: "Nov 1–3", name: "Diwali", type: "Festival" },
  { date: "Dec 25", name: "Christmas", type: "Optional" },
];
