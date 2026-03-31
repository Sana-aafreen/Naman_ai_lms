import React, { useState, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/hooks/use-toast";

interface Leave {
  Leave_ID: string;
  User_ID: string;
  User_Name: string;
  Department: string;
  Leave_Type: string;
  From_Date: string;
  To_Date: string;
  Days: string;
  Reason: string;
  Status: string;
  Requested_Date: string;
  Approved_By: string;
  Approval_Date: string;
  Comments: string;
}

const LeaveManagement: React.FC = () => {
  const { user } = useAuth();
  const { toast } = useToast();
  const [leaves, setLeaves] = useState<Leave[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [approvalComment, setApprovalComment] = useState("");
  const [selectedLeaveId, setSelectedLeaveId] = useState<string | null>(null);
  const [approvalAction, setApprovalAction] = useState<"approve" | "reject" | null>(null);

  // Form state
  const [formData, setFormData] = useState({
    leaveType: "Casual",
    fromDate: "",
    toDate: "",
    days: 0,
    reason: "",
  });

  // Calculate days when dates change
  useEffect(() => {
    if (formData.fromDate && formData.toDate) {
      const from = new Date(formData.fromDate);
      const to = new Date(formData.toDate);
      const daysDiff = Math.ceil((to.getTime() - from.getTime()) / (1000 * 60 * 60 * 24)) + 1;
      setFormData(prev => ({ ...prev, days: daysDiff > 0 ? daysDiff : 0 }));
    }
  }, [formData.fromDate, formData.toDate]);

  // Fetch leaves on component mount
  useEffect(() => {
    fetchLeaves();
  }, []);

  const fetchLeaves = async () => {
    setLoading(true);
    try {
      const response = await fetch(
        `http://localhost:5000/api/leaves?userId=${user?.id}&department=${user?.department}&role=${user?.role}`
      );
      const data = await response.json();
      setLeaves(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Error fetching leaves:", error);
      toast({
        title: "Error",
        description: "Failed to load leaves",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitLeave = async () => {
    if (!formData.leaveType || !formData.fromDate || !formData.toDate || !formData.reason) {
      toast({
        title: "Missing Fields",
        description: "Please fill in all fields",
        variant: "destructive",
      });
      return;
    }

    setSubmitting(true);
    try {
      const response = await fetch("http://localhost:5000/api/leaves", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          userId: user?.id,
          userName: user?.name,
          department: user?.department,
          leaveType: formData.leaveType,
          fromDate: formData.fromDate,
          toDate: formData.toDate,
          days: formData.days,
          reason: formData.reason,
        }),
      });

      const data = await response.json();
      if (data.success) {
        toast({
          title: "Success",
          description: "Leave request submitted successfully",
        });
        setFormData({
          leaveType: "Casual",
          fromDate: "",
          toDate: "",
          days: 0,
          reason: "",
        });
        fetchLeaves();
      } else {
        toast({
          title: "Error",
          description: data.error || "Failed to submit leave request",
          variant: "destructive",
        });
      }
    } catch (error) {
      console.error("Error submitting leave:", error);
      toast({
        title: "Error",
        description: "Failed to submit leave request",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleApprovalAction = async (leaveId: string, action: "approve" | "reject") => {
    setSubmitting(true);
    try {
      const response = await fetch(`http://localhost:5000/api/leaves/${leaveId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action,
          approvedBy: user?.name,
          comments: approvalComment,
        }),
      });

      const data = await response.json();
      if (data.success) {
        toast({
          title: "Success",
          description: `Leave request ${action === "approve" ? "approved" : "rejected"}`,
        });
        setApprovalComment("");
        setSelectedLeaveId(null);
        setApprovalAction(null);
        fetchLeaves();
      } else {
        toast({
          title: "Error",
          description: data.error || "Failed to update leave status",
          variant: "destructive",
        });
      }
    } catch (error) {
      console.error("Error updating leave:", error);
      toast({
        title: "Error",
        description: "Failed to update leave status",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "Approved":
        return "bg-nd-green-light text-nd-green";
      case "Rejected":
        return "bg-red-100 text-red-700";
      case "Pending":
        return "bg-gold-light text-gold";
      default:
        return "bg-secondary text-muted-foreground";
    }
  };

  const isManager = user?.role === "Manager";
  const pendingCount = leaves.filter(l => l.Status === "Pending").length;

  return (
    <div>
      <div className="mb-5">
        <div className="text-[11px] text-muted-foreground mb-2">
          Home <span className="text-saffron">/ Leave Management</span>
        </div>
        <h1 className="text-xl font-bold mb-1">Leave Management</h1>
        <p className="text-[13px] text-muted-foreground">
          {isManager
            ? `Manage leave requests from your team (${pendingCount} pending)`
            : "Apply for leaves and track your requests"}
        </p>
      </div>

      {!isManager && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3.5 mb-5">
          {/* Leave Request Form - Only for Employees */}
          <div className="bg-card border border-border rounded-xl p-[18px]">
            <div className="text-sm font-semibold mb-3.5">📝 Apply for Leave</div>
            <div className="grid grid-cols-2 gap-3 mb-3">
              <div>
                <label className="text-xs text-muted-foreground block mb-1">Leave Type</label>
                <select
                  value={formData.leaveType}
                  onChange={(e) => setFormData({ ...formData, leaveType: e.target.value })}
                  className="w-full px-3 py-2 border-[1.5px] border-border rounded-lg text-[13px] bg-card outline-none focus:border-saffron"
                >
                  <option>Casual</option>
                  <option>Sick</option>
                  <option>Earned</option>
                  <option>Festival</option>
                  <option>Emergency</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-muted-foreground block mb-1">From Date</label>
                <input
                  type="date"
                  value={formData.fromDate}
                  onChange={(e) => setFormData({ ...formData, fromDate: e.target.value })}
                  className="w-full px-3 py-2 border-[1.5px] border-border rounded-lg text-[13px] bg-card outline-none focus:border-saffron"
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground block mb-1">To Date</label>
                <input
                  type="date"
                  value={formData.toDate}
                  onChange={(e) => setFormData({ ...formData, toDate: e.target.value })}
                  className="w-full px-3 py-2 border-[1.5px] border-border rounded-lg text-[13px] bg-card outline-none focus:border-saffron"
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground block mb-1">No. of Days</label>
                <input
                  type="text"
                  value={formData.days}
                  readOnly
                  className="w-full px-3 py-2 border-[1.5px] border-border rounded-lg text-[13px] bg-secondary text-muted-foreground"
                />
              </div>
            </div>
            <div className="mb-3">
              <label className="text-xs text-muted-foreground block mb-1">Reason</label>
              <textarea
                rows={3}
                placeholder="Brief reason for leave…"
                value={formData.reason}
                onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
                className="w-full px-3 py-2 border-[1.5px] border-border rounded-lg text-[13px] bg-card outline-none focus:border-saffron resize-y"
              />
            </div>
            <button
              onClick={handleSubmitLeave}
              disabled={submitting}
              className="px-5 py-2 bg-saffron text-primary-foreground rounded-lg text-[13px] font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {submitting ? "Submitting..." : "Submit Leave Request"}
            </button>
          </div>

          {/* Leave History/Status */}
          <div className="bg-card border border-border rounded-xl p-[18px]">
            <div className="text-sm font-semibold mb-3.5">📊 My Leave Requests</div>
            {loading ? (
              <div className="text-center py-4 text-muted-foreground">Loading...</div>
            ) : leaves.length === 0 ? (
              <div className="text-center py-4 text-muted-foreground">No leave requests yet</div>
            ) : (
              <div className="space-y-2 max-h-[300px] overflow-y-auto">
                {leaves.map((leave) => (
                  <div key={leave.Leave_ID} className="p-2.5 bg-secondary rounded-lg border border-border">
                    <div className="flex justify-between items-start mb-1">
                      <div className="font-semibold text-[13px]">{leave.Leave_Type}</div>
                      <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${getStatusColor(leave.Status)}`}>
                        {leave.Status}
                      </span>
                    </div>
                    <div className="text-[11px] text-muted-foreground">
                      {leave.From_Date} to {leave.To_Date} ({leave.Days} days)
                    </div>
                    {leave.Approved_By && (
                      <div className="text-[11px] text-muted-foreground mt-1">
                        Approved by: {leave.Approved_By}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Manager Panel - Pending Leaves to Approve */}
      {isManager && (
        <div className="bg-card border border-border rounded-xl p-[18px]">
          <div className="text-sm font-semibold mb-3.5">✋ Pending Approval Requests</div>
          {loading ? (
            <div className="text-center py-4 text-muted-foreground">Loading...</div>
          ) : leaves.length === 0 ? (
            <div className="text-center py-4 text-muted-foreground">No pending leave requests from your team</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-[13px]">
                <thead>
                  <tr className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide">
                    <th className="text-left p-2.5 bg-secondary rounded-l-md">Employee</th>
                    <th className="text-left p-2.5 bg-secondary">Leave Type</th>
                    <th className="text-left p-2.5 bg-secondary">Dates</th>
                    <th className="text-left p-2.5 bg-secondary">Days</th>
                    <th className="text-left p-2.5 bg-secondary">Status</th>
                    <th className="text-left p-2.5 bg-secondary rounded-r-md">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {leaves.map((leave) => (
                    <tr key={leave.Leave_ID} className="border-b border-border last:border-b-0 hover:bg-secondary/30">
                      <td className="p-2.5">{leave.User_Name}</td>
                      <td className="p-2.5">{leave.Leave_Type}</td>
                      <td className="p-2.5 text-[12px]">
                        {leave.From_Date} to {leave.To_Date}
                      </td>
                      <td className="p-2.5">{leave.Days}</td>
                      <td className="p-2.5">
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${getStatusColor(leave.Status)}`}>
                          {leave.Status}
                        </span>
                      </td>
                      <td className="p-2.5">
                        <div className="flex gap-2">
                          <button
                            onClick={() => {
                              setSelectedLeaveId(leave.Leave_ID);
                              setApprovalAction("approve");
                            }}
                            className="px-2 py-1 bg-nd-green-light text-nd-green rounded text-[11px] font-semibold hover:opacity-80 cursor-pointer"
                          >
                            Approve
                          </button>
                          <button
                            onClick={() => {
                              setSelectedLeaveId(leave.Leave_ID);
                              setApprovalAction("reject");
                            }}
                            className="px-2 py-1 bg-red-100 text-red-700 rounded text-[11px] font-semibold hover:opacity-80 cursor-pointer"
                          >
                            Reject
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Approval Dialog */}
          {selectedLeaveId && approvalAction && (
            <div className="mt-4 p-4 bg-secondary rounded-lg border border-border">
              <div className="mb-3">
                <p className="font-semibold text-[13px]">
                  {approvalAction === "approve" ? "Approve" : "Reject"} Leave Request
                </p>
                <p className="text-[12px] text-muted-foreground mt-1">
                  {leaves.find(l => l.Leave_ID === selectedLeaveId)?.User_Name} -{" "}
                  {leaves.find(l => l.Leave_ID === selectedLeaveId)?.Leave_Type}
                </p>
              </div>
              <div className="mb-3">
                <label className="text-xs font-medium block mb-2">
                  {approvalAction === "approve" ? "Comments (optional)" : "Reason (required)"}
                </label>
                <textarea
                  rows={2}
                  placeholder={approvalAction === "approve" ? "Add approval comments…" : "Reason for rejection…"}
                  value={approvalComment}
                  onChange={(e) => setApprovalComment(e.target.value)}
                  className="w-full px-3 py-2 border border-border rounded-lg text-[13px] focus:border-saffron outline-none resize-y"
                />
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    setSelectedLeaveId(null);
                    setApprovalAction(null);
                    setApprovalComment("");
                  }}
                  className="px-4 py-1.5 border border-border rounded-lg text-[13px] font-semibold hover:bg-secondary cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleApprovalAction(selectedLeaveId, approvalAction)}
                  disabled={submitting || (approvalAction === "reject" && !approvalComment)}
                  className={`px-4 py-1.5 text-white rounded-lg text-[13px] font-semibold cursor-pointer disabled:opacity-50 ${
                    approvalAction === "approve"
                      ? "bg-nd-green hover:bg-nd-green/90"
                      : "bg-red-600 hover:bg-red-700"
                  }`}
                >
                  {submitting ? "Processing..." : approvalAction === "approve" ? "Approve" : "Reject"}
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default LeaveManagement;
