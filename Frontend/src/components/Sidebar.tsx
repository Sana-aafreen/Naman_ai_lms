import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import UserProfilePanel from "@/components/UserProfilePanel";
import { 
  BarChart3, 
  BookOpen, 
  Briefcase, 
  Calendar, 
  ClipboardList, 
  GraduationCap, 
  Home, 
  LayoutDashboard, 
  Settings, 
  Sparkles,
  ChevronRight,
  PanelLeftClose,
  PanelLeft,
  CircleDot,
  Target
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface NavItem {
  id: string;
  icon: React.ReactNode;
  label: string;
  badge?: string;
  section: string;
  adminOnly?: boolean;
  managerOnly?: boolean;
  path: string;
}

const navItems: NavItem[] = [
  { id: "dashboard", icon: <Home className="w-[18px] h-[18px]" />, label: "Dashboard", section: "Main", path: "/dashboard" },
  { id: "courses", icon: <LayoutDashboard className="w-[18px] h-[18px]" />, label: "Strategic Courses", section: "Main", path: "/courses" },
  { id: "training", icon: <GraduationCap className="w-[18px] h-[18px]" />, label: "Resource Library", section: "Main", path: "/training" },
  { id: "progress", icon: <BarChart3 className="w-[18px] h-[18px]" />, label: "Performance Analytics", section: "Main", path: "/progress" },
  { id: "kpi", icon: <Target className="w-[18px] h-[18px]" />, label: "KPI Manager", section: "Main", path: "/kpi" },
  { id: "career", icon: <Briefcase className="w-[18px] h-[18px]" />, label: "Career Portal", section: "Workspace", path: "/career" },
  { id: "leaves", icon: <ClipboardList className="w-[18px] h-[18px]" />, label: "Leave Desk", section: "Workspace", path: "/leaves" },
  { id: "holidays", icon: <Calendar className="w-[18px] h-[18px]" />, label: "Institutional Calendar", section: "Workspace", path: "/holidays" },
  { id: "monitoring", icon: <Sparkles className="w-[18px] h-[18px]" />, label: "Monitoring Hub", section: "Intelligence", path: "/monitoring" },
  { id: "ai", icon: <Sparkles className="w-[18px] h-[18px]" />, label: "Naman AI Assistant", section: "Intelligence", path: "/ai" },
  { id: "sop", icon: <BookOpen className="w-[18px] h-[18px]" />, label: "Operational SOPs", section: "Intelligence", path: "/sop" },
  { id: "admin", icon: <Settings className="w-[18px] h-[18px]" />, label: "Governance Control", section: "System", adminOnly: true, path: "/admin" },
];

const Sidebar: React.FC<{ isOpen?: boolean; onClose?: () => void }> = ({ isOpen = false, onClose }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const [profileOpen, setProfileOpen] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);

  const isAdminOrManager = user?.role === "Admin" || user?.role === "Manager";
  const sections = ["Main", "Workspace", "Intelligence", ...(isAdminOrManager ? ["System"] : [])];
  const currentPath = location.pathname;

  const initials = user?.name
    ? user.name.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase()
    : "U";

  return (
    <>
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-30 md:hidden backdrop-blur-sm"
          onClick={onClose}
        />
      )}
      
      <aside className={`h-screen flex-shrink-0 bg-[#30231D] border-r border-white/5 flex flex-col z-40 fixed top-0 bottom-0 md:static transition-all duration-500 cubic-bezier(0.4, 0, 0.2, 1) ${isOpen ? "translate-x-0 shadow-2xl" : "-translate-x-full md:translate-x-0"} ${isCollapsed ? "w-[88px]" : "w-[260px]"}`}>

        {/* Brand Section */}
        <div className="h-24 flex items-center px-6">
          {!isCollapsed ? (
            <div className="flex items-center gap-4 cursor-pointer" onClick={() => navigate("/dashboard")}>
              <div className="w-10 h-10 rounded-xl brand-gradient flex items-center justify-center text-white shadow-xl shadow-orange-500/10 transition-transform duration-500">
                <CircleDot className="w-5 h-5 stroke-[2.5]" />
              </div>
              <div className="flex flex-col">
                <span className="font-bold text-white tracking-tight text-lg">Naman<span className="text-amber-400">AI</span></span>
                <span className="text-[9px] text-white/30 font-bold uppercase tracking-widest">Enterprise LMS</span>
              </div>
            </div>
          ) : (
            <div className="w-10 h-10 mx-auto rounded-xl brand-gradient flex items-center justify-center text-white shadow-xl">
              <CircleDot className="w-5 h-5 stroke-[2.5]" />
            </div>
          )}
        </div>

        {/* Navigation Area */}
        <nav className="flex-1 py-4 overflow-y-auto scrollbar-none px-4 space-y-8">
          {sections.map((section) => (
            <div key={section} className="space-y-2">
              {!isCollapsed && (
                <div className="px-3 mb-2">
                  <span className="text-[10px] font-bold text-white/20 tracking-[0.2em] uppercase">
                    {section}
                  </span>
                </div>
              )}

              <div className="flex flex-col gap-0.5">
                {navItems
                  .filter((item) => item.section === section && (!item.adminOnly || isAdminOrManager) && (!item.managerOnly || isAdminOrManager))
                  .map((item) => {
                    const isActive = currentPath === item.path || currentPath.startsWith(item.path + "/");
                    
                    return (
                      <button
                        key={item.id}
                        onClick={() => {
                          navigate(item.path);
                          if (onClose) onClose();
                        }}
                        className={`
                          w-full flex items-center gap-3.5 px-3 py-2.5 rounded-xl
                          transition-all duration-300 text-left group relative
                          ${isActive
                            ? "bg-white/5 text-amber-400 shadow-sm"
                            : "text-white/40 hover:bg-white/[0.03] hover:text-white"
                          }
                        `}
                      >
                        <div className={`transition-colors duration-300 ${isActive ? "text-amber-400" : "text-white/30 group-hover:text-white"}`}>
                          {item.icon}
                        </div>

                        {!isCollapsed && (
                          <span className={`flex-1 font-medium text-[13px] tracking-tight truncate ${isActive ? "text-white font-semibold" : ""}`}>
                            {item.label}
                          </span>
                        )}

                        {isActive && (
                          <div className={`absolute left-0 w-1 h-4 bg-amber-400 rounded-r-full transition-all duration-300 ${isCollapsed ? "left-0" : "-left-4"}`} />
                        )}
                      </button>
                    );
                  })}
              </div>
            </div>
          ))}
        </nav>

        {/* Footer / User Profile Area */}
        <div className="p-4 border-t border-white/5">
          {!isCollapsed && (
            <button
              onClick={() => setProfileOpen(true)}
              className="w-full flex items-center gap-3 p-2.5 rounded-xl bg-white/[0.02] border border-white/5 hover:bg-white/5 transition-all group"
            >
              <div className="w-9 h-9 rounded-lg bg-[#3d2e27] flex items-center justify-center font-bold text-white/80 border border-white/10 shadow-lg text-xs overflow-hidden">
                {(user as any)?.avatar_url ? (
                  <img src={(user as any).avatar_url} className="w-full h-full object-cover" />
                ) : initials}
              </div>
              <div className="flex-1 min-w-0 text-left">
                <div className="text-[12px] font-semibold text-white/90 truncate group-hover:text-amber-400 transition-colors">{user?.name}</div>
                <div className="text-[9px] text-white/30 font-bold uppercase tracking-widest">{user?.role}</div>
              </div>
            </button>
          )}

          <button 
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="mt-4 w-full h-10 flex items-center justify-center rounded-xl text-white/10 hover:text-white/40 hover:bg-white/[0.02] transition-colors"
          >
            {isCollapsed ? <PanelLeft className="w-4 h-4" /> : <PanelLeftClose className="w-4 h-4" />}
          </button>
        </div>
      </aside>

      <UserProfilePanel open={profileOpen} onClose={() => setProfileOpen(false)} />
    </>
  );
};

export default Sidebar;