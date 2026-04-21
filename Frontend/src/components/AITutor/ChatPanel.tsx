import React, { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Send, Bot, User, Sparkles, Loader2, Info } from 'lucide-react';
import { apiPost } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/hooks/use-toast';
import { motion, AnimatePresence } from 'framer-motion';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface ChatPanelProps {
  onModuleGenerated?: (module: any) => void;
}

export const ChatPanel: React.FC<ChatPanelProps> = ({ onModuleGenerated }) => {
  const { user } = useAuth();
  const { toast } = useToast();
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: 'Salutations! I am your Naman Strategic AI Coach. How may I assist your professional development today? I can explain complex methodologies or generate tailored learning modules.' }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await apiPost<{ reply: string }>('/api/tutor/chat', {
        messages: [...messages, userMessage],
        department: user?.department
      });

      const assistantMessage: Message = { role: 'assistant', content: response.reply };
      setMessages(prev => [...prev, assistantMessage]);

      const jsonMatch = response.reply.match(/```json\n([\s\S]*?)\n```/);
      if (jsonMatch && onModuleGenerated) {
        try {
          const moduleData = JSON.parse(jsonMatch[1]);
          onModuleGenerated(moduleData);
          toast({
            title: "Module Optimized",
            description: `Intelligence asset for "${moduleData.title}" is now active.`,
          });
        } catch (e) {
          console.error("Failed to parse module JSON", e);
        }
      }
    } catch (error) {
      console.error('Tutor chat failed:', error);
      toast({
        variant: "destructive",
        title: "Link Interrupted",
        description: "Intelligence uplink failure. Re-establishing connection.",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[600px] overflow-hidden bg-white">
      {/* Premium Header */}
      <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl brand-gradient flex items-center justify-center text-white shadow-lg shadow-orange-500/10">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-[13px] font-bold text-slate-800 leading-none mb-1">Strategic AI Coach</h3>
            <div className="flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Authorized Session</span>
            </div>
          </div>
        </div>
        <div className="p-2 rounded-lg hover:bg-slate-100 transition-colors text-slate-300 cursor-help">
          <Info className="w-4 h-4" />
        </div>
      </div>

      {/* Messages Area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-5 space-y-6 scrollbar-thin">
        <AnimatePresence>
          {messages.map((msg, i) => (
            <motion.div 
              key={i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`max-w-[85%] flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                <div className={`w-8 h-8 rounded-lg flex-shrink-0 flex items-center justify-center border ${
                  msg.role === 'user' 
                    ? 'bg-[#30231D] border-[#30231D] text-white shadow-md' 
                    : 'bg-white border-slate-100 text-slate-400 shadow-sm'
                }`}>
                  {msg.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                </div>
                <div className={`p-4 rounded-2xl text-[13px] leading-relaxed font-medium ${
                  msg.role === 'user' 
                    ? 'bg-amber-50 text-[#30231D] rounded-tr-none border border-amber-100/50' 
                    : 'bg-white text-slate-600 border border-slate-100 rounded-tl-none shadow-sm'
                }`}>
                  {msg.content}
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        
        {isLoading && (
          <div className="flex justify-start">
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-lg bg-white border border-slate-100 flex items-center justify-center text-slate-300">
                <Bot className="w-4 h-4" />
              </div>
              <div className="bg-slate-50 border border-slate-100 p-4 rounded-2xl rounded-tl-none shadow-sm">
                <Loader2 className="w-4 h-4 animate-spin text-amber-500" />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="p-5 pt-2">
        <div className="relative group">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="Search knowledge base..."
            className="w-full bg-slate-50 border border-slate-200 rounded-2xl px-5 py-4 pr-14 text-[13px] text-slate-700 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500/40 transition-all resize-none min-h-[58px] max-h-[150px] shadow-inner"
            rows={1}
          />
          <Button 
            size="icon" 
            variant="ghost"
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="absolute right-2.5 bottom-2.5 h-10 w-10 text-amber-500 hover:bg-amber-500 hover:text-white transition-all rounded-xl active:scale-90"
          >
            <Send className="w-5 h-5" />
          </Button>
        </div>
        <div className="flex items-center justify-center gap-1.5 mt-4 opacity-30 select-none">
          <Sparkles className="w-3 h-3 text-slate-400" />
          <span className="text-[9px] font-bold text-slate-500 uppercase tracking-[0.25em]">Strategic AI Processing</span>
        </div>
      </div>
    </div>
  );
};
