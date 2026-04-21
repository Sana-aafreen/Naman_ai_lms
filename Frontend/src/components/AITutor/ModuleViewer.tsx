import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { BookOpen, CheckCircle2, Circle, Clock, PlayCircle, Star, ArrowRight, Sparkles } from 'lucide-react';
import { type Module } from '@/lib/types';
import { motion } from 'framer-motion';

interface ModuleViewerProps {
  modules: Module[];
  onSelectModule: (module: Module) => void;
  activeModuleId?: string;
  progress: any[];
}

export const ModuleViewer: React.FC<ModuleViewerProps> = ({ 
  modules, 
  onSelectModule, 
  activeModuleId,
  progress 
}) => {
  const getProgressStatus = (moduleId: string) => {
    const p = progress.find(pg => pg.module_id === moduleId);
    return p ? p.status : 'not_started';
  };

  const getScore = (moduleId: string) => {
    const p = progress.find(pg => pg.module_id === moduleId);
    return p ? p.score : null;
  };

  if (modules.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 px-6 text-center bg-white border border-slate-100 rounded-[32px] shadow-sm">
        <div className="w-20 h-20 rounded-3xl bg-amber-50 flex items-center justify-center text-amber-500 mb-8 shadow-inner border border-amber-100/50">
          <BookOpen className="w-10 h-10" />
        </div>
        <h3 className="text-2xl font-bold text-slate-900 mb-3 tracking-tight">Intelligence Repository Empty</h3>
        <p className="text-[15px] text-slate-500 max-w-sm font-medium leading-relaxed">
          Request the Strategic AI Coach to synthesize a new learning asset by providing a topic of interest.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
      {modules.map((module, index) => {
        const status = getProgressStatus(module.id);
        const score = getScore(module.id);
        const isActive = activeModuleId === module.id;

        return (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05 }}
            key={module.id}
          >
            <div className={`enterprise-card relative group p-1 ${isActive ? 'ring-2 ring-amber-500' : ''}`}>
              <div className="bg-white rounded-[22px] p-6 h-full flex flex-col">
                <div className="absolute top-6 right-6">
                  {status === 'completed' ? (
                    <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-50 text-emerald-600 border border-emerald-100 shadow-sm">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span className="text-[10px] font-black uppercase tracking-widest">Mastered</span>
                    </div>
                  ) : status === 'in_progress' ? (
                    <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-amber-50 text-amber-600 border border-amber-100 shadow-sm">
                      <Clock className="w-3.5 h-3.5" />
                      <span className="text-[10px] font-black uppercase tracking-widest">Learning</span>
                    </div>
                  ) : null}
                </div>

                <div className="flex items-center gap-4 mb-6">
                  <div className="w-14 h-14 rounded-2xl bg-slate-50 flex items-center justify-center text-[#FF7033] group-hover:brand-gradient group-hover:text-white group-hover:scale-105 transition-all duration-500 border border-slate-100 group-hover:border-transparent shadow-sm">
                    <Sparkles className="w-6 h-6" />
                  </div>
                  <div className="flex-1 min-w-0 pr-16 text-left">
                    <h3 className="text-lg font-bold text-slate-900 leading-tight mb-1 truncate tracking-tight">{module.title}</h3>
                    <div className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">{module.topic}</div>
                  </div>
                </div>

                <CardContent className="p-0 flex-1 space-y-6">
                  <p className="text-[13px] text-slate-500 leading-relaxed font-normal line-clamp-3">
                    {module.overview || module.content?.overview}
                  </p>

                  <div className="flex items-center justify-between pt-6 border-t border-slate-50 mt-auto">
                    {score !== null ? (
                      <div className="flex items-center gap-2 bg-amber-50/50 px-3 py-1.5 rounded-xl border border-amber-100/30">
                        <div className="flex items-center">
                          {[1, 2, 3, 4, 5].map((star) => (
                            <Star 
                              key={star} 
                              className={`w-3 h-3 ${score >= star * 20 ? 'fill-amber-500 text-amber-500' : 'text-slate-200'}`} 
                            />
                          ))}
                        </div>
                        <span className="text-[12px] font-black text-amber-600">{score}%</span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-1.5 text-slate-300">
                        <Circle className="w-3.5 h-3.5" />
                        <span className="text-[10px] font-bold uppercase tracking-widest">Uncertified</span>
                      </div>
                    )}

                    <Button 
                      onClick={() => onSelectModule(module)}
                      className={`h-11 px-6 rounded-xl text-[11px] font-black uppercase tracking-widest transition-all duration-300 active:scale-95 flex items-center gap-2 ${
                        isActive 
                          ? 'brand-gradient text-white shadow-lg shadow-orange-500/20' 
                          : 'bg-slate-900 text-white hover:bg-slate-800 shadow-md'
                      }`}
                    >
                      {status === 'completed' ? 'Review Asset' : 'Begin Protocol'}
                      <ArrowRight className="w-4 h-4 opacity-70" />
                    </Button>
                  </div>
                </CardContent>

                {/* Progress bar background decoration */}
                <div className="absolute bottom-0 left-0 h-1.5 bg-slate-100 w-full overflow-hidden rounded-b-3xl">
                  <div 
                    className="h-full brand-gradient transition-all duration-1000 shadow-[0_0_8px_rgba(255,112,51,0.4)]"
                    style={{ width: status === 'completed' ? '100%' : status === 'in_progress' ? '45%' : '0%' }}
                  />
                </div>
              </div>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
};
