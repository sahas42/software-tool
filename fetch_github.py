import sys
import os
import re
from pathlib import Path

# Add the project root to sys.path so we can import src
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.compliance_checker.codebase_loader import load_codebase

def parse_and_save_files(content: str, output_dir: str):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # gitingest uses 48 equals signs, "FILE: path", 48 equals signs
    pattern = r"={48}\nFile: (.*?)\n={48}\n|={48}\nFILE: (.*?)\n={48}\n"
    
    # re.split captures the groups. Since we have an OR with two capture groups, 
    # it might return tuples or mixed. Let's use re.finditer instead for safer parsing.
    
    # A safer approach for split when there might be "File:" or "FILE:":
    # Just use ignorecase
    pattern_ic = r"(?i)={48}\nFILE: (.*?)\n={48}\n"
    
    parts = re.split(pattern_ic, content)
    
    file_count = 1
    
    # parts[0] is everything before the first match (tree summary, etc)
    for i in range(1, len(parts), 2):
        file_path = parts[i].strip()
        file_content = parts[i+1]
        
        local_filename = f"file{file_count}.txt"
        local_filepath = os.path.join(output_dir, local_filename)
        
        header = f"File Name: {os.path.basename(file_path)}\n"
        header += f"Directory Location: {os.path.dirname(file_path) or '.'}\n"
        header += f"Original Path: {file_path}\n"
        
        with open(local_filepath, "w", encoding="utf-8", errors="replace") as f:
            f.write(header + "\n" + file_content)
            
        file_count += 1
        
    print(f"Saved {file_count - 1} files to {output_dir}/")

def main():
    url = "https://github.com/sahas42/aspire-bridge"
    print(f"Fetching from {url}...")
    
    # We use the function that has already been used in the codebase
    content = load_codebase(url)
    
    output_dir = "fetched_content"
    parse_and_save_files(content, output_dir)
        
    print(f"Done!")

if __name__ == "__main__":
    main()
