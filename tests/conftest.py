# tests/conftest.py
import sys
from pathlib import Path

# Add the project root (parent of tests/) to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)
