import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_official_gabaritos import extract_pdf


def test_split_annulment_marker_preserves_the_answer_in_the_other_column():
    with patch('audit_official_gabaritos.subprocess.run',return_value=SimpleNamespace(stdout='112 D 157\n135\n* 180 C\n')):
        answers,ambiguous,_=extract_pdf(Path('unused.pdf'))
    assert answers=={112:{'comum':'D'}}
    assert ambiguous==[157]
