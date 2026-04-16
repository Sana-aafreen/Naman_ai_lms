import os
import re

def check_ascii(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        non_ascii = [c for c in content if ord(c) > 127]
        if non_ascii:
            # unique non-ascii chars
            chars = "".join(sorted(list(set(non_ascii))))
            print(f"Found non-ASCII in {filepath}: {chars}")
            return True
        return False
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return False

files_to_check = [
    "main.py",
    "mongo_db.py",
    "agents/AIChat.py",
    "agents/Course_generator.py",
    "agents/Career.py",
    "agents/Profile_routes.py",
]

print("Checking for non-ASCII characters...")
found = False
for f in files_to_check:
    if check_ascii(f):
        found = True

if not found:
    print("All checked files are pure ASCII.")
