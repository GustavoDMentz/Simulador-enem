#!/usr/bin/env python3
"""Strict, reproducible join of Inep ITENS_PROVA CSV with published ENEM catalog.
Usage: python scripts/import_official_tri.py ITENS_PROVA_2023.csv --year 2023
Outputs a review report; no question data is modified. Does NOT modify published data.
"""
import argparse, csv, json, math, pathlib, collections

ROOT = pathlib.Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'data/blue-published/questions.jsonl'

def num(v):
    v = str(v or '').strip().replace(',', '.')
    try:
        n = float(v)
        return n if math.isfinite(n) else None
    except ValueError:
        return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('csv', type=pathlib.Path)
    ap.add_argument('--year', type=int, required=True)
    ap.add_argument('--output', type=pathlib.Path, default=ROOT / 'data/audit/tri-import-review.json')
    args = ap.parse_args()
    questions = [json.loads(x) for x in CATALOG.read_text().splitlines() if x.strip()]
    with args.csv.open(encoding='latin-1', newline='') as f:
        sample = f.read(8192); f.seek(0)
        delimiter = ';' if sample.splitlines()[0].count(';') >= sample.splitlines()[0].count(',') else ','
        reader = csv.DictReader(f, delimiter=delimiter)
        required={'CO_ITEM','SG_AREA','TX_GABARITO','NU_PARAM_A','NU_PARAM_B','NU_PARAM_C','IN_ITEM_ABAN'}
        missing=required-set(reader.fieldnames or [])
        if missing: raise SystemExit('Missing required columns: '+', '.join(sorted(missing)))
        rows = list(reader)
    by_item = collections.defaultdict(list)
    for r in rows:
        by_item[str(r.get('CO_ITEM', '')).strip()].append(r)
    report = {'year':args.year,'source_file':str(args.csv),'source_rows':len(rows),'matched':[],'blocked':[]}
    for q in questions:
        if q.get('ano') != args.year or q.get('scoring_enabled') is not True: continue
        matches = by_item.get(str(q.get('co_item')), [])
        eligible = []
        for r in matches:
            if r.get('SG_AREA','').strip() != q.get('area_conhecimento'): continue
            if r.get('TX_GABARITO','').strip().upper() != q.get('gabarito_oficial'): continue
            if str(r.get('IN_ITEM_ABAN','0')).strip() not in ('','0'): continue
            a,b,c = [num(r.get('NU_PARAM_'+k)) for k in 'ABC']
            if any(x is None for x in (a,b,c)) or not (a>0 and 0<=c<=1): continue
            eligible.append((a,b,c))
        unique = set(eligible)
        if len(unique)==1 and len(eligible)==len(matches):
            a,b,c=next(iter(unique))
            report['matched'].append({'id':q['id_unico_sistema'],'co_item':q['co_item'],'a':a,'b':b,'c':c,'source':'INEP ITENS_PROVA','review_required':True,'source_rows':len(matches)})
        else:
            report['blocked'].append({'id':q['id_unico_sistema'],'co_item':q.get('co_item'),'reason':'no unique compatible parameter triple','source_matches':len(matches),'eligible':len(eligible)})
    report['counts']={'matched':len(report['matched']),'blocked':len(report['blocked'])}
    report['warning']='Candidates require manual source and identity verification before publication; no TRI values were imported.'
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report['counts']))

if __name__=='__main__': main()
