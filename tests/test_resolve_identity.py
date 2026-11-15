import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_identity_resolution_is_bound_to_official_sources_and_key():
    report = json.loads((ROOT / 'data/audit/identity-resolution.json').read_text())
    sources = json.loads((ROOT / 'data/audit/identity/sources.json').read_text())['sources']
    assert set(report['sources']) == {'2018', '2019', '2020', '2023', '2024', '2025'} == set(sources)
    for s in sources.values():
        assert s['url'].startswith('https://download.inep.gov.br/microdados/') and len(s['csv_sha256']) == 64
    assert len(report['items']) == 1015 and report['published_with_wrong_co_item'] == 157
    assert len(report['skipped_other_application']) == 35  # 2020 D2 digital
    resolved = [e for e in report['evidence'] if e['resolved']]
    assert len(resolved) == 24 and len(report['evidence']) == 24
    for e in resolved:
        assert e['candidates'][0]['ratio'] >= 0.97
        assert all(c['ratio'] <= 0.6 for c in e['candidates'][1:])
    # cada item resolvido vem de uma linha AZUL do ITENS_PROVA oficial e a resposta coincide com o gabarito do PDF
    for year in (2018, 2019, 2020, 2023, 2024, 2025):
        rows = list(csv.DictReader((ROOT / f'data/audit/identity/itens-prova-{year}-azul.csv').open(encoding='utf-8'), delimiter=';'))
        index = {(r['CO_PROVA'], r['CO_POSICAO'], r['SG_AREA']): r for r in rows}
        for uid, it in report['items'].items():
            if not uid.startswith(str(year)):
                continue
            row = index[(str(it['co_prova']), str(int(uid.rsplit('Q', 1)[1])), it['area'])]
            assert int(row['CO_ITEM']) == it['co_item'] and row['TX_GABARITO'] == it['tx_gabarito']
    mismatches = [u for u, it in report['items'].items() if it['official_key'] != it['tx_gabarito']]
    assert len(mismatches) == 7  # anulações oficiais: PDF 'Anulado'/sem letra, CSV 'X'
