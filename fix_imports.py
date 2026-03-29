"""Fix all relative imports to absolute imports"""
import os
import re

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # Replace relative imports with absolute
    content = re.sub(r'from \.\.(\w+) import', r'from \1 import', content)
    content = re.sub(r'from \.(\w+) import', r'from gateway.\1 import', content)

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed: {filepath}")
    else:
        print(f"Skipped: {filepath}")

# Fix all Python files
for root, dirs, files in os.walk('C:/Users/mymai/Desktop/TSMv1'):
    for file in files:
        if file.endswith('.py') and file != 'fix_imports.py':
            filepath = os.path.join(root, file)
            try:
                fix_file(filepath)
            except Exception as e:
                print(f"Error fixing {filepath}: {e}")

print("\nImport fixes complete!")
