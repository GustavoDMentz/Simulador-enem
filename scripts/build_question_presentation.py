#!/usr/bin/env python3
"""Rebuild reviewed display metadata without modifying audited records or answers."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from publish_blue_candidates import record_digest
ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT/'data/audit/question-presentation.json'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
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
    return dict(schema_version=1,questions=entries)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');args=p.parse_args();data=build()
    if args.check:
        assert json.loads(DEST.read_text())==data, 'Presentation metadata is stale'
    else: DEST.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'reviewed':len(data['questions']),'modes':{m:sum(e['mode']==m for e in data['questions'].values()) for m in ['text','figure','composition']}}))
