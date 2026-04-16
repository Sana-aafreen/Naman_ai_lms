const fs = require('fs');
const path = require('path');

const files = [
  'JobBoard.tsx',
  'InterviewPrep.tsx',
  'CVBuilder.tsx'
];

const dir = 'c:/Users/sumbu/Downloads/namandarshan-learn-ai-fullstack/namandarshan-learn-ai-fullstack/Frontend/src/components/Career';

const replacements = {
  'bg-[#070F1C]': 'bg-transparent', // or remove if possible
  'bg-[#0A1628]': 'bg-secondary/40',
  'bg-[#0F1E35]': 'bg-card',
  'bg-[#0B1729]': 'bg-card',
  'text-white': 'text-foreground',
  'text-slate-400': 'text-muted-foreground',
  'text-slate-500': 'text-muted-foreground/80',
  'text-slate-300': 'text-foreground/80',
  'border-white/8': 'border-border',
  'border-white/10': 'border-border',
  'border-white/20': 'border-border',
  'border-white/30': 'border-border',
  'border-white/6': 'border-border',
  'bg-white/3': 'bg-secondary/30',
  'bg-white/5': 'bg-secondary/50',
  'bg-white/8': 'bg-secondary/80',
  'bg-white/10': 'bg-secondary/80',
  'bg-white/15': 'bg-secondary',
  'bg-black/60': 'bg-black/40',
  'bg-black/70': 'bg-black/40',
  // Specific hero backgrounds
  'from-[#0A1628] via-[#0F1E35] to-[#0A1628]': 'from-secondary/60 via-background to-secondary/60',
  'text-[#0A1628]': 'text-white', // amber text usually needs white on top now? Wait, amber text should just be dark text. 'text-[#0A1628]' is usually on top of amber. We can make it 'text-background' or 'text-primary' but amber buttons usually have dark text. Let's keep it 'text-[#0A1628]' or 'text-slate-900'.
  'bg-slate-500/10 text-slate-400 border-slate-500/20': 'bg-secondary text-muted-foreground border-border'
};

files.forEach(file => {
  const filepath = path.join(dir, file);
  let content = fs.readFileSync(filepath, 'utf8');

  for (const [key, value] of Object.entries(replacements)) {
    content = content.split(key).join(value);
  }

  // Also replace min-h-screen to h-full. CareerPortal handles scrolling.
  content = content.replace(/min-h-screen/g, 'h-full');
  
  fs.writeFileSync(filepath, content, 'utf8');
  console.log(`Updated ${file}`);
});
