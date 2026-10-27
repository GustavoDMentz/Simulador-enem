#!/usr/bin/env python3
"""Apply the fixed, source-reviewed batch 07 decisions; never writes to a database.

Requires the original PDFs with the hashes recorded in batch-07-review.json.
This is a replay of explicit review decisions, not an automatic approval pipeline.
"""
import argparse
import copy
import hashlib
import json
import re
from pathlib import Path

from audit_official_gabaritos import extract_pdf
from publish_blue_candidates import record_digest, publish, write_jsonl


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized(text):
    return re.sub(r'\s+', ' ', text).strip()


def apply(pdf_root):
    import fitz
    report = json.loads(Path('data/audit/batch-07-review.json').read_text())
    sources = {s['year']:s for s in report['sources']}
    for year, source in sources.items():
        assert sha(pdf_root/f'{year}-d2.pdf') == source['source_sha256'], 'Booklet digest mismatch'
        assert sha(pdf_root/f'{year}-key.pdf') == source['answer_key_sha256'], 'Key digest mismatch'
    release_path = Path('data/blue-published/questions.jsonl')
    release = list(map(json.loads, release_path.read_text().splitlines()))
    by_id = {q['id_unico_sistema']: q for q in release}
    for uid, digest in report['previous_records_sha256'].items():
        assert record_digest(by_id[uid]) == digest, 'Previous approval changed: '+uid
    snapshot = {q['id_unico_sistema']: q for q in map(json.loads, Path('data/audit/session-recovery/preview-questions.jsonl').read_text().splitlines())}
    manifest_path = Path('data/audit/manifest.json')
    manifest = json.loads(manifest_path.read_text())
    entries = {e['id']: e for e in manifest['questions']}
    decisions, additions = [], []
    for result in report['results']:
        if result['status'] != 'APPROVED':
            continue
        year = result['year']
        source = sources[year]
        answers, ambiguous, _ = extract_pdf(pdf_root/f'{year}-key.pdf')
        assert not ambiguous
        with fitz.open(pdf_root/f'{year}-d2.pdf') as document:
            uid = result['id']
            q = copy.deepcopy(snapshot[uid])
            assert q['conteudo'] == result['before_content']
            number = q['posicao_prova']
            assert answers[number]['comum'] == result['official_answer']
            text = '\n'.join(document[r['page']-1].get_text(clip=fitz.Rect(r['bbox'])) for r in result['regions'])
            text = re.sub(r'^(?:QUESTÃO|Questão)\s*\d+\s*\n', '', text)
            assert hashlib.sha256(text.encode()).hexdigest() == result['source_text_sha256']
            assert text == result['source_text']
            content = result['after_content']
            # Fixed visual-review decisions: encoded PDF text is not a fidelity proof.
            # Bind the exact original source regions and reconstruct their original pixels.
            assert all(result['visual_review'][k] for k in ['text','options','graphics','credits','continuity','answer'])
            assert set(content['alternativas']) == set('ABCDE')
            render = result['support_render']
            pixmaps = [document[r['page']-1].get_pixmap(matrix=fitz.Matrix(render['scale'],render['scale']),clip=fitz.Rect(r['bbox']),alpha=False) for r in render['regions']]
            if len(pixmaps) == 1:
                combined = pixmaps[0]
            else:
                combined = fitz.Pixmap(fitz.csRGB,(0,0,max(p.width for p in pixmaps),sum(p.height for p in pixmaps)),False)
                combined.clear_with(255)
                top = 0
                for pixmap in pixmaps:
                    pixmap.set_origin(0,top)
                    combined.copy(pixmap,pixmap.irect)
                    top += pixmap.height
            asset = Path('data/extracted')/content['metadados_visual']['caminho_local_imagem'].removeprefix('/images/')
            combined.save(asset)
            assert sha(asset) == result['asset_sha256'], 'Rendered support differs'
            q.update(conteudo=content, gabarito_oficial=result['official_answer'])
            assert record_digest(q) == result['record_sha256']
            if uid in by_id:
                assert record_digest(by_id[uid]) == record_digest(q)
                continue
            entry = dict(id=uid,year=year,day=2,number=number,status='CONFORME',publication_authorized=True,
                source_sha256=source['source_sha256'],source_url=source['source_url'],
                source_index_url=f'https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enem/provas-e-gabaritos/{year}',
                answer_source_sha256=source['answer_key_sha256'],answer_source_url=source['answer_key_url'],
                record_sha256=record_digest(q),audit=dict.fromkeys(['text','options','graphics','credits','continuity','answer'],True),
                reviewed_at='2026-10-26',reviewer='source-region visual comparison in ChatGPT Work',
                regions=result['regions'],note='Batch 07: complete source pages and key visually compared; PDF words, A–E, credits and continuity checked. No TRI.')
            if result['asset_sha256']:
                entry.update(asset_sha256=result['asset_sha256'],support_render=result['support_render'])
            assert uid not in entries
            decisions.append(entry)
            additions.append(q)
    manifest['questions'].extend(decisions)
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    write_jsonl(release_path,release+additions)
    result = publish()
    assert result['published'] == report['approved_after'] and not result['quarantined']
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf-root',type=Path,required=True)
    args = parser.parse_args()
    print(json.dumps(apply(args.pdf_root),indent=2))
