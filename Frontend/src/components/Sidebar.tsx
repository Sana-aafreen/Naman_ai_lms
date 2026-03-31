import React from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";

interface NavItem {
  id: string;
  icon: string;
  label: string;
  badge?: string;
  section: string;
  adminOnly?: boolean;
  path: string;
}

const navItems: NavItem[] = [
  { id: "dashboard", icon: "🏠", label: "Dashboard", section: "Main", path: "/dashboard" },
  { id: "courses", icon: "📚", label: "Courses", badge: "12", section: "Main", path: "/courses" },
  { id: "training", icon: "🎓", label: "Training Material", section: "Main", path: "/training" },
  { id: "progress", icon: "📈", label: "My Progress", section: "Main", path: "/progress" },
  { id: "leaves", icon: "📅", label: "Leave Management", section: "Workplace", path: "/leaves" },
  { id: "holidays", icon: "🎉", label: "Holiday Calendar", section: "Workplace", path: "/holidays" },
  { id: "projects", icon: "📋", label: "Projects", section: "Workplace", path: "/projects" },
  { id: "medical", icon: "🏥", label: "Medical & Insurance", section: "Workplace", path: "/medical" },
  { id: "ai", icon: "🤖", label: "AI Assistant", section: "AI & Tools", path: "/ai" },
  { id: "sop", icon: "📄", label: "SOP Library", section: "AI & Tools", path: "/sop" },
  { id: "admin", icon: "⚙️", label: "Admin Dashboard", section: "Administration", adminOnly: true, path: "/admin" },
];

const Sidebar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const isAdminOrManager = user?.role === "Admin" || user?.role === "Manager";

  const sections = ["Main", "Workplace", "AI & Tools", ...(isAdminOrManager ? ["Administration"] : [])];

  // Get current page based on URL path
  const currentPath = location.pathname;
  const activePage = currentPath.startsWith("/") ? currentPath.substring(1) : "dashboard";

  return (
    <div className="w-[260px] flex-shrink-0 bg-white border-r border-border overflow-y-auto flex flex-col z-40 fixed top-16 bottom-0 md:static md:top-auto md:bottom-auto">
      <div className="flex-1 py-4 overflow-y-auto">
        {sections.map(section => (
          <div key={section} className="mb-4">
            <div className="text-[11px] font-bold text-muted-foreground/70 tracking-widest uppercase px-6 mb-2">
              {section}
            </div>
            <div className="px-3 flex flex-col gap-1">
              {navItems
                .filter(item => item.section === section && (!item.adminOnly || isAdminOrManager))
                .map(item => (
                  <button
                    key={item.id}
                    onClick={() => navigate(item.path)}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 text-[14px] transition-all text-left rounded-xl group ${activePage === item.id
                        ? "bg-saffron/10 text-saffron font-bold"
                        : "text-muted-foreground hover:bg-secondary hover:text-foreground font-medium"
                      }`}
                  >
                    <span
                      className={`text-[16px] w-5 text-center flex-shrink-0 transition-transform duration-200 ${activePage === item.id ? "scale-110" : "group-hover:scale-110 grayscale group-hover:grayscale-0"
                        }`}
                    >
                      {item.icon}
                    </span>
                    {item.label}
                    {item.badge && (
                      <span className="ml-auto text-[10px] px-2 py-0.5 rounded-full bg-saffron text-primary-foreground font-semibold shadow-sm">
                        {item.badge}
                      </span>
                    )}
                  </button>
                ))}
            </div>
          </div>
        ))}
      </div>

      <div className="p-4 mt-auto">
        <div className="p-3 rounded-2xl bg-secondary/60 border border-border/60 hover:border-border transition-colors">
          <div className="flex items-center gap-3">
            <div className="w-[38px] h-[38px] rounded-full bg-gradient-to-br from-saffron to-gold flex items-center justify-center text-[14px] font-bold text-primary-foreground flex-shrink-0 shadow-sm">
              {user?.initials}
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-[14px] font-bold truncate text-foreground tracking-tight">{user?.name}</div>
              <div className="text-[12px] font-medium text-muted-foreground truncate">{user?.role}</div>
            </div>
            <button
              onClick={() => {
                // Logout is handled in Topbar
              }}
              className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-white hover:text-destructive hover:shadow-sm text-muted-foreground transition-all"
              title="Logout"
            >
              <span className="text-sm">🚪</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
