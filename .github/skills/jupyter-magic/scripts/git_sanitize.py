#!/usr/bin/env python3
import json
import sys
import os
from pathlib import Path

def sanitize_notebook(file_path):
    """
    Removes output cells, execution counts, and metadata from a Jupyter notebook
    to ensure clean git diffs and maintain "Agentic Governance" standards.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            nb = json.load(f)

        for cell in nb.get('cells', []):
            if cell['cell_type'] == 'code':
                cell['outputs'] = []
                cell['execution_count'] = None
            
            # Remove unnecessary cell-level metadata that causes diff noise
            cell.get('metadata', {}).pop('execution', None)
            cell.get('metadata', {}).pop('collapsed', None)
            cell.get('metadata', {}).pop('scrolled', None)

        # Optional: Reset notebook-level metadata to a neutral state
        if 'metadata' in nb:
            nb['metadata'].pop('widgets', None)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(nb, f, indent=1, ensure_ascii=False)
            f.write('\n') # Ensure trailing newline

        print(f"✅ Sanitized: {file_path}")
    except Exception as e:
        print(f"❌ Error sanitizing {file_path}: {e}")

def main():
    # Targets: Current directory or specific notebooks/ folder
    target_dirs = ['./notebooks', './']
    
    found_any = False
    for target in target_dirs:
        if os.path.exists(target):
            for path in Path(target).rglob('*.ipynb'):
                if '.ipynb_checkpoints' not in str(path):
                    sanitize_notebook(path)
                    found_any = True
    
    if not found_any:
        print("No notebooks found to sanitize.")

if __name__ == "__main__":
    main()