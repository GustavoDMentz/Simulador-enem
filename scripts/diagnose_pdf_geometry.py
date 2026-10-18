#!/usr/bin/env python3
"""Detecta alternativas pelas linhas geométricas do PDF, sem publicar questões."""
from __future__ import annotations
import argparse
import json
import re
from collections import Counter
from pathlib import Path
import fitz

OPTION = re.compile(r'^[ \t]*([A-E])(?:[).]|[ \t]+)[ \t]*(\S.*)$')


def analyze(page: fitz.Page, bbox: list[float]) -> dict:
    rect = fitz.Rect(bbox)
    if rect.is_empty or not page.rect.contains(rect):
        raise ValueError('Recorte fora da página')
    hits = []
    for block in page.get_text('dict', clip=rect)['blocks']:
        if block.get('type') != 0:
            continue
        for line in block.get('lines', []):
            text = ''.join(span.get('text', '') for span in line.get('spans', []))
            if 'ENEM2024' in text:
                continue
            match = OPTION.match(text)
            if match:
                hits.append({'letter': match.group(1), 'text': match.group(2),
                             'bbox': [round(x, 2) for x in line['bbox']]})
    sequence = ''.join(hit['letter'] for hit in hits)
    return {'sequence': sequence, 'ABCDE_detected': 'ABCDE' in sequence,
            'exact_ABCDE': sequence == 'ABCDE', 'candidate_lines': hits,
            'publication_authorized': False}


def run(pdf_path: Path, review_path: Path, output_path: Path) -> dict:
    data = json.loads(review_path.read_text(encoding='utf-8'))
    records = data.get('records')
    if not isinstance(records, list):
        raise ValueError('Arquivo de revisão sem records')
    results = []
    with fitz.open(pdf_path) as pdf:
        for r in records:
            page = r.get('page')
            if not isinstance(page, int) or not 1 <= page <= len(pdf):
                raise ValueError(f'Página inválida: {page}')
            item = analyze(pdf[page - 1], r['bbox'])
            results.append({'id': r.get('id'), 'number': r.get('original_number'),
                            'page': page, **item})
    counts = Counter('exact_ABCDE' if r['exact_ABCDE'] else
                     'ABCDE_with_extra_markers' if r['ABCDE_detected'] else
                     'missing_ABCDE' for r in results)
    report = {'schema_version': 1, 'method': 'pdf-line-geometry-v1',
              'source_sha256': data.get('source_sha256'),
              'summary': dict(counts), 'results': results,
              'publication_authorized': False}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf', required=True, type=Path)
    parser.add_argument('--review', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.pdf, args.review, args.output)['summary'], ensure_ascii=False))


if __name__ == '__main__':
    main()
