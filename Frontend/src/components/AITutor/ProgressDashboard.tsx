import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { BarChart3, Target, Award, Zap, TrendingUp, BookOpen, Search, PlayCircle } from 'lucide-react';
import { motion } from 'framer-motion';

interface ProgressDashboardProps {
  progress: any[];
  modules: any[];
}

export const ProgressDashboard: React.FC<ProgressDashboardProps> = ({ progress, modules }) => {
  const completedCount = progress.filter(p => p.status === 'completed').length;
  const avgScore = progress.length > 0
    ? Math.round(progress.reduce((acc, p) => acc + (p.score || 0), 0) / progress.length)
    : 0;

  const stats = [
    { label: 'Strategic Mastery', value: `${completedCount}/${modules.length}`, icon: Award, color: 'text-amber-500', bg: 'bg-amber-50' },
    { label: 'Proficiency Index', value: `${avgScore}%`, icon: TrendingUp, color: 'text-emerald-500', bg: 'bg-emerald-50' },
    { label: 'Knowledge Points', value: (completedCount * 150).toString(), icon: Zap, color: 'text-blue-500', bg: 'bg-blue-50' },
    { label: 'Current Vectors', value: modules.length.toString(), icon: Target, color: 'text-rose-500', bg: 'bg-rose-50' },
  ];

  return (
    <div className="space-y-10">
      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: i * 0.05 }}
            className="enterprise-card group"
          >
             <div className="p-6 flex flex-col h-full bg-white">
                <div className={`w-12 h-12 rounded-2xl ${stat.bg} ${stat.color} flex items-center justify-center mb-5 border border-slate-100 group-hover:brand-gradient group-hover:text-white transition-all duration-500 group-hover:scale-110 shadow-sm`}>
                  <stat.icon className="w-6 h-6" />
                </div>
                <div className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] mb-1">{stat.label}</div>
                <div className="text-3xl font-black text-slate-900 tracking-tighter leading-none">{stat.value}</div>
             </div>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
        {/* Competency Matrix */}
        <div className="enterprise-card border-slate-200/50">
          <CardHeader className="p-8 border-b border-slate-50 bg-slate-50/10">
            <div className="flex items-center justify-between">
               <div>
                  <h3 className="text-xl font-bold text-slate-900 tracking-tight leading-none mb-1">Competency Matrix</h3>
                  <p className="text-[11px] text-slate-400 font-bold uppercase tracking-widest">Real-time Skill Vectors</p>
               </div>
               <div className="w-10 h-10 rounded-xl bg-slate-50 flex items-center justify-center text-slate-400">
                  <BarChart3 className="w-5 h-5" />
               </div>
            </div>
          </CardHeader>
          <CardContent className="p-8 space-y-6 bg-white">
            {progress.length === 0 ? (
              <div className="py-12 text-center">
                <p className="text-slate-400 text-[13px] font-medium leading-relaxed">
                   No proficiency data detected.<br/> Complete specialized assessments to generate vectors.
                </p>
              </div>
            ) : (
              progress.slice(0, 5).map((p, i) => (
                <div key={i} className="space-y-3 p-5 rounded-2xl border border-slate-50 bg-slate-50/20 group hover:border-amber-100/50 transition-all">
                  <div className="flex justify-between items-center px-1">
                    <span className="text-[13px] font-bold text-slate-700 tracking-tight">{p.topic}</span>
                    <span className="text-[11px] font-black text-amber-600 bg-amber-50 px-2 py-0.5 rounded-lg border border-amber-100/30">{p.score}%</span>
                  </div>
                  <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden shadow-inner">
                    <motion.div 
                      initial={{ width: 0 }}
                      animate={{ width: `${p.score}%` }}
                      className="h-full brand-gradient rounded-full shadow-[0_0_8px_rgba(255,112,51,0.2)]"
                    />
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </div>

        {/* Milestone Vault */}
        <div className="enterprise-card border-slate-200/50">
          <CardHeader className="p-8 border-b border-slate-50 bg-slate-50/10">
            <div className="flex items-center justify-between">
               <div>
                  <h3 className="text-xl font-bold text-slate-900 tracking-tight leading-none mb-1">Knowledge Archive</h3>
                  <p className="text-[11px] text-slate-400 font-bold uppercase tracking-widest">Mastered Intelligence Assets</p>
               </div>
               <div className="w-10 h-10 rounded-xl bg-slate-50 flex items-center justify-center text-slate-400">
                  <Search className="w-5 h-5" />
               </div>
            </div>
          </CardHeader>
          <CardContent className="p-8 space-y-4 bg-white">
            {progress.filter(p => p.status === 'completed').length === 0 ? (
              <div className="py-12 text-center text-slate-400">
                <p className="text-[13px] font-medium italic">Protocol pending. Achieve mastery to archive results.</p>
              </div>
            ) : (
              progress.filter(p => p.status === 'completed').map((p, i) => (
                <div key={i} className="flex items-center gap-4 p-4 rounded-2xl border border-slate-100 hover:bg-slate-50 transition-all group">
                  <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-500 flex items-center justify-center shadow-sm border border-emerald-100/50 group-hover:scale-110 transition-transform">
                    <CheckCircleIcon className="w-5 h-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-[13px] font-bold text-slate-800 truncate">{p.topic}</div>
                    <div className="text-[10px] text-slate-400 font-medium">{new Date(p.updated_at).toLocaleDateString()} • Verified Proficient</div>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </div>
      </div>
    </div>
  );
};

const CheckCircleIcon = (props: any) => (
  <svg 
    xmlns="http://www.w3.org/2000/svg" 
    viewBox="0 0 24 24" 
    fill="none" 
    stroke="currentColor" 
    strokeWidth="3" 
    strokeLinecap="round" 
    strokeLinejoin="round" 
    {...props}
  >
    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
    <polyline points="22 4 12 14.01 9 11.01" />
  </svg>
);
