import React, { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { CheckCircle2, AlertCircle, Award, GraduationCap, ArrowRight, Zap, Trophy, ShieldCheck } from 'lucide-react';
import { type Module } from '@/lib/types';
import { motion, AnimatePresence } from 'framer-motion';

interface AssessmentModalProps {
  isOpen: boolean;
  onClose: () => void;
  module: Module | null;
  onComplete: (score: number, answers: any[]) => void;
}

export const AssessmentModal: React.FC<AssessmentModalProps> = ({
  isOpen,
  onClose,
  module,
  onComplete
}) => {
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState<any[]>([]);
  const [isFinished, setIsFinished] = useState(false);
  const [score, setScore] = useState(0);

  if (!module) return null;

  const questions = module.content?.practice_questions || module.practice_questions || [];

  const handleAnswerSelect = (answerIndex: number) => {
    const newAnswers = [...answers];
    newAnswers[currentQuestionIndex] = answerIndex;
    setAnswers(newAnswers);
  };

  const handleNext = () => {
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(prev => prev + 1);
    } else {
      calculateScore();
    }
  };

  const calculateScore = () => {
    let correctCount = 0;
    questions.forEach((q: any, i: number) => {
      // Find the correct answer by checking index of correct text in options array
      // or if correct_answer is just an index (depending on model output)
      if (typeof q.correct_answer === 'number' && answers[i] === q.correct_answer) {
        correctCount++;
      } else if (typeof q.correct_answer === 'string') {
        const correctIdx = q.options.indexOf(q.correct_answer);
        if (answers[i] === correctIdx) correctCount++;
      }
    });

    const finalScore = Math.round((correctCount / questions.length) * 100);
    setScore(finalScore);
    setIsFinished(true);
    onComplete(finalScore, answers);
  };

  const handleClose = () => {
    setIsFinished(false);
    setCurrentQuestionIndex(0);
    setAnswers([]);
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="sm:max-w-[700px] p-0 overflow-hidden bg-[#FCFAF7] border-none shadow-2xl rounded-[32px]">
        {!isFinished ? (
          <div className="flex flex-col h-[650px]">
            {/* Header / Progress Area */}
            <div className="p-8 pb-4">
               <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                     <div className="w-10 h-10 rounded-xl brand-gradient flex items-center justify-center text-white shadow-lg shadow-orange-500/10">
                        <Zap className="w-5 h-5" />
                     </div>
                     <div>
                        <h2 className="text-[14px] font-black text-[#30231D] tracking-tight uppercase leading-none mb-1">Strategic Assessment</h2>
                        <span className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">{module.title}</span>
                     </div>
                  </div>
                  <div className="flex items-center gap-2 bg-white px-4 py-2 rounded-xl border border-slate-100 shadow-sm">
                     <span className="text-[11px] font-black text-slate-600 uppercase tracking-widest">Protocol</span>
                     <span className="text-[13px] font-black text-amber-600">{currentQuestionIndex + 1}/{questions.length}</span>
                  </div>
               </div>
               <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden shadow-inner">
                  <motion.div 
                    className="h-full brand-gradient"
                    initial={{ width: 0 }}
                    animate={{ width: `${((currentQuestionIndex + 1) / questions.length) * 100}%` }}
                  />
               </div>
            </div>

            {/* Question Body */}
            <div className="flex-1 overflow-y-auto px-8 py-6">
               <motion.div
                 key={currentQuestionIndex}
                 initial={{ opacity: 0, x: 20 }}
                 animate={{ opacity: 1, x: 0 }}
                 className="space-y-8"
               >
                  <h3 className="text-xl font-bold text-slate-900 leading-tight tracking-tight">
                    {questions[currentQuestionIndex].question}
                  </h3>
                  
                  <div className="grid grid-cols-1 gap-4">
                    {questions[currentQuestionIndex].options.map((option: string, i: number) => (
                      <button
                        key={i}
                        onClick={() => handleAnswerSelect(i)}
                        className={`w-full p-5 rounded-[22px] text-left transition-all duration-300 border-2 group relative overflow-hidden ${
                          answers[currentQuestionIndex] === i
                            ? 'border-amber-500 bg-amber-50/50 shadow-md translate-x-1'
                            : 'border-slate-100 bg-white hover:border-slate-200 hover:bg-slate-50/50 hover:-translate-y-0.5'
                        }`}
                      >
                         <div className={`absolute left-0 top-0 w-1 h-full brand-gradient transition-all duration-500 ${answers[currentQuestionIndex] === i ? 'opacity-100' : 'opacity-0'}`} />
                         <div className="flex items-center gap-5">
                            <div className={`w-8 h-8 rounded-[10px] flex items-center justify-center font-black text-xs transition-colors ${
                              answers[currentQuestionIndex] === i 
                                ? 'brand-gradient text-white' 
                                : 'bg-slate-50 text-slate-400 group-hover:bg-slate-100'
                            }`}>
                               {String.fromCharCode(65 + i)}
                            </div>
                            <span className={`text-[14px] font-bold ${answers[currentQuestionIndex] === i ? 'text-[#30231D]' : 'text-slate-600'}`}>
                              {option}
                            </span>
                         </div>
                      </button>
                    ))}
                  </div>
               </motion.div>
            </div>

            {/* Footer */}
            <div className="p-8 pt-4 border-t border-slate-100 bg-white/50">
               <Button
                 onClick={handleNext}
                 disabled={answers[currentQuestionIndex] === undefined}
                 className="w-full h-14 brand-gradient rounded-[20px] text-[13px] font-black uppercase tracking-[0.1em] text-white shadow-xl shadow-orange-500/20 active:scale-[0.98] transition-all disabled:opacity-50 disabled:grayscale"
               >
                 {currentQuestionIndex === questions.length - 1 ? 'Analyze Performance' : 'Commit Vector'}
                 <ArrowRight className="ml-2 w-5 h-5" />
               </Button>
            </div>
          </div>
        ) : (
          <div className="p-10 flex flex-col items-center text-center">
            <motion.div
              initial={{ scale: 0.5, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="w-24 h-24 rounded-[32px] brand-gradient flex items-center justify-center text-white mb-8 shadow-2xl shadow-orange-500/40 relative"
            >
               <Trophy className="w-12 h-12" />
               <motion.div 
                 className="absolute -top-2 -right-2 w-10 h-10 rounded-full bg-emerald-500 flex items-center justify-center border-4 border-[#FCFAF7]"
                 initial={{ scale: 0 }}
                 animate={{ scale: 1 }}
                 transition={{ delay: 0.5 }}
               >
                  <ShieldCheck className="w-5 h-5 text-white" />
               </motion.div>
            </motion.div>

            <h2 className="text-3xl font-black text-slate-900 tracking-tighter mb-4 leading-none">Assessment Certified</h2>
            <p className="text-[15px] text-slate-500 font-medium max-w-md mb-10 leading-relaxed italic">
               "{score >= 80 ? 'Exceptional cognitive resonance detected. You have demonstrated strategic mastery of the material.' : 'Proficiency level established. Continue tactical iterations to reach maximum potential.'}"
            </p>

            <div className="grid grid-cols-2 gap-6 w-full max-w-md mb-12">
               <div className="bg-white border border-slate-100 p-6 rounded-[24px] shadow-sm">
                  <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Final Score</div>
                  <div className="text-3xl font-black text-slate-900 tracking-tight leading-none">{score}%</div>
               </div>
               <div className="bg-white border border-slate-100 p-6 rounded-[24px] shadow-sm">
                  <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Status</div>
                  <div className={`text-[13px] font-black uppercase tracking-widest leading-none mt-3 ${score >= 80 ? 'text-emerald-500' : 'text-amber-500'}`}>
                    {score >= 80 ? 'Certified' : 'Proficient'}
                  </div>
               </div>
            </div>

            <Button
              onClick={handleClose}
              className="w-full h-14 bg-[#30231D] hover:bg-slate-800 text-white rounded-[20px] text-[13px] font-black uppercase tracking-widest active:scale-95 transition-all shadow-xl shadow-slate-900/10"
            >
              Archiving Session & Exit
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};
