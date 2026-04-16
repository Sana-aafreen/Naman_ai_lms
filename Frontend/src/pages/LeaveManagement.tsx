import React, { useEffect, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/hooks/use-toast";
import { apiGet, apiPatch, apiPost } from "@/lib/api";
import { 
  Calendar as CalendarIcon, 
  ChevronRight, 
  Clock, 
  ShieldCheck, 
  AlertCircle,
  CheckCircle2,
  XCircle,
  FileText,
  Plus,
  ArrowRight,
  Info
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface Leave {
  id: number;
  employee_id: number;
  employee_name: string;
  department: string;
  leave_type: string;
  start_date: string;
  end_date: string;
  reason: string;
  status: "pending" | "approved" | "rejected";
  applied_at: string;
  approved_by?: string;
  comments?: string;
}

interface LeaveMutationResponse {
  success: boolean;
  error?: string;
  message?: string;
}

const statusBadge = (status: string) => {
  const map: Record<string, string> = {
    pending: "bg-amber-50 text-amber-600 border-amber-100",
    approved: "bg-emerald-50 text-emerald-600 border-emerald-100",
    rejected: "bg-rose-50 text-rose-600 border-rose-100",
  };
  return map[status] ?? "bg-slate-50 text-slate-400 border-slate-100";
};

const statusLabel = (status: string) => {
  const map: Record<string, string> = {
    pending: "In Review",
    approved: "Authorized",
    rejected: "Declined",
  };
  return map[status] ?? status;
};

const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4, delay, ease: "easeOut" } as const,
});

const LeaveManagement: React.FC = () => {
  const { user, hasRole } = useAuth();
  const { toast } = useToast();

  const [leaves, setLeaves] = useState<Leave[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [approvalLeaveId, setApprovalLeaveId] = useState<number | null>(null);
  const [approvalAction, setApprovalAction] = useState<"approve" | "reject" | null>(null);
  const [approvalComment, setApprovalComment] = useState("");
  const [formData, setFormData] = useState({
    leaveType: "Casual",
    fromDate: "",
    toDate: "",
    days: 0,
    reason: "",
  });

  const canApprove = hasRole("Manager", "Admin");

  useEffect(() => {
    if (formData.fromDate && formData.toDate) {
      const diff =
        Math.ceil(
          (new Date(formData.toDate).getTime() - new Date(formData.fromDate).getTime()) /
            86_400_000,
        ) + 1;
      setFormData((prev) => ({ ...prev, days: diff > 0 ? diff : 0 }));
    }
  }, [formData.fromDate, formData.toDate]);

  const fetchLeaves = React.useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiGet<Leave[]>(
        `/api/leaves?userId=${user?.id ?? ""}&department=${user?.department ?? ""}&role=${user?.role ?? ""}`,
      );
      setLeaves(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, [user?.id, user?.department, user?.role]);

  useEffect(() => {
    void fetchLeaves();
  }, [fetchLeaves]);

  const handleSubmitLeave = async () => {
    if (!user?.id || submitting) return;

    if (!formData.leaveType || !formData.fromDate || !formData.toDate || !formData.reason) {
      toast({
        title: "Incomplete Request",
        description: "Please fulfill all required fields before submission.",
        variant: "destructive",
      });
      return;
    }

    setSubmitting(true);
    try {
      const data = await apiPost<LeaveMutationResponse>("/api/leaves", {
        employee_id: user.id,
        leave_type: formData.leaveType,
        start_date: formData.fromDate,
        end_date: formData.toDate,
        reason: formData.reason,
      });

      if (data.success) {
        toast({ title: "Request Submitted", description: "Leave request has been archived for institutional review." });
        setFormData({ leaveType: "Casual", fromDate: "", toDate: "", days: 0, reason: "" });
        void fetchLeaves();
      }
    } finally {
      setSubmitting(false);
    }
  };

  const openApproval = (id: number, action: "approve" | "reject") => {
    setApprovalLeaveId(id);
    setApprovalAction(action);
    setApprovalComment("");
  };

  const confirmApproval = async () => {
    if (!approvalLeaveId || !approvalAction) return;

    setSubmitting(true);
    try {
      const data = await apiPatch<LeaveMutationResponse>(`/api/leaves/${approvalLeaveId}`, {
        action: approvalAction,
        approvedBy: user?.name,
        comments: approvalComment,
      });

      if (data.success) {
        toast({ title: "Directive Processed", description: `Leave request has been ${approvalAction}d.` });
        setApprovalLeaveId(null);
        setApprovalAction(null);
        void fetchLeaves();
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="pb-20 max-w-[1280px] mx-auto px-6">
      <header className="mb-12 pt-6">
        <div className="text-[10px] text-slate-400 font-bold uppercase tracking-[0.25em] mb-6 flex items-center gap-2">
          Operations <ChevronRight className="w-3 h-3" /> <span className="text-slate-800 font-black">Resource Availability</span>
        </div>
        <div>
          <h1 className="text-4xl font-bold text-slate-900 mb-4 tracking-tight">Deployment & Availability</h1>
          <p className="text-lg text-slate-500 font-medium max-w-2xl leading-relaxed">
            {hasRole("Admin")
              ? "Comprehensive organizational oversight of personnel movement and deployment directives."
              : hasRole("Manager")
                ? "Departmental oversight and authorization of tactical leave allocations."
                : "Manage your leave authorizations and track historical deployment data."}
          </p>
        </div>
      </header>

      <div className="grid grid-cols-1 xl:grid-cols-[380px_1fr] gap-10">
        <motion.div {...fadeUp(0.05)} className="bg-white border border-slate-100 rounded-3xl p-10 relative overflow-hidden h-fit shadow-sm">
          <div className="absolute top-0 right-0 w-32 h-32 bg-amber-50/10 blur-3xl rounded-full" />
          <div className="flex items-center justify-between mb-10">
            <h3 className="text-xl font-bold text-slate-900 tracking-tight">Request Deployment</h3>
            <Plus className="w-5 h-5 text-slate-200" />
          </div>

          <div className="space-y-6">
            <div>
              <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-3 block">Leave Category</label>
              <select
                className="w-full bg-slate-50/50 border border-slate-100 rounded-xl px-5 py-3.5 text-sm font-semibold text-slate-800 focus:bg-white focus:border-amber-200 transition-all outline-none appearance-none"
                value={formData.leaveType}
                onChange={(e) => setFormData((prev) => ({ ...prev, leaveType: e.target.value }))}
              >
                {["Casual", "Sick", "Earned", "Optional"].map((type) => (
                  <option key={type} value={type}>{type} Leave</option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-3 block">Commence On</label>
                <input
                  type="date"
                  className="w-full bg-slate-50/50 border border-slate-100 rounded-xl px-5 py-3.5 text-sm font-semibold text-slate-800 focus:bg-white focus:border-amber-200 transition-all outline-none"
                  value={formData.fromDate}
                  onChange={(e) => setFormData((prev) => ({ ...prev, fromDate: e.target.value }))}
                />
              </div>
              <div>
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-3 block">Terminate On</label>
                <input
                  type="date"
                  className="w-full bg-slate-50/50 border border-slate-100 rounded-xl px-5 py-3.5 text-sm font-semibold text-slate-800 focus:bg-white focus:border-amber-200 transition-all outline-none"
                  value={formData.toDate}
                  onChange={(e) => setFormData((prev) => ({ ...prev, toDate: e.target.value }))}
                />
              </div>
            </div>

            {formData.days > 0 && (
              <div className="flex items-center gap-2.5 p-4 bg-slate-50 border border-slate-100 rounded-xl text-[11px] font-bold text-slate-600">
                <Info className="w-4 h-4 text-slate-400" /> Calculated Period: {formData.days} Day{formData.days > 1 ? "s" : ""}
              </div>
            )}

            <div>
              <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-3 block">Objective / Reason</label>
              <textarea
                rows={4}
                className="w-full bg-slate-50/50 border border-slate-100 rounded-xl px-5 py-3.5 text-sm font-medium text-slate-600 focus:bg-white focus:border-amber-200 transition-all outline-none resize-none"
                placeholder="Context for your leave request..."
                value={formData.reason}
                onChange={(e) => setFormData((prev) => ({ ...prev, reason: e.target.value }))}
              />
            </div>

            <button
              disabled={submitting}
              onClick={handleSubmitLeave}
              className="enterprise-btn-primary w-full py-4 text-[11px] font-bold uppercase tracking-widest flex items-center justify-center gap-2 shadow-none hover:shadow-lg transition-all"
            >
              {submitting ? "Transmitting..." : "Submit Request"}
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </motion.div>

        <motion.div {...fadeUp(0.1)} className="bg-white border border-slate-100 rounded-3xl p-10 relative overflow-hidden shadow-sm">
          <div className="flex items-center justify-between mb-10">
            <h3 className="text-xl font-bold text-slate-900 tracking-tight">
              {canApprove ? "Personnel Movement Logs" : "Your Leave Archives"}
            </h3>
            <FileText className="w-5 h-5 text-slate-200" />
          </div>

          {loading ? (
            <div className="py-24 flex flex-col items-center gap-6">
              <div className="w-10 h-10 border-4 border-slate-100 border-t-[#FF7033] rounded-full animate-spin" />
              <div className="text-[11px] font-bold text-slate-400 uppercase tracking-widest">Loading Logs...</div>
            </div>
          ) : leaves.length === 0 ? (
            <div className="py-24 text-center border-2 border-dashed border-slate-50 rounded-3xl bg-slate-50/20">
              <AlertCircle className="w-10 h-10 text-slate-100 mx-auto mb-4" />
              <p className="text-[12px] text-slate-400 font-medium italic">No historical movement identified.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-50">
                    <th className="pb-5 text-left text-[11px] font-bold text-slate-400 uppercase tracking-widest">{canApprove ? "Personnel" : "Category"}</th>
                    <th className="pb-5 text-left text-[11px] font-bold text-slate-400 uppercase tracking-widest">Duration</th>
                    <th className="pb-5 text-left text-[11px] font-bold text-slate-400 uppercase tracking-widest">Objective</th>
                    <th className="pb-5 text-left text-[11px] font-bold text-slate-400 uppercase tracking-widest">Authorization</th>
                    {canApprove && <th className="pb-5 text-right text-[11px] font-bold text-slate-400 uppercase tracking-widest">Directives</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50/50">
                  {leaves.map((leave) => (
                    <tr key={leave.id} className="group hover:bg-slate-50/50 transition-all">
                      <td className="py-7">
                        <div className="font-bold text-[15px] text-slate-800 group-hover:text-amber-600 transition-colors tracking-tight">
                          {canApprove ? leave.employee_name : `${leave.leave_type} Leave`}
                        </div>
                        {canApprove && (
                          <div className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mt-1">
                            {leave.department} · {leave.leave_type}
                          </div>
                        )}
                      </td>
                      <td className="py-7">
                        <div className="flex items-center gap-2.5 text-[12px] font-bold text-slate-700">
                           {leave.start_date}
                        </div>
                        <div className="flex items-center gap-2.5 text-[10px] text-slate-400 font-bold uppercase mt-1">
                           To: {leave.end_date}
                        </div>
                      </td>
                      <td className="py-7 max-w-[200px]">
                        <p className="text-[13px] font-medium text-slate-500 line-clamp-2">{leave.reason || "Validated objective."}</p>
                      </td>
                      <td className="py-7">
                        <div className={`inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg border text-[10px] font-bold uppercase tracking-widest shadow-sm ${statusBadge(leave.status)}`}>
                          {leave.status === 'approved' ? <CheckCircle2 className="w-3.5 h-3.5" /> : leave.status === 'rejected' ? <XCircle className="w-3.5 h-3.5" /> : <Clock className="w-3.5 h-3.5 text-amber-500" />}
                          {statusLabel(leave.status)}
                        </div>
                      </td>
                      {canApprove && (
                        <td className="py-7 text-right">
                          {leave.status === "pending" ? (
                            <div className="flex gap-2.5 justify-end">
                              <button
                                onClick={() => openApproval(leave.id, "approve")}
                                className="w-9 h-9 rounded-xl bg-emerald-50 text-emerald-600 border border-emerald-100 hover:bg-emerald-600 hover:text-white transition-all flex items-center justify-center shadow-sm"
                                title="Authorize"
                              >
                                <CheckCircle2 className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => openApproval(leave.id, "reject")}
                                className="w-9 h-9 rounded-xl bg-rose-50 text-rose-600 border border-rose-100 hover:bg-rose-600 hover:text-white transition-all flex items-center justify-center shadow-sm"
                                title="Decline"
                              >
                                <XCircle className="w-4 h-4" />
                              </button>
                            </div>
                          ) : (
                            <div className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">
                              {leave.approved_by ?? "Institutional System"}
                            </div>
                          )}
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </motion.div>
      </div>

      <AnimatePresence>
        {approvalLeaveId && (
          <div className="fixed inset-0 z-[120] flex items-center justify-center p-6">
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setApprovalLeaveId(null)} className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm" />
            <motion.div initial={{ scale: 0.95, y: 20, opacity: 0 }} animate={{ scale: 1, y: 0, opacity: 1 }} exit={{ scale: 0.95, y: 20, opacity: 0 }} className="bg-white rounded-[2rem] w-full max-w-md p-10 shadow-2xl relative z-10 border border-slate-100">
              <div className="flex items-center justify-between mb-8">
                 <h2 className="text-xl font-bold text-slate-900 tracking-tight">{approvalAction === 'approve' ? 'Authorize Directive' : 'Decline Directive'}</h2>
                 <ShieldCheck className={`w-6 h-6 ${approvalAction === 'approve' ? 'text-emerald-500' : 'text-rose-500'}`} />
              </div>
              
              <p className="text-[13px] text-slate-500 font-medium mb-8 leading-relaxed">
                Provide institutional commentary and finalize the operational directive for this movement record.
              </p>
              
              <textarea
                rows={4}
                className="w-full bg-slate-50/50 border border-slate-100 rounded-xl px-5 py-3.5 text-sm font-medium text-slate-600 focus:bg-white focus:border-amber-200 transition-all outline-none resize-none mb-8"
                placeholder="Institutional commentary (optional)..."
                value={approvalComment}
                onChange={(e) => setApprovalComment(e.target.value)}
              />
              
              <div className="flex gap-4">
                <button
                  onClick={() => setApprovalLeaveId(null)}
                  className="flex-1 py-3.5 rounded-xl border border-slate-100 text-slate-400 text-[11px] font-bold uppercase tracking-widest hover:bg-slate-50 transition-all"
                >
                  Abort
                </button>
                <button
                  disabled={submitting}
                  onClick={confirmApproval}
                  className={`flex-[2] py-3.5 rounded-xl text-[11px] font-bold uppercase tracking-widest text-white shadow-xl transition-all active:scale-[0.98] ${
                    approvalAction === "approve"
                      ? "bg-emerald-600 hover:bg-emerald-700 shadow-emerald-500/10"
                      : "bg-rose-600 hover:bg-rose-700 shadow-rose-500/10"
                  }`}
                >
                  {submitting ? "Processing..." : `Confirm ${approvalAction}`}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default LeaveManagement;
