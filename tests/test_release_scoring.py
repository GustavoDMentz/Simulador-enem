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
    assert len(release)==len(entries)==328
    assert len({q['id_unico_sistema'] for q in release})==328
    original=[q for q in snapshot if q['scoring_enabled']]
    current={q['id_unico_sistema']:q for q in release}
    assert len(original)==59
    assert all(current[q['id_unico_sistema']]=={**q,'parametros_tri':None,'preview_status':'VALIDATED','preview_unverified':False,'preview_warning':None} for q in original)
    for q in release:
        assert approved_record(q,entries,root/'data/extracted')
        assert q['parametros_tri'] is None
    pending=[(a,b) for a,b in zip(snapshot,preview) if not a['scoring_enabled'] and a['id_unico_sistema'] not in {q['id_unico_sistema'] for q in release}]
    assert len(pending)==185
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


def test_batch_03_preserves_all_97_previous_approvals():
    root=Path(__file__).resolve().parents[1]
    batch2=json.loads((root/'data/audit/batch-02-review.json').read_text())
    current={q['id_unico_sistema']:q for q in map(json.loads,(root/'data/blue-published/questions.jsonl').read_text().splitlines())}
    for row in batch2['results']:
        if row['status']=='APPROVED':
            assert current[row['id']]['conteudo']==row['after_content']
            assert current[row['id']]['gabarito_oficial']==row['official_answer']
    batch3=json.loads((root/'data/audit/batch-03-review.json').read_text())
    assert batch3['examined']==50 and batch3['newly_approved']==47
    assert sum(bool(row.get('accessible_support')) for row in batch3['results'])==30
    for row in batch3['results']:
        if row['status']=='PENDING':
            assert row['id'] not in current


def test_batch_04_preserves_all_144_previous_approvals():
    root=Path(__file__).resolve().parents[1]
    current={q['id_unico_sistema']:q for q in map(json.loads,(root/'data/blue-published/questions.jsonl').read_text().splitlines())}
    for batch in ['batch-02-review.json','batch-03-review.json']:
        for row in json.loads((root/'data/audit'/batch).read_text())['results']:
            if row['status']=='APPROVED':
                assert current[row['id']]['conteudo']==row['after_content']
                assert current[row['id']]['gabarito_oficial']==row['official_answer']
    report=json.loads((root/'data/audit/batch-04-review.json').read_text())
    assert report['examined']==50 and report['newly_approved']==46
    assert sum(bool(row.get('accessible_support')) for row in report['results'])==29
    for row in report['results']:
        if row['status']=='PENDING':
            assert row['id'] not in current


def test_batch_05_preserves_all_190_previous_approvals():
    root=Path(__file__).resolve().parents[1]
    current={q['id_unico_sistema']:q for q in map(json.loads,(root/'data/blue-published/questions.jsonl').read_text().splitlines())}
    for batch in ['batch-02-review.json','batch-03-review.json','batch-04-review.json']:
        for row in json.loads((root/'data/audit'/batch).read_text())['results']:
            if row['status']=='APPROVED':
                assert current[row['id']]['conteudo']==row['after_content']
                assert current[row['id']]['gabarito_oficial']==row['official_answer']
    report=json.loads((root/'data/audit/batch-05-review.json').read_text())
    assert report['examined']==50 and report['newly_approved']==48
    assert sum(bool(row.get('accessible_support')) for row in report['results'])==20
    for row in report['results']:
        if row['status']=='PENDING':
            assert row['id'] not in current


def test_batch_06_preserves_238_and_binds_50_source_review_decisions():
    import hashlib
    root=Path(__file__).resolve().parents[1]
    report=json.loads((root/'data/audit/batch-06-review.json').read_text())
    raw=(root/'data/blue-published/questions.jsonl').read_text().splitlines(keepends=True)
    rows={json.loads(line)['id_unico_sistema']:json.loads(line) for line in raw}
    prior=report['previous_records_sha256']
    assert len(prior)==238
    previous=''.join(line for line in raw if json.loads(line)['id_unico_sistema'] in prior)
    assert hashlib.sha256(previous.encode()).hexdigest()==report['previous_catalog_sha256']
    assert report['examined']==report['newly_approved']==50
    for result in report['results']:
        q=rows[result['id']]
        assert result['id'] not in prior
        assert q['conteudo']==result['after_content']
        assert q['gabarito_oficial']==result['official_answer']
        assert record_digest(q)==result['record_sha256']
        assert hashlib.sha256(result['source_text'].encode()).hexdigest()==result['source_text_sha256']
        assert all(result['visual_review'][k] for k in ['text','options','graphics','credits','continuity','answer'])
    assert sum(r['presentation']=='text' for r in report['results'])==47
    assert sum(r['presentation']=='composition' for r in report['results'])==3


def test_batch_07_preserves_288_and_all_explicit_review_decisions():
    import hashlib
    import re
    from collections import Counter
    root=Path(__file__).resolve().parents[1]
    report=json.loads((root/'data/audit/batch-07-review.json').read_text())
    raw=(root/'data/blue-published/questions.jsonl').read_text().splitlines(keepends=True)
    rows={json.loads(line)['id_unico_sistema']:json.loads(line) for line in raw}
    prior=report['previous_records_sha256']
    assert len(prior)==288
    previous=''.join(line for line in raw if json.loads(line)['id_unico_sistema'] in prior)
    assert hashlib.sha256(previous.encode()).hexdigest()==report['previous_catalog_sha256']
    assert report['examined']==50 and report['newly_approved']==40
    approved=[r for r in report['results'] if r['status']=='APPROVED']
    held=[r for r in report['results'] if r['status']=='PENDING']
    assert len(held)==10 and all(r['id'] not in rows for r in held)
    assert Counter(r['area'] for r in approved)=={'CN':26,'MT':14}
    for r in approved:
        q=rows[r['id']]
        assert r['id'] not in prior and q['conteudo']==r['after_content']
        assert q['gabarito_oficial']==r['official_answer']
        assert record_digest(q)==r['record_sha256']
        assert hashlib.sha256(r['source_text'].encode()).hexdigest()==r['source_text_sha256']
        assert not re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]',str(q['conteudo'])+str(r['presentation_metadata']))
    assert rows['2021_AZUL_D2_Q92']['conteudo']['alternativas']['D']=='f₁ > f₂ e v₁ = v₂.'
    assert rows['2021_AZUL_D2_Q136']['conteudo']['alternativas']['E']=='13φ + 8'
    assert rows['2022_AZUL_D2_Q129']['conteudo']['alternativas']['C']=='NH₄⁺'
    assert '√3' in next(r for r in approved if r['id']=='2021_AZUL_D2_Q169')['presentation_metadata']['after']
