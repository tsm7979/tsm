"""Fix all imports in TSMv1 to use correct paths."""

import os
import re
from pathlib import Path

def fix_imports_in_file(filepath: Path) -> bool:
    """Fix imports in a single file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original = content

        # Fix old src.core.learning imports → learning
        content = re.sub(r'from src\.core\.learning\.', r'from learning.', content)
        content = re.sub(r'import src\.core\.learning\.', r'import learning.', content)

        # Fix old src.core.llm imports → router or models
        content = re.sub(r'from src\.core\.llm import LLMRouter', r'from router.orchestrator import PolyLLMOrchestrator as LLMRouter', content)
        content = re.sub(r'from src\.core\.llm import', r'from router.orchestrator import', content)

        # Fix old src.core.agentic imports → execution
        content = re.sub(r'from src\.core\.agentic\.', r'from execution.', content)
        content = re.sub(r'import src\.core\.agentic\.', r'import execution.', content)

        # Fix relative imports in execution
        content = re.sub(r'from \.memory_manager import', r'from execution.memory_manager import', content)

        # Fix old backend paths
        content = re.sub(r'"backend/data/', r'"data/', content)
        content = re.sub(r"'backend/data/", r"'data/", content)

        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True

        return False

    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False


def main():
    """Fix imports in all Python files."""
    base_dir = Path('.')

    directories = [
        'execution',
        'learning',
        'trust',
        'models',
        'router',
        'gateway',
        'firewall',
    ]

    print("=" * 70)
    print("FIXING IMPORTS IN TSMv1")
    print("=" * 70)

    fixed_count = 0
    total_count = 0

    for directory in directories:
        dir_path = base_dir / directory
        if not dir_path.exists():
            continue

        print(f"\n[{directory}]")

        for py_file in dir_path.rglob('*.py'):
            total_count += 1
            if fix_imports_in_file(py_file):
                fixed_count += 1
                print(f"  Fixed: {py_file.relative_to(base_dir)}")

    print("\n" + "=" * 70)
    print(f"COMPLETE: Fixed {fixed_count}/{total_count} files")
    print("=" * 70)


if __name__ == "__main__":
    main()
