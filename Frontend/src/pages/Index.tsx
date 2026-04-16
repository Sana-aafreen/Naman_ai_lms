import React, { useState } from "react";
import { Outlet } from "react-router-dom";
import { useLocation } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import Topbar from "@/components/Topbar";
import Sidebar from "@/components/Sidebar";
import FloatingAIAssistant from "@/components/FloatingAIAssistant";

const Index: React.FC = () => {
  const { user } = useAuth();
  const location = useLocation();
  const showFloatingAssistant = location.pathname === "/dashboard";
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <Topbar onMenuClick={() => setMobileMenuOpen(!mobileMenuOpen)} />
      <div className="flex flex-1 overflow-hidden relative">
        <Sidebar isOpen={mobileMenuOpen} onClose={() => setMobileMenuOpen(false)} />
        <main className="flex-1 overflow-y-auto p-6 bg-background">
          <Outlet />
        </main>
      </div>
      {showFloatingAssistant && <FloatingAIAssistant />}
    </div>
  );
};

export default Index;
