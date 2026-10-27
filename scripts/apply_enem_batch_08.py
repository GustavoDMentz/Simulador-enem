#!/usr/bin/env python3
"""Replay the individually reviewed batch 08 decisions, without database access.

Requires unmodified official PDFs named as recorded in batch-08-review.json.
Automatic extraction never authorizes an item: all approvals are fixed decisions
bound to original PDF regions, source hashes, visual checks and final content.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from audit_official_gabaritos import extract_pdf
from publish_blue_candidates import record_digest, publish, write_jsonl

REPORT = Path('data/audit/batch-08-review.json')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def render_asset(document, asset):
    import fitz
    from PIL import Image
    # MuPDF's cached downsampled images depend on earlier clip sizes. Evict the
    # cache so replay order cannot change the original image resampling.
    fitz.TOOLS.store_shrink(100)
    panels = []
    for region in asset['render']:
        scale = region['scale']
        pix = document[region['page']-1].get_pixmap(matrix=fitz.Matrix(scale,scale),
            clip=fitz.Rect(region['bbox']),alpha=False)
        panel = Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
        panels.append(panel.crop(tuple(region['pixel_trim'])))
    image = Image.new('RGB',(max(p.width for p in panels),sum(p.height for p in panels)),'white')
    top = 0
    for panel in panels:
        image.paste(panel,(0,top)); top += panel.height
    from io import BytesIO
    buffer = BytesIO(); image.save(buffer,format='PNG')
    data = buffer.getvalue()
    assert sha(data) == asset['sha256'], 'Rendered pixels differ: '+asset['image']
    assert image.size == (asset['width'],asset['height'])
    return data


def apply(pdf_root):
    import fitz
    report = json.loads(REPORT.read_text())
    release_path = Path('data/blue-published/questions.jsonl')
    lines = release_path.read_bytes().splitlines(keepends=True)
    release = [json.loads(line) for line in lines]
    by_id = {q['id_unico_sistema']:q for q in release}
    raw_by_id = {q['id_unico_sistema']:line for q,line in zip(release,lines)}
    for uid,digest in report['previous_records_sha256'].items():
        assert record_digest(by_id[uid]) == digest, 'Previous content changed: '+uid
        assert sha(raw_by_id[uid]) == report['previous_lines_sha256'][uid], 'Previous bytes changed: '+uid
    snapshot = {q['id_unico_sistema']:q for q in map(json.loads,Path('data/audit/session-recovery/preview-questions.jsonl').read_text().splitlines())}
    manifest_path = Path('data/audit/manifest.json')
    manifest = json.loads(manifest_path.read_text()); entries = {e['id']:e for e in manifest['questions']}
    additions, decisions = [], []
    checked = set(); keys = {}
    for result in report['results']:
        source = result['source']; pdf = pdf_root/result['source_file']; key = pdf_root/result['key_file']
        for file,field in [(pdf,'source_sha256'),(key,'answer_source_sha256')]:
            if file not in checked:
                assert sha(file.read_bytes()) == source[field], 'Official source mismatch: '+str(file)
                checked.add(file)
        if key not in keys: keys[key] = extract_pdf(key)
        answers, ambiguous, _ = keys[key]
        number = result['number']; language = result['language'] or 'comum'
        assert number not in ambiguous
        answer = answers[number][language]
        assert answer == result['official_answer'], 'Official answer mismatch: '+result['id']
        if result['status'] != 'APPROVED':
            assert result['id'] not in entries, 'Blocked item was authorized'
            continue
        assert result['classification'] == 'RECOVERABLE'
        assert all(result['visual_review'][k] is True for k in ['text','options','graphics','credits','continuity','answer'])
        with fitz.open(pdf) as document:
            text = '\n'.join(document[r['page']-1].get_text(clip=fitz.Rect(r['bbox'])) for r in result['regions'])
            assert sha(text.encode()) == result['source_text_sha256'] and text == result['source_text']
            q = copy.deepcopy(snapshot[result['id']]); assert q['conteudo'] == result['before_content']
            q.update(conteudo=result['after_content'],gabarito_oficial=answer)
            assert record_digest(q) == result['record_sha256']
            dependencies = {}
            for asset in result['assets'].values():
                assert asset['image'].startswith('/images/verified/batch08-')
                data = render_asset(document,asset)
                path = Path('data/extracted')/asset['image'].removeprefix('/images/')
                path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(data)
                dependencies[asset['image']] = asset['sha256']
        if result['id'] in by_id:
            assert record_digest(by_id[result['id']]) == result['record_sha256']
            assert entries[result['id']]['display_assets_sha256'] == dependencies
            continue
        assert result['id'] not in entries
        decisions.append(dict(id=result['id'],year=result['year'],day=result['day'],number=number,
            application=result['application'],language=result['language'],status='CONFORME',publication_authorized=True,
            **{k:v for k,v in source.items() if k not in ('year','day')},record_sha256=result['record_sha256'],audit=result['visual_review'],
            asset_sha256=result['assets']['source']['sha256'],display_assets_sha256=dependencies,
            reviewed_at='2026-10-27',reviewer='Official PDF pixel and key comparison in ChatGPT Work',
            regions=result['regions'],evidence=str(REPORT),note='Batch 08 fixed individual decision; no TRI. See full before/after, original regions and identity reconciliation in report.'))
        additions.append(q)
    manifest['questions'].extend(decisions)
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    write_jsonl(release_path,release+additions)
    result = publish()
    assert result['published'] == report['approved_after'] and not result['quarantined']
    actual = {json.loads(line)['id_unico_sistema']:line for line in release_path.read_bytes().splitlines(keepends=True)}
    assert all(sha(actual[uid]) == digest for uid,digest in report['previous_lines_sha256'].items())
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf-root',type=Path,required=True)
    print(json.dumps(apply(parser.parse_args().pdf_root),indent=2))
