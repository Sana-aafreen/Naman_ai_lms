import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { ChatPanel } from '@/components/AITutor/ChatPanel';
import { ModuleViewer } from '@/components/AITutor/ModuleViewer';
import { ProgressDashboard } from '@/components/AITutor/ProgressDashboard';
import { AssessmentModal } from '@/components/AITutor/AssessmentModal';
import { Button } from '@/components/ui/button';
import { Sparkles, ChevronRight, GraduationCap } from 'lucide-react';
import { type Module } from '@/lib/types';
import { useToast } from '@/hooks/use-toast';
import { apiGet, apiPost } from '@/lib/api';
import { motion, AnimatePresence } from 'framer-motion';

export default function AITutor() {
  const { user } = useAuth();
  const { toast } = useToast();
  const [activeModule, setActiveModule] = useState<Module | null>(null);
  const [modules, setModules] = useState<Module[]>([]);
  const [progress, setProgress] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [isAssessmentOpen, setIsAssessmentOpen] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [modulesData, progressData] = await Promise.all([
        apiGet<Module[]>('/api/tutor/modules'),
        apiGet<any[]>('/api/tutor/progress')
      ]);
      setModules(modulesData);
      setProgress(progressData);
    } catch (err) {
      console.error('Failed to fetch tutor data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleModuleGenerated = async (moduleData: any) => {
    try {
      await apiPost('/api/tutor/modules', {
        title: moduleData.title,
        topic: moduleData.topic,
        content: moduleData,
        department: user?.department
      });
      fetchData();
      setActiveTab('modules');
    } catch (err) {
      console.error('Failed to save generated module:', err);
      toast({
        variant: "destructive",
        title: "Persistence Error",
        description: "Failed to save the generated module to your library.",
      });
    }
  };

  const handleSelectModule = (module: Module) => {
    setActiveModule(module);
    setIsAssessmentOpen(true);
  };

  const handleCompleteAssessment = async (score: number, answers: any[]) => {
    if (!activeModule) return;

    try {
      await apiPost('/api/tutor/progress', {
        module_id: activeModule.id,
        topic: activeModule.topic,
        status: 'completed',
        score: score,
        strengths: activeModule.key_concepts?.map(c => c.title) || [activeModule.topic],
        weaknesses: []
      });

      await apiPost('/api/tutor/assessment', {
        module_id: activeModule.id,
        questions: activeModule.content?.practice_questions || activeModule.practice_questions || [],
        answers: answers,
        score: score,
        feedback: "Strategic objective achieved. Performance has been recorded in your profile."
      });

      toast({
        title: "Assessment Certified",
        description: `Proficiency level verified at ${score}%. Data archived.`,
      });

      fetchData();
    } catch (err) {
      console.error('Failed to record assessment:', err);
    }
  };

  return (
    <div className="pb-20 max-w-[1280px] mx-auto px-4 md:px-6">
      {/* Header Section Matches Strategic Courses */}
      <header className="mb-12 pt-6">
        <div className="text-[10px] text-slate-400 font-bold uppercase tracking-[0.25em] mb-6 flex items-center gap-2">
          Knowledge <ChevronRight className="w-3 h-3" /> <span className="text-slate-800 font-black tracking-tight">AI Tutor Academy</span>
        </div>
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-8">
          <div>
            <h1 className="text-4xl font-bold text-slate-900 mb-4 tracking-tight leading-none">Cognitive Development Center</h1>
            <p className="text-lg text-slate-500 font-medium max-w-2xl leading-relaxed">
              Personalized learning assets generated through <span className="text-amber-600 font-bold underline decoration-amber-200/50 underline-offset-4">Strategic AI Intelligence</span>.
            </p>
          </div>
          <div className="flex items-center gap-4 bg-white p-1.5 rounded-2xl border border-slate-100 shadow-sm">
             <div className="flex gap-1">
                {['dashboard', 'modules'].map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`px-6 py-2.5 text-[11px] font-bold rounded-xl transition-all capitalize ${activeTab === tab ? "bg-[#30231D] text-white shadow-md active:scale-95" : "text-slate-400 hover:text-slate-700 hover:bg-slate-50"}`}
                  >
                    {tab}
                  </button>
                ))}
             </div>
          </div>
        </div>
      </header>

      <main className="grid grid-cols-1 xl:grid-cols-12 gap-10">
        {/* Modules/Stats Area */}
        <div className="xl:col-span-8">
          <AnimatePresence mode="wait">
            {activeTab === 'dashboard' ? (
              <motion.div
                key="dashboard"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
              >
                <ProgressDashboard progress={progress} modules={modules} />
              </motion.div>
            ) : (
              <motion.div
                key="modules"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
              >
                <ModuleViewer 
                  modules={modules} 
                  onSelectModule={handleSelectModule} 
                  activeModuleId={activeModule?.id}
                  progress={progress} 
                />
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Tactical Support Area (Chat) */}
        <div className="xl:col-span-4 lg:sticky lg:top-6 self-start space-y-8">
          <div className="enterprise-card border-slate-200/60 shadow-xl shadow-slate-200/20">
            <ChatPanel onModuleGenerated={handleModuleGenerated} />
          </div>
          
          <div className="enterprise-card p-8 relative overflow-hidden group border-amber-100/50 bg-amber-50/10">
             <div className="absolute top-0 right-0 p-6 opacity-[0.03] scale-[2] pointer-events-none">
                <GraduationCap className="w-24 h-24 text-amber-900" />
             </div>
             <div className="flex items-center gap-2 mb-4">
                <Sparkles className="w-4 h-4 text-amber-500" />
                <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em]">Strategic Doctrine</h4>
             </div>
             <p className="text-[13px] text-slate-600 font-medium leading-relaxed italic relative z-10">
               "Mastery is not a destination, but a continuous tactical evolution of the self."
             </p>
             <div className="mt-6 flex items-center gap-3 pt-6 border-t border-amber-100/30">
                <div className="w-2 h-2 rounded-full bg-amber-500 shadow-sm shadow-amber-500/40" />
                <span className="text-[10px] font-black text-[#30231D] uppercase tracking-widest">Naman Strategic AI</span>
             </div>
          </div>
        </div>
      </main>

      <AssessmentModal 
        isOpen={isAssessmentOpen}
        onClose={() => setIsAssessmentOpen(false)}
        module={activeModule}
        onComplete={handleCompleteAssessment}
      />
    </div>
  );
}
