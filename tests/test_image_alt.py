import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_question_presentation import GENERIC, norm  # noqa: E402

ROWS = {json.loads(l)['id_unico_sistema']: json.loads(l) for l in (ROOT / 'data/blue-published/questions.jsonl').read_text().splitlines()}
PRES = json.loads((ROOT / 'data/audit/question-presentation.json').read_text())['questions']
FMT = json.loads((ROOT / 'data/audit/support-text-format.json').read_text())


def test_every_visible_crop_with_a_generic_record_description_has_a_specific_alt():
    visible = [u for u, q in ROWS.items() if GENERIC.match(q['conteudo']['metadados_visual'].get('descricao_imagem') or '') and PRES[u]['mode'] != 'text']
    assert len(visible) == 675
    for uid in visible:
        q, alt = ROWS[uid], PRES[uid].get('alt', '')
        assert alt.startswith(f"Questão {q['posicao_prova']} do ENEM {q['ano']}, dia {q['dia']}, "), uid
        assert 'Recorte original da prova oficial' not in alt
        base = (q['conteudo']['texto_base'] or '').strip()
        if base:  # o texto-base, que a tela esconde dos leitores de tela, vem na descrição (só a forma dos caracteres pode mudar)
            assert norm(alt.split(' Texto-base: ', 1)[1]) == norm(base), uid


def test_formatted_support_text_only_changes_how_characters_look_and_never_edits_the_record():
    for uid, fields in FMT['questions'].items():
        base = ROWS[uid]['conteudo']['texto_base']
        text = base
        for old, new, count in fields['texto_base']:
            assert text.count(old) == count, (uid, old)
            text = text.replace(old, new)
        assert text != base and norm(text) == norm(base), uid
        assert re.sub(r'\s+', ' ', text) in PRES[uid]['alt'].replace('\n', ' ') or text.replace('\n\n', ' ') in PRES[uid]['alt'], uid
    for uid, alts in FMT['alternativas_transcritas'].items():
        assert set(alts) == set('ABCDE')
        assert all('reprodução gráfica oficial' in v for v in ROWS[uid]['conteudo']['alternativas'].values())  # o registro não guarda a fórmula
        assert all(f'{k}) {alts[k]};' in PRES[uid]['alt'] for k in 'ABCDE'), uid


def test_every_visible_crop_with_figures_is_either_described_or_declared_text_only():
    fig = json.loads((ROOT / 'data/audit/figure-descriptions.json').read_text())
    described, plain = set(fig['questions']), set(fig['sem_figura'])
    assert not described & plain and len(described) == 391 and len(plain) == 163
    for uid in described:
        v = fig['questions'][uid]
        assert v.get('figura') or v.get('alternativas'), uid
        alt = PRES[uid]['alt']
        assert 'não está descrito em texto' not in alt, uid
        if v.get('figura'):
            assert v['figura'].rstrip('.') in alt, uid
        placeholder = all('reprodução gráfica oficial' in t for t in ROWS[uid]['conteudo']['alternativas'].values())
        if v.get('alternativas') and placeholder and uid not in FMT['alternativas_transcritas']:
            assert set(v['alternativas']) == set('ABCDE'), uid
            assert all(v['alternativas'][k].rstrip('.;') in alt for k in 'ABCDE'), uid  # alternativas só em imagem: vão na descrição
    for uid in plain:
        assert uid in ROWS and 'sem figuras além do texto' in PRES[uid]['alt'], uid
    assert not [u for u, e in PRES.items() if 'não está descrito em texto' in e.get('alt', '')]
