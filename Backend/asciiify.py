import sys
import re

def asciiify(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Replace common box drawing characters
    content = content.replace('─', '-')
    content = content.replace('━', '-')
    content = content.replace('═', '=')
    content = content.replace('║', '|')
    content = content.replace('┌', '+')
    content = content.replace('┐', '+')
    content = content.replace('└', '+')
    content = content.replace('┘', '+')
    content = content.replace('├', '+')
    content = content.replace('┤', '+')
    content = content.replace('┬', '+')
    content = content.replace('┴', '+')
    content = content.replace('┼', '+')
    
    # Replace other common non-ASCII symbols
    content = content.replace('•', '*')
    content = content.replace('…', '...')
    content = content.replace('✓', '[OK]')
    content = content.replace('✅', '[OK]')
    content = content.replace('⚠️', '[WARN]')
    content = content.replace('❌', '[ERROR]')
    content = content.replace('→', '->')
    content = content.replace('←', '<-')
    content = content.replace('»', '>>')
    content = content.replace('«', '<<')
    
    # Generic non-ASCII removal (replace with space or similar if still present)
    # We only target printable characters usually found in code/banners
    
    # Re-write the file
    with open(file_path, 'w', encoding='ascii', errors='ignore') as f:
        f.write(content)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        asciiify(sys.argv[1])
        print(f"ASCII-ified {sys.argv[1]}")
