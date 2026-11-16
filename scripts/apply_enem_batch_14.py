#!/usr/bin/env python3
"""Replay the batch 14 decisions (questions with figures: original crops from the official PDFs); no database access.

Requires the unmodified official PDFs recorded in batch-14-review.json (SHA-256 checked).
Every item is bound to its original PDF region, official answer key and final content;
extraction never authorizes anything by itself. Batch 14 also extends the checkpoint
inventory with the new identities as pending rows before approving them.
"""
import argparse
import copy
import hashlib
import json
from io import BytesIO
from pathlib import Path

from audit_official_gabaritos import extract_pdf
from publish_blue_candidates import record_digest, publish, write_jsonl

REPORT = Path('data/audit/batch-14-review.json')
SNAPSHOT = Path('data/audit/session-recovery/preview-questions.jsonl')
REVIEWER = 'Official PDF text layer + answer key + ITENS_PROVA identity; region contact-sheet visual confirmation (Claude Code)'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def render_asset(document, asset):
    import fitz
    from PIL import Image
    fitz.TOOLS.store_shrink(100)
    panels = []
    for region in asset['render']:
        s = region['scale']
        pix = document[region['page']-1].get_pixmap(matrix=fitz.Matrix(s, s), clip=fitz.Rect(region['bbox']), alpha=False)
        panels.append(Image.frombytes('RGB', (pix.width, pix.height), pix.samples).crop(tuple(region['pixel_trim'])))
    image = Image.new('RGB', (max(p.width for p in panels), sum(p.height for p in panels)), 'white')
    top = 0
    for panel in panels:
        image.paste(panel, (0, top)); top += panel.height
    buffer = BytesIO(); image.save(buffer, format='PNG')
    data = buffer.getvalue()
    assert sha(data) == asset['sha256'], 'Rendered pixels differ: ' + asset['image']
    assert image.size == (asset['width'], asset['height'])
    return data


def apply(pdf_root):
    import fitz
    report = json.loads(REPORT.read_text())
    release_path = Path('data/blue-published/questions.jsonl')
    lines = release_path.read_bytes().splitlines(keepends=True)
    release = [json.loads(line) for line in lines]
    by_id = {q['id_unico_sistema']: q for q in release}
    raw_by_id = {q['id_unico_sistema']: line for q, line in zip(release, lines)}
    for uid, digest in report['previous_lines_sha256'].items():
        assert uid in by_id and sha(raw_by_id[uid]) == digest, 'Previous release bytes changed: ' + uid

    # 1) inventory: new identities enter as pending rows (no answer, no score, no TRI)
    snap_lines = SNAPSHOT.read_bytes().splitlines(keepends=True)
    snapshot = {json.loads(l)['id_unico_sistema']: json.loads(l) for l in snap_lines}
    appended = []
    for result in report['results']:
        row = result['pending_row']
        assert row['gabarito_oficial'] is None and row['scoring_enabled'] is False and row['parametros_tri'] is None
        if result['id'] in snapshot:
            assert snapshot[result['id']] == row, 'Inventory row changed: ' + result['id']
        else:
            appended.append((json.dumps(row, ensure_ascii=False) + '\n').encode())
            snapshot[result['id']] = row
    if appended:
        SNAPSHOT.write_bytes(b''.join(snap_lines) + b''.join(appended))
    keys = [(q['ano'], q['dia'], q['posicao_prova']) for q in snapshot.values()]
    assert len(keys) == len(set(keys)), 'Duplicate position in inventory'

    manifest_path = Path('data/audit/manifest.json')
    manifest = json.loads(manifest_path.read_text()); entries = {e['id']: e for e in manifest['questions']}
    additions, decisions, checked, keymaps = [], [], set(), {}
    for result in report['results']:
        source = result['source']; pdf = pdf_root / result['source_file']; key = pdf_root / result['key_file']
        for file, field in [(pdf, 'source_sha256'), (key, 'answer_source_sha256')]:
            if file not in checked:
                assert sha(file.read_bytes()) == source[field], 'Official source mismatch: ' + str(file)
                checked.add(file)
        if key not in keymaps:
            keymaps[key] = extract_pdf(key)
        answers, ambiguous, _ = keymaps[key]
        number = result['number']
        assert number not in ambiguous and result['language'] is None
        answer = answers[number]['comum']
        assert answer == result['official_answer'], 'Official answer mismatch: ' + result['id']
        ident = json.loads(Path('data/audit/identity-resolution.json').read_text())['items'][result['id']]
        assert answer == ident['tx_gabarito'] == result['identity_reconciliation']['tx_gabarito'], 'Identity not corroborated: ' + result['id']
        assert result['pending_row']['co_item'] == ident['co_item'] == result['identity_reconciliation']['co_item'], 'CO_ITEM differs from resolved identity: ' + result['id']
        assert result['status'] == 'APPROVED' and result['classification'] == 'RECOVERABLE'
        assert all(result['visual_review'][k] is True for k in ['text', 'options', 'graphics', 'credits', 'continuity', 'answer'])
        content = result['after_content']
        assert set(content['alternativas']) == set('ABCDE') and all(content['alternativas'][k].strip() for k in 'ABCDE')
        with fitz.open(pdf) as document:
            text = '\n'.join(document[r['page']-1].get_text(clip=fitz.Rect(r['bbox'])) for r in result['regions'])
            assert sha(text.encode()) == result['source_text_sha256'] and text == result['source_text']
            q = copy.deepcopy(snapshot[result['id']]); assert q['conteudo'] == result['before_content']
            q.update(conteudo=content, gabarito_oficial=answer, parametros_tri=None)
            assert record_digest(q) == result['record_sha256']
            asset = result['assets']['source']
            assert asset['image'].startswith('/images/verified/batch14-')
            assert content['metadados_visual']['caminho_local_imagem'] == asset['image']
            data = render_asset(document, asset)
            path = Path('data/extracted') / asset['image'].removeprefix('/images/')
            path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        if result['id'] in by_id:
            assert record_digest(by_id[result['id']]) == result['record_sha256']
            continue
        assert result['id'] not in entries
        decisions.append(dict(id=result['id'], year=result['year'], day=result['day'], number=number,
            application=result['application'], language=result['language'], status='CONFORME', publication_authorized=True,
            **{k: v for k, v in source.items() if k not in ('year', 'day')}, record_sha256=result['record_sha256'],
            audit=result['visual_review'], asset_sha256=asset['sha256'], display_assets_sha256={asset['image']: asset['sha256']},
            reviewed_at='2026-11-15', reviewer=REVIEWER, regions=result['regions'], evidence=str(REPORT),
            note='Batch 14: figure region (original crop) from the official PDF; answer from the official key; CO_ITEM resolved from the official ITENS_PROVA. No TRI.'))
        additions.append(q)
    manifest['questions'].extend(decisions)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    write_jsonl(release_path, release + additions)
    result = publish()
    assert result['published'] == report['approved_after'] and not result['quarantined']
    actual = {json.loads(line)['id_unico_sistema']: line for line in release_path.read_bytes().splitlines(keepends=True)}
    assert all(sha(actual[uid]) == digest for uid, digest in report['previous_lines_sha256'].items())
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf-root', type=Path, default=Path('data/enem-pdfs/oficiais'))
    print(json.dumps(apply(parser.parse_args().pdf_root), indent=2))
