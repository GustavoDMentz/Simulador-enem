#!/usr/bin/env python3
"""Rebuild reviewed display metadata without modifying audited records or answers."""
import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from publish_blue_candidates import record_digest
ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT/'data/audit/question-presentation.json'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

GENERIC=re.compile(r'^Recorte original da prova oficial \(texto, ')
AREAS={'LC':'Linguagens, Códigos e suas Tecnologias','CH':'Ciências Humanas e suas Tecnologias','CN':'Ciências da Natureza e suas Tecnologias','MT':'Matemática e suas Tecnologias'}
FORMAT=ROOT/'data/audit/support-text-format.json'
FIGURES=ROOT/'data/audit/figure-descriptions.json'
def norm(text):
    """Forma comparável: NFKC, menos e fração unificados, sem '^' nem espaços (só a forma dos caracteres pode mudar)."""
    return re.sub(r'\s+','',unicodedata.normalize('NFKC',text).replace('\u2212','-').replace('\u2044','/').replace('^',''))
def formatted(uid,field,text,spec):
    for old,new,count in spec.get(uid,{}).get(field,[]):
        assert text.count(old)==count,(uid,old,text.count(old))
        text=text.replace(old,new)
    return text
def plural(n,um,varios): return f"{n} {um if n==1 else varios}"
def describe(q,flags,spec,transcribed,figures):
    """Descrição específica do recorte (alt): o que a imagem traz e o texto-base, que a tela esconde dos leitores de tela."""
    c=q['conteudo'];base=(c.get('texto_base') or '').strip();uid=q['id_unico_sistema']
    shown=''
    if base:
        shown=formatted(uid,'texto_base',base,spec)
        assert norm(shown)==norm(base),('A formatação alterou o texto',uid)
    n=sum(int(f.split(':')[1]) for f in flags if f.startswith('imagens:'))
    parts=(['texto-base'] if base else [])+['comando','alternativas A a E']
    figs=([plural(n,'imagem ou fotografia','imagens ou fotografias')] if n else [])+(['desenhos vetoriais (gráficos, esquemas, tabelas ou quadros)'] if any(f.startswith('desenhos:') for f in flags) else [])
    fig=figures['questions'].get(uid);plain=uid in figures['sem_figura']
    out=f"Questão {q['posicao_prova']} do ENEM {q['ano']}, dia {q['dia']}, {AREAS.get(q['area_conhecimento'],q['area_conhecimento'])}. Reprodução do caderno oficial com {', '.join(parts[:-1])} e {parts[-1]}"
    if fig and fig.get('figura'): out+='. Figura: '+fig['figura'].rstrip('.')
    elif fig: pass  # só as alternativas são figuras (descritas abaixo)
    elif plain: out+=', sem figuras além do texto'
    elif figs: out+=f", além de {' e '.join(figs)}. O conteúdo visual das figuras não está descrito em texto: use Ampliar para vê-lo"
    out+='. O comando e as alternativas também estão disponíveis em texto fora da imagem.'
    if all('reprodução gráfica oficial' in v for v in c['alternativas'].values()):
        if uid in transcribed:
            assert set(transcribed[uid])==set('ABCDE')
            out+=' As alternativas são fórmulas, transcritas da imagem: '+' '.join(f"{k}) {transcribed[uid][k]};" for k in 'ABCDE')
        elif fig and fig.get('alternativas'):
            assert set(fig['alternativas'])==set('ABCDE'),uid
            out+=' As alternativas aparecem na imagem e são, em ordem: '+' '.join(f"{k}) {fig['alternativas'][k]}"+('' if fig['alternativas'][k].rstrip().endswith(('.',';')) else '.') for k in 'ABCDE')
        else: out+=' As alternativas A a E são figuras e só aparecem na imagem.'
    if shown: out+=' Texto-base: '+shown
    return out
def build():
    rows={q['id_unico_sistema']:q for q in map(json.loads,(ROOT/'data/blue-published/questions.jsonl').read_text().splitlines())}
    entries={}
    for batch in ('03','04','05'):
        report=json.loads((ROOT/f'data/audit/batch-{batch}-review.json').read_text())
        full=set(report.get('full_source_formula_panels',[]))
        for result in report['results']:
            uid=result['id']
            if result['status']!='APPROVED': continue
            q=rows[uid]
            assert q['conteudo']==result['after_content']
            if result.get('accessible_support') and uid not in full:
                assert q['conteudo']['texto_base']
                mode='text'
            elif uid in full: mode='composition'
            else: continue
            source=q['conteudo']['metadados_visual']['caminho_local_imagem']
            assert sha(ROOT/'data/extracted'/source.removeprefix('/images/'))==result['asset_sha256']
            entries[uid]=dict(mode=mode,record_sha256=record_digest(q),source=source,source_sha256=result['asset_sha256'],evidence=f'data/audit/batch-{batch}-review.json')
            if uid in full: entries[uid]['includes_command']=True
    for uid,mode in [('2024_AZUL_D2_Q155','figure'),('2018_AZUL_D1_Q74','composition')]:
        q=rows[uid];source=q['conteudo']['metadados_visual']['caminho_local_imagem'];asset=ROOT/'data/extracted'/source.removeprefix('/images/')
        e=dict(mode=mode,record_sha256=record_digest(q),source=source,source_sha256=sha(asset),evidence='docs/question-rendering.md')
        if mode=='figure':
            # Pixels reviewed against the complete published source panel. No rescaling.
            box=[40,235,620,585];target=ROOT/'data/extracted/verified/render-2024-d2-q155-figure.png'
            if '--check' not in sys.argv:
                from PIL import Image
                Image.open(asset).crop(box).save(target)
            e.update(figure='/images/verified/'+target.name,figure_sha256=sha(target),crop=box,
                before='Um proprietário pretende instalar um sensor de presença para a proteção de seu imóvel. O sensor deverá detectar movimentos de objetos e pessoas numa determinada região plana. A figura ilustra a vista superior da área de cobertura (setor circular em azul) de um sensor colocado no ponto S. Essa área depende da medida do ângulo α, em grau, e do raio R, em metro.',
                after='Ao aumentar o ângulo α ou o raio R aumenta-se a área de cobertura do sensor. Entretanto, quanto maior essa área, maior o preço do sensor.\n\nPara esse fim, há cinco tipos de sensores disponíveis no mercado, cada um com as seguintes características:\n• tipo I: α = 15° e R = 20 m;\n• tipo II: α = 30° e R = 22 m;\n• tipo III: α = 40° e R = 12 m;\n• tipo IV: α = 60° e R = 16 m;\n• tipo V: α = 90° e R = 10 m.\n\nEsse proprietário pretende adquirir um desses sensores que seja capaz de cobrir, no mínimo, uma área de medida 70 m², com o menor preço possível.\n\nUse 3 como valor aproximado para π.',
                alt='Vista superior: setor circular azul com centro no ponto S, ângulo α e raio R. Os valores de cada sensor estão transcritos abaixo.')
        else: e['alt']='Cartilha escolar do Estado Novo: Getúlio Vargas com crianças e mensagem impressa. A disposição entre retrato e mensagem integra o documento histórico.'
        entries[uid]=e
    # Fixed batch 07 display decisions; an empty after-caption is valid.
    report=json.loads((ROOT/'data/audit/batch-07-review.json').read_text())
    for result in report['results']:
        if result['status']!='APPROVED': continue
        uid=result['id']; q=rows[uid]; e=result['presentation_metadata']
        assert q['conteudo']==result['after_content']
        assert record_digest(q)==e['record_sha256']
        assert sha(ROOT/'data/extracted'/e['source'].removeprefix('/images/'))==e['source_sha256']
        entries[uid]=e
    report=json.loads((ROOT/'data/audit/batch-08-review.json').read_text())
    for result in report['results']:
        if result['status']!='APPROVED': continue
        uid=result['id']; q=rows[uid]; e=result['presentation_metadata']
        assert q['conteudo']==result['after_content']
        assert record_digest(q)==e['record_sha256']
        for asset in result['assets'].values():
            assert sha(ROOT/'data/extracted'/asset['image'].removeprefix('/images/'))==asset['sha256']
        entries[uid]=e
    fmt=json.loads(FORMAT.read_text());spec=fmt['questions'];transcribed=fmt['alternativas_transcritas'];figures=json.loads(FIGURES.read_text())
    for batch in ('09','10','11','12','13','14','15','16','17','18','19','20','21','22','23','24','25','26','27','28','29','30','31','32','33','34'):
        report=json.loads((ROOT/f'data/audit/batch-{batch}-review.json').read_text())
        for result in report['results']:
            if result['status']!='APPROVED': continue
            uid=result['id']; q=rows[uid]; e=result['presentation_metadata']
            assert q['conteudo']==result['after_content']
            assert record_digest(q)==e['record_sha256']
            for asset in result['assets'].values():
                assert sha(ROOT/'data/extracted'/asset['image'].removeprefix('/images/'))==asset['sha256']
            if e['mode']!='text' and 'alt' not in e and GENERIC.match(q['conteudo']['metadados_visual'].get('descricao_imagem') or ''):
                e=dict(e,alt=describe(q,result.get('parser_flags') or [],spec,transcribed,figures))
            entries[uid]=e
    return dict(schema_version=1,questions=entries)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');args=p.parse_args();data=build()
    if args.check:
        assert json.loads(DEST.read_text())==data, 'Presentation metadata is stale'
    else: DEST.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'reviewed':len(data['questions']),'modes':{m:sum(e['mode']==m for e in data['questions'].values()) for m in ['text','figure','composition']}}))
