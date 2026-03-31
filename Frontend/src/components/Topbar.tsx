import React from "react";
import { useAuth } from "@/contexts/AuthContext";
import { useNavigate } from "react-router-dom";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";

const Topbar: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="h-16 bg-white/80 backdrop-blur-md border-b border-border shadow-sm flex items-center px-6 gap-6 flex-shrink-0 z-50 sticky top-0">
      <div className="flex items-center gap-3 flex-shrink-0">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-saffron to-gold flex items-center justify-center text-[16px] shadow-sm">
          🛕
        </div>
        <div className="text-[15px] font-bold text-foreground tracking-tight">
          NamanDarshan <span className="text-muted-foreground font-medium text-[12px] ml-1 tracking-normal">LMS</span>
        </div>
      </div>

      <div className="w-px h-6 bg-border flex-shrink-0 hidden md:block" />

      <div className="flex-1 max-w-[420px] relative hidden sm:block">
        <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[14px] opacity-40">🔍</span>
        <input
          type="text"
          placeholder="Search courses, SOPs, employees…"
          className="w-full py-2 pl-10 pr-4 bg-secondary/50 border border-transparent rounded-full text-sm text-foreground placeholder:text-muted-foreground outline-none focus:bg-white focus:border-border focus:shadow-sm transition-all duration-200"
        />
      </div>

      <div className="ml-auto flex items-center gap-4">
        <button className="w-10 h-10 rounded-full hover:bg-secondary flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors relative">
          <span className="text-[17px]">🔔</span>
          <div className="w-2.5 h-2.5 bg-destructive rounded-full absolute top-2 right-2 border-2 border-white" />
        </button>
        
        <div className="flex items-center gap-3 pl-2 border-l border-border">
          <div className="flex flex-col items-end hidden md:flex">
            <div className="text-[13px] font-semibold text-foreground tracking-tight">{user?.name}</div>
            <div className="text-[11px] text-primary font-medium">{user?.role}</div>
          </div>
          
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="w-9 h-9 rounded-full bg-gradient-to-br from-secondary to-border flex items-center justify-center text-[13px] font-bold text-foreground border border-border shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all cursor-pointer">
                {user?.initials}
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel className="font-normal">
                <div className="flex flex-col space-y-1">
                  <p className="text-sm font-medium leading-none">{user?.name}</p>
                  <p className="text-xs leading-none text-muted-foreground">{user?.role}</p>
                  <p className="text-xs leading-none text-muted-foreground">{user?.department}</p>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild>
                <a href="/profile" className="cursor-pointer">
                  👤 Profile Settings
                </a>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleLogout} className="text-destructive cursor-pointer focus:text-destructive">
                🚪 Logout
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </div>
  );
};

export default Topbar;
