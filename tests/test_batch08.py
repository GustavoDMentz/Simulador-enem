"""Batch 08 protects prior bytes, explicit decisions and visual dependencies."""
import copy
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from publish_blue_candidates import approved_record, record_digest


def load():
    report = json.loads((ROOT/'data/audit/batch-08-review.json').read_text())
    raw = (ROOT/'data/blue-published/questions.jsonl').read_bytes().splitlines(keepends=True)
    return report, {json.loads(line)['id_unico_sistema']:line for line in raw}


def test_all_185_have_a_decision_and_prior_328_are_byte_identical():
    report, raw = load()
    assert len(report['results']) == len({r['id'] for r in report['results']}) == 185
    assert Counter(r['classification'] for r in report['results']) == {'RECOVERABLE':181,'OFFICIALLY_ANNULLED':3,'IDENTITY_CONFLICT':1}
    assert len(report['previous_lines_sha256']) == 328
    for uid,digest in report['previous_lines_sha256'].items():
        assert hashlib.sha256(raw[uid]).hexdigest() == digest
    assert hashlib.sha256(b''.join(line for uid,line in raw.items() if uid in report['previous_records_sha256'])).hexdigest() == report['previous_catalog_sha256']
    assert len(raw) == report['approved_after'] == 509
    pending = [q for q in map(json.loads,(ROOT/'data/blue-published/preview-questions.jsonl').read_text().splitlines()) if q['id_unico_sistema'] not in raw]
    assert len(pending) == 4
    assert all(q['scoring_enabled'] is False and q['gabarito_oficial'] is None and q['parametros_tri'] is None for q in pending)


def test_recovered_records_match_fixed_decisions_and_all_image_hashes():
    report, raw = load()
    manifest = json.loads((ROOT/'data/audit/manifest.json').read_text())['questions']
    entries = {e['id']:e for e in manifest}
    for r in report['results']:
        if r['status'] != 'APPROVED':
            assert r['id'] not in raw and r['id'] not in entries
            continue
        q = json.loads(raw[r['id']])
        assert record_digest(q) == r['record_sha256']
        assert q['conteudo'] == r['after_content'] and q['gabarito_oficial'] == r['official_answer']
        assert all(r['visual_review'].values())
        assert approved_record(q,manifest,ROOT/'data/extracted')
        assert hashlib.sha256(r['source_text'].encode()).hexdigest() == r['source_text_sha256']
        for a in r['assets'].values():
            assert hashlib.sha256((ROOT/'data/extracted'/a['image'].removeprefix('/images/')).read_bytes()).hexdigest() == a['sha256']
        if r['presentation_metadata'].get('options'):
            assert set(r['presentation_metadata']['options']) == set('ABCDE')
            for letter,a in r['presentation_metadata']['options'].items():
                assert a['sha256'] == r['assets']['option_'+letter]['sha256']


def test_missing_or_corrupted_graphical_alternative_blocks_scoring():
    report,raw = load()
    r = next(r for r in report['results'] if r['id']=='2021_AZUL_D2_Q126')
    q = json.loads(raw[r['id']])
    entry = next(e for e in json.loads((ROOT/'data/audit/manifest.json').read_text())['questions'] if e['id']==r['id'])
    changed = copy.deepcopy(entry)
    changed['display_assets_sha256'][r['assets']['option_B']['image']] = '0'*64
    assert not approved_record(q,[changed],ROOT/'data/extracted')
    changed['display_assets_sha256']['/images/verified/missing-batch08.png'] = '1'*64
    assert not approved_record(q,[changed],ROOT/'data/extracted')


def test_digital_identity_and_annulments_are_application_specific():
    report,_ = load(); by_id = {r['id']:r for r in report['results']}
    assert by_id['2020_AZUL_D2_Q91']['application']=='digital'
    assert by_id['2020_AZUL_D2_Q91']['official_answer']=='D'
    assert by_id['2020_AZUL_D2_Q135']['status']=='APPROVED'
    assert by_id['2020_AZUL_D2_Q157']['classification']=='OFFICIALLY_ANNULLED'
    assert by_id['2024_AZUL_D1_Q04']['classification']=='IDENTITY_CONFLICT'
    repaired = [r for r in report['results'] if r.get('identity_reconciliation')]
    assert len(repaired)==13
    for r in repaired:
        assert r['identity_reconciliation']['original_identity']['id_unico_sistema']==r['id']
        assert r['identity_reconciliation']['original_identity']['posicao_prova']==r['number']
        assert r['before_content'] != r['after_content']


def test_command_boundaries_and_option_labels_do_not_erase_supports():
    report,_ = load(); rows = {r['id']:r for r in report['results']}
    assert rows['2019_AZUL_D2_Q124']['after_content']['enunciado']=='O composto A, representado no esquema de reação, é o'
    assert rows['2019_AZUL_D2_Q124']['assets']['support']['height']>250
    assert rows['2025_AZUL_D2_Q161']['assets']['support']['height']>700
    assert rows['2025_AZUL_D2_Q161']['after_content']['enunciado'].startswith('O quarteirão onde se encontra')
    assert rows['2024_AZUL_D1_Q29']['after_content']['enunciado'].startswith('Das reflexões')
    for r in report['results']:
        if r['status']!='APPROVED': continue
        for kind,a in r['assets'].items():
            if kind in ('support','figure'): assert min(a['width'],a['height'])>30
        if r['year'] in (2022,2023):
            c = r['after_content']
            assert not c['enunciado'].endswith(' A')
            for a,b in zip('ABCD','BCDE'): assert not c['alternativas'][a].endswith(' '+b)
