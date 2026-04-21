import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { HashRouter as BrowserRouter, Route, Routes, Navigate } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import Login from "@/pages/Login";
import Index from "./pages/Index.tsx";
import Dashboard from "@/pages/Dashboard";
import Courses from "@/pages/Courses";
import AIAssistant from "@/pages/AIAssistant";
import MonitoringAI from "@/pages/MonitoringAI";
import AITutor from "@/pages/AITutor";
import LeaveManagement from "@/pages/LeaveManagement";
import SOPLibrary from "@/pages/SOPLibrary";
import HolidayCalendar from "@/pages/HolidayCalendar";
import MyProgress from "@/pages/MyProgress";
import AdminDashboard from "@/pages/AdminDashboard";
import CareerPortal from "@/components/Career/CareerPortal";
import KPIManager from "@/pages/KPIManager";
import NotFound from "./pages/NotFound.tsx";

const queryClient = new QueryClient();

// Protected Route Component
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated } = useAuth();
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  return children;
};

// Login Route - Redirect to dashboard if already authenticated
const LoginRoute = () => {
  const { isAuthenticated } = useAuth();
  
  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }
  
  return <Login />;
};

const App = () => (
  <QueryClientProvider client={queryClient}>
    <AuthProvider>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <Routes>
            <Route path="/login" element={<LoginRoute />} />
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Index />
                </ProtectedRoute>
              }
            >
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard" element={<Dashboard />} />
              <Route path="courses" element={<Courses />} />
              <Route path="tutor" element={<AITutor />} />
              <Route path="progress" element={<MyProgress />} />
              <Route path="leaves" element={<LeaveManagement />} />
              <Route path="holidays" element={<HolidayCalendar />} />
              <Route path="ai" element={<AIAssistant />} />
              <Route path="monitoring" element={<MonitoringAI />} />
              <Route path="sop" element={<SOPLibrary />} />
              <Route path="career" element={<CareerPortal />} />
              <Route path="admin" element={<AdminDashboard />} />
              <Route path="kpi" element={<KPIManager />} />
            </Route>
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </AuthProvider>
  </QueryClientProvider>
);

export default App;
