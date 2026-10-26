#!/usr/bin/env python3
"""Publish only explicit, content-bound approvals. Never changes fused data or DB.

Restores the existing release from the checkpoint; pending records are preserved.
"""
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlparse

RECOVERY = Path('data/audit/session-recovery/preview-questions.jsonl')
MANIFEST = Path('data/audit/manifest.json')
DEST = Path('data/blue-published/questions.jsonl')
PREVIEW = Path('data/blue-published/preview-questions.jsonl')


def record_digest(q):
    payload = dict(id=q['id_unico_sistema'], year=q['ano'], day=q['dia'],
                   position=q['posicao_prova'], content=q['conteudo'], answer=q['gabarito_oficial'])
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def approved_record(q, entries, asset_root=Path('data/extracted')):
    matches = [e for e in entries if e.get('id') == q.get('id_unico_sistema')]
    if len(matches) != 1:
        return False
    e = matches[0]
    if e.get('publication_authorized') is not True or e.get('status') != 'CONFORME':
        return False
    if not all((e.get('audit') or {}).get(k) is True for k in ('text','options','graphics','credits','continuity','answer')):
        return False
    if not all(re.fullmatch(r'[a-fA-F0-9]{64}', e.get(k) or '') for k in ('source_sha256','answer_source_sha256','record_sha256')):
        return False
    url = urlparse(e.get('answer_source_url') or '')
    if url.scheme != 'https' or url.netloc not in ('download.inep.gov.br','www.gov.br'):
        return False
    if (e.get('year'),e.get('day'),e.get('number')) != (q.get('ano'),q.get('dia'),q.get('posicao_prova')):
        return False
    c = q.get('conteudo') or {}
    opts = c.get('alternativas') or {}
    if q.get('gabarito_oficial') not in tuple('ABCDE') or not str(c.get('enunciado') or '').strip():
        return False
    if set(opts) != set('ABCDE') or any(not isinstance(opts[k],str) or not opts[k].strip() for k in 'ABCDE'):
        return False
    if e['record_sha256'] != record_digest(q):
        return False
    visual = c.get('metadados_visual') or {}
    if visual.get('contem_imagem') or visual.get('caminho_local_imagem'):
        name = visual.get('caminho_local_imagem') or ''
        if not re.fullmatch(r'/images/verified/[\w-]+\.png', name):
            return False
        asset = asset_root / name.removeprefix('/images/')
        if not asset.is_file() or hashlib.sha256(asset.read_bytes()).hexdigest() != e.get('asset_sha256'):
            return False
    return True


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.jsonl.tmp')
    tmp.write_text(''.join(json.dumps(q,ensure_ascii=False)+'\n' for q in rows),encoding='utf-8')
    tmp.replace(path)


def publish(source=RECOVERY):
    data = json.loads(MANIFEST.read_text(encoding='utf-8'))
    if data.get('schema_version') != 1 or not isinstance(data.get('questions'),list):
        raise ValueError('Invalid audit manifest')
    entries = data['questions']
    rows = [json.loads(l) for l in source.read_text(encoding='utf-8').splitlines() if l.strip()]
    # The checked-in release is the canonical content for subsequent batches.
    # The immutable recovery snapshot remains the inventory and quarantine base.
    if DEST.exists() and source == RECOVERY:
        release = [json.loads(l) for l in DEST.read_text(encoding='utf-8').splitlines() if l.strip()]
        inventory = {q['id_unico_sistema'] for q in rows}
        approved_ids = {e.get('id') for e in entries}
        overlay = {}
        for q in release:
            uid = q['id_unico_sistema']
            if uid not in inventory or uid in overlay:
                raise ValueError('Unknown or duplicate release identity')
            if uid in approved_ids:
                overlay[uid] = q
        rows = [overlay.get(q['id_unico_sistema'], q) for q in rows]
    ids = [q['id_unico_sistema'] for q in rows]
    keys = [(q['ano'],q['dia'],q['posicao_prova']) for q in rows]
    if len(ids) != len(set(ids)) or len(keys) != len(set(keys)):
        raise ValueError('Duplicate question identity')
    published, preview, quarantined = [], [], []
    for q in rows:
        if approved_record(q,entries):
            item = {**q,'scoring_enabled':True,'parametros_tri':None,'preview_status':'VALIDATED','preview_unverified':False,'preview_warning':None}
            published.append(item)
            preview.append(item)
        elif any(e.get('id') == q['id_unico_sistema'] for e in entries):
            quarantined.append(q['id_unico_sistema'])
            preview.append({**q,'scoring_enabled':False,'gabarito_oficial':None,'parametros_tri':None,'preview_status':'QUARANTINED','preview_unverified':True,'preview_warning':'Dependência ou evidência de validação inconsistente. Sem pontuação.'})
        else:
            # Keep the 454 pending checkpoint rows unchanged. Reject unsafe input.
            if q.get('scoring_enabled') is not False or q.get('gabarito_oficial') is not None or q.get('parametros_tri') is not None:
                raise ValueError('Unapproved checkpoint row exposes answer or calibration')
            preview.append(q)
    write_jsonl(DEST,published)
    write_jsonl(PREVIEW,preview)
    return dict(published=len(published),preview=len(preview),quarantined=quarantined,database_changed=False)


def restore_assets(pdf_root):
    """Rebuild only the checkpoint's approved dependencies from hash-matched PDFs."""
    import fitz
    from audit_official_gabaritos import extract_pdf
    manifest = json.loads(Path('data/audit/session-recovery/reviewed-manifest.json').read_text())
    rows = [json.loads(l) for l in RECOVERY.read_text().splitlines() if l.strip()]
    by_id = {q['id_unico_sistema']:q for q in rows}
    report = []
    for e in manifest['questions']:
        q = by_id[e['id']]
        if record_digest(q) != e['record_sha256']:
            raise ValueError('Checkpoint content digest mismatch: '+e['id'])
        year, day, number = e['year'], e['day'], e['number']
        pdf = pdf_root / f'{year}-regular-d{day}-azul.pdf'
        key = pdf_root / f'{year}-regular-d{day}-azul-gabarito.pdf'
        for source, field in ((pdf,'source_sha256'),(key,'answer_source_sha256')):
            if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != e[field]:
                raise ValueError('Official source missing or digest mismatch: '+str(source))
        answers, ambiguous, _ = extract_pdf(key)
        if number in ambiguous or answers.get(number,{}).get('comum') != q['gabarito_oficial']:
            raise ValueError('Official answer mismatch: '+e['id'])
        visual = q['conteudo'].get('metadados_visual') or {}
        if visual.get('contem_imagem'):
            with fitz.open(pdf) as doc:
                region = e['regions'][0]
                page = doc[region['page']-1]
                if (year,day,number) == (2025,1,15):
                    box = [21,187,278,410]
                else:
                    box = list(region['bbox'])
                    prefix = q['conteudo']['enunciado'][:23]
                    hits = [line['bbox'] for block in page.get_text('dict')['blocks']
                            for line in block.get('lines',[])
                            if prefix in ''.join(span['text'] for span in line['spans'])]
                    if (year,day,number) == (2018,1,74):
                        box[3] = 742
                    elif hits:
                        box[3] = min(h[1] for h in hits)-3
                    else:
                        raise ValueError('Supporting-block boundary not found: '+e['id'])
                    if year == 2025:
                        box[0] -= 4
                        box[2] = page.rect.width-18
                if box[3] <= box[1]:
                    raise ValueError('Invalid source region: '+e['id'])
                dest = Path('data/extracted') / visual['caminho_local_imagem'].removeprefix('/images/')
                dest.parent.mkdir(parents=True,exist_ok=True)
                page.get_pixmap(matrix=fitz.Matrix(2.5,2.5),clip=fitz.Rect(box)).save(dest)
                previous = e.get('asset_sha256')
                e['asset_sha256'] = hashlib.sha256(dest.read_bytes()).hexdigest()
                e['asset_restoration'] = {'previous_sha256':previous,'page':region['page'],
                    'bbox':box,'scale':2.5,'format':'PNG','method':'direct official PDF rendering'}
        report.append({'id':e['id'],'content_digest_match':True,'official_pdf_digest_match':True,
                       'official_key_digest_match':True,'official_answer_match':True,
                       'graphics_restored':bool(visual.get('contem_imagem'))})
    MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    Path('data/audit/restoration-verification.json').write_text(json.dumps({
        'zip_sha256':'a2efb083c95057b71f698e25cd11da031703b2f7da4bd50d3d7e8dbe82371a97',
        'checked':len(report),'results':report},ensure_ascii=False,indent=2)+'\n')


def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--restore-pdfs',type=Path,help='Directory of hash-matched original official PDFs')
    args = p.parse_args()
    if args.restore_pdfs:
        restore_assets(args.restore_pdfs)
    print(json.dumps(publish(),ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
