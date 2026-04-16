import os

REPLACEMENTS = {
    "\u2013": "-",    # En-dash
    "\u2014": "-",    # Em-dash
    "\u2022": "*",    # Bullet
    "\u2026": "...",  # Ellipsis
    "\u20b9": "Rs. ", # Rupee
    "\u2500": "-",    # Box drawing horizontal
    "\u2705": "[OK]", # Check mark
    "\u274c": "[FAIL]",# Cross mark
    "\u2728": "*",    # Sparkles
    "\ud83d": "!",    # High surrogate (emoji part)
    "\ud83c": "!",    # High surrogate (emoji part)
}

def sanitize_file(filepath):
    if not os.path.exists(filepath):
        return
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            
        original_len = len(content)
        for char, sub in REPLACEMENTS.items():
            content = content.replace(char, sub)
            
        # Also strip any remaining non-ascii just in case
        sanitized = "".join([c if ord(c) < 128 else " " for c in content])
        
        with open(filepath, "w", encoding="ascii") as f:
            f.write(sanitized)
            
        print(f"Sanitized {filepath}")
    except Exception as e:
        print(f"Error sanitizing {filepath}: {e}")

files_to_sanitize = [
    "main.py",
    "mongo_db.py",
    "agents/AIChat.py",
    "agents/Course_generator.py",
    "agents/Career.py",
    "agents/Profile_routes.py",
    "agents/kpi_manager.py",
    "agents/Monitoring_agent.py"
]

for f in files_to_sanitize:
    sanitize_file(f)
