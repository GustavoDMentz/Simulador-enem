import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import resolve_identity  # noqa: E402


def test_identity_resolution_is_bound_to_official_sources_and_key():
    report = json.loads((ROOT / 'data/audit/identity-resolution.json').read_text())
    sources = json.loads((ROOT / 'data/audit/identity/sources.json').read_text())['sources']
    assert set(report['sources']) == {'2017', '2018', '2019', '2020', '2021', '2022', '2023', '2024', '2025'} == set(sources)
    for s in sources.values():
        assert s['url'].startswith('https://download.inep.gov.br/microdados/') and len(s['csv_sha256']) == 64
    assert len(report['items']) == 1577 and report['published_with_wrong_co_item'] == 160  # +37 de idioma (LC 1–5)
    assert report['language_resolution']['resolved'] == 37 and report['language_resolution']['published_with_wrong_co_item'] == 24 and not report['language_resolution']['unresolved']
    assert len(report['skipped_other_application']) == 35  # 2020 D2 digital
    resolved = [e for e in report['evidence'] if e['resolved']]
    assert len(resolved) == 36 and len(report['evidence']) == 36
    for e in resolved:
        assert e['candidates'][0]['ratio'] >= 0.97
        assert all(c['ratio'] <= 0.6 for c in e['candidates'][1:] if c['co_prova'] not in e['equivalent_co_prova'])
    # cada item resolvido vem de uma linha AZUL do ITENS_PROVA oficial e a resposta coincide com o gabarito do PDF
    for year in range(2017, 2026):
        rows = list(csv.DictReader((ROOT / f'data/audit/identity/itens-prova-{year}-azul.csv').open(encoding='utf-8'), delimiter=';'))
        groups = {}
        for r in rows:
            if r['SG_AREA'] == 'LC' and r['TP_LINGUA'] != '':
                continue
            groups.setdefault((r['CO_PROVA'], r['SG_AREA']), []).append(r)
        index = {}
        for (prova, area), rs in groups.items():
            gp = resolve_identity.global_pos(area, rs)
            for r in rs:
                index[(prova, str(gp[id(r)]), area)] = r
        for uid, it in report['items'].items():
            if not uid.startswith(str(year)):
                continue
            if 'lingua' in it:  # posições 1–5 de LC: linha da variante de idioma (TP_LINGUA 0 = inglês, 1 = espanhol)
                row = next(r for r in rows if r['CO_PROVA'] == str(it['co_prova']) and r['SG_AREA'] == 'LC'
                           and int(r['CO_POSICAO']) == int(uid.rsplit('Q', 1)[1]) and r['TP_LINGUA'] == {'ingles': '0', 'espanhol': '1'}[it['lingua']])
            else:
                row = index[(str(it['co_prova']), str(int(uid.rsplit('Q', 1)[1])), it['area'])]
            assert int(row['CO_ITEM']) == it['co_item'] and row['TX_GABARITO'] == it['tx_gabarito']
    mismatches = [u for u, it in report['items'].items() if it['official_key'] != it['tx_gabarito']]
    assert len(mismatches) == 9  # anulações oficiais: PDF 'Anulado'/sem letra, CSV 'X'
