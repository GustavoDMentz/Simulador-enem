import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from publish_blue_candidates import approved_record, record_digest
from audit_official_gabaritos import extract_pdf


def test_annulled_rows_preserve_the_other_column():
    with patch('audit_official_gabaritos.subprocess.run',return_value=SimpleNamespace(stdout='112 D 157 Anulado\n135 anulada 180 C\n')):
        answers,ambiguous,_=extract_pdf(Path('unused.pdf'))
    assert answers=={112:{'comum':'D'},157:{'comum':'Anulado'},135:{'comum':'anulada'},180:{'comum':'C'}}
    assert not ambiguous


def test_approval_binds_identity_content_answer_and_completeness():
    q=dict(id_unico_sistema='sample',ano=2022,dia=2,posicao_prova=91,gabarito_oficial='A',conteudo=dict(enunciado='Stem',alternativas=dict.fromkeys('ABCDE','Option')))
    e=dict(id='sample',year=2022,day=2,number=91,status='CONFORME',publication_authorized=True,source_sha256='a'*64,answer_source_sha256='b'*64,answer_source_url='https://download.inep.gov.br/key.pdf',record_sha256=record_digest(q),audit=dict.fromkeys(['text','options','graphics','credits','continuity','answer'],True))
    assert approved_record(q,[e])
    assert not approved_record(q,[])
    assert not approved_record(q,[e,e])
    assert not approved_record({**q,'gabarito_oficial':'B'},[e])
    assert not approved_record({**q,'conteudo':{**q['conteudo'],'enunciado':'Truncated'}},[e])
    assert not approved_record(q,[{**e,'number':92}])
    assert not approved_record(q,[{**e,'audit':{**e['audit'],'answer':False}}])


def test_restored_release_and_unchanged_quarantine():
    root=Path(__file__).resolve().parents[1]
    snapshot=[json.loads(l) for l in (root/'data/audit/session-recovery/preview-questions.jsonl').read_text().splitlines()]
    preview_path=root/'data/blue-published/preview-questions.jsonl'
    preview=[json.loads(l) for l in (preview_path if preview_path.exists() else root/'data/audit/session-recovery/preview-questions.jsonl').read_text().splitlines()]
    release=[json.loads(l) for l in (root/'data/blue-published/questions.jsonl').read_text().splitlines()]
    entries=json.loads((root/'data/audit/manifest.json').read_text())['questions']
    assert len(snapshot)==len(preview)==513
    assert len(release)==len(entries)==97
    assert len({q['id_unico_sistema'] for q in release})==97
    original=[q for q in snapshot if q['scoring_enabled']]
    current={q['id_unico_sistema']:q for q in release}
    assert len(original)==59
    assert all(current[q['id_unico_sistema']]=={**q,'parametros_tri':None,'preview_status':'VALIDATED','preview_unverified':False,'preview_warning':None} for q in original)
    for q in release:
        assert approved_record(q,entries,root/'data/extracted')
        assert q['parametros_tri'] is None
    pending=[(a,b) for a,b in zip(snapshot,preview) if not a['scoring_enabled'] and a['id_unico_sistema'] not in {q['id_unico_sistema'] for q in release}]
    assert len(pending)==416
    assert all(a==b for a,b in pending)


def test_incremental_publisher_preserves_approval_and_quarantines_tampering(tmp_path,monkeypatch):
    import publish_blue_candidates as publisher
    q=dict(id_unico_sistema='sample',ano=2022,dia=2,posicao_prova=91,gabarito_oficial='A',conteudo=dict(enunciado='Verified',alternativas=dict.fromkeys('ABCDE','Option')))
    entry=dict(id='sample',year=2022,day=2,number=91,status='CONFORME',publication_authorized=True,source_sha256='a'*64,answer_source_sha256='b'*64,answer_source_url='https://download.inep.gov.br/key.pdf',record_sha256=record_digest(q),audit=dict.fromkeys(['text','options','graphics','credits','continuity','answer'],True))
    monkeypatch.chdir(tmp_path)
    for directory in ['data/audit/session-recovery','data/blue-published']:
        Path(directory).mkdir(parents=True)
    publisher.RECOVERY.write_text(json.dumps({**q,'gabarito_oficial':None,'scoring_enabled':False})+'\n')
    publisher.MANIFEST.write_text(json.dumps({'schema_version':1,'questions':[entry]}))
    publisher.DEST.write_text(json.dumps(q)+'\n')
    assert publisher.publish()['published']==1
    changed={**q,'conteudo':{**q['conteudo'],'enunciado':'Unverified alteration'}}
    publisher.DEST.write_text(json.dumps(changed)+'\n')
    result=publisher.publish()
    assert result['published']==0 and result['quarantined']==['sample']
    publisher.DEST.write_text(json.dumps({**q,'id_unico_sistema':'unknown'})+'\n')
    import pytest
    with pytest.raises(ValueError,match='Unknown or duplicate'):
        publisher.publish()
