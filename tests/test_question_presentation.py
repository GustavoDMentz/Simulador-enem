import subprocess
import sys
from pathlib import Path

def test_reviewed_display_migration_is_reproducible_without_editing_catalog():
    root=Path(__file__).resolve().parents[1]
    result=subprocess.run([sys.executable,str(root/'scripts/build_question_presentation.py'),'--check'],capture_output=True,text=True,check=True)
    assert '"reviewed": 315' in result.stdout
