import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from publish_blue_candidates import approved_record, record_digest  # noqa: E402


IDENT = json.loads((ROOT / 'data/audit/identity-resolution.json').read_text())['items']


def load():
    report = json.loads((ROOT / 'data/audit/batch-21-review.json').read_text())
    raw = {json.loads(l)['id_unico_sistema']: l for l in (ROOT / 'data/blue-published/questions.jsonl').read_bytes().splitlines(keepends=True)}
    return report, raw


def test_batch_21_adds_33_new_identities_and_keeps_1101_previous_lines_byte_identical():
    report, raw = load()
    assert report['approved_before'] == 1218 and report['newly_approved'] == 54 and report['approved_after'] == 1272
    assert len(report['results']) == len({r['id'] for r in report['results']}) == 54
    assert len(report['previous_lines_sha256']) == 1218
    for uid, digest in report['previous_lines_sha256'].items():
        assert hashlib.sha256(raw[uid]).hexdigest() == digest
    assert len(raw) >= 1272


def test_each_new_record_is_content_bound_text_only_and_has_its_crop():
    report, raw = load()
    entries = {e['id']: e for e in json.loads((ROOT / 'data/audit/manifest.json').read_text())['questions']}
    for r in report['results']:
        q = json.loads(raw[r['id']])
        e = entries[r['id']]
        assert r['status'] == 'APPROVED' and r['visual_review'] and all(r['visual_review'].values())
        assert approved_record(q, list(entries.values()), ROOT / 'data/extracted')
        assert record_digest(q) == r['record_sha256'] == e['record_sha256']
        ident = IDENT[r['id']]
        assert q['gabarito_oficial'] == r['official_answer'] == r['identity_reconciliation']['tx_gabarito'] == ident['tx_gabarito'] == ident['official_key']
        assert q['co_item'] == ident['co_item'] == r['identity_reconciliation']['co_item']
        assert q['parametros_tri'] is None and q['scoring_enabled'] is True
        assert q['conteudo'] == r['after_content'] and set(q['conteudo']['alternativas']) == set('ABCDE')
        asset = r['assets']['source']
        assert hashlib.sha256((ROOT / 'data/extracted' / asset['image'].removeprefix('/images/')).read_bytes()).hexdigest() == asset['sha256']
        assert r['presentation_metadata']['mode'] == 'composition' and r['presentation_metadata']['includes_command'] is True and all(f.split(':')[0] in ('imagens', 'desenhos', 'comando_por_ultima_frase', 'possivel_poesia', 'numeracao_de_linhas', 'hifen_fim_de_linha', 'caractere_estranho_ou_ligadura', 'continua_em_outra_coluna_ou_pagina') for f in r['parser_flags'])


def test_new_identities_enter_the_inventory_as_pending_rows_only():
    report, _ = load()
    snap = {json.loads(l)['id_unico_sistema']: json.loads(l) for l in (ROOT / 'data/audit/session-recovery/preview-questions.jsonl').read_text().splitlines()}
    for r in report['results']:
        row = snap[r['id']]
        assert row['gabarito_oficial'] is None and row['scoring_enabled'] is False and row['parametros_tri'] is None
        assert row == r['pending_row']
