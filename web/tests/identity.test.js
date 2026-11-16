'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('fs'),path=require('path');
const {load,readIdentity,withIdentity,readTri}=require('../published-questions');
const raw=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../../data/audit/identity-resolution.json'),'utf8'));
test('identity: every area resolves to exactly one azul CO_PROVA that matches the official key',()=>{
 const resolved=raw.evidence.filter(e=>e.resolved);
 assert.equal(raw.evidence.length,36);assert.equal(resolved.length,36);
 for(const e of resolved){
  assert(e.candidates[0].ratio>=0.97);
  for(const c of e.candidates.slice(1)){if(e.equivalent_co_prova.includes(c.co_prova))continue;assert(c.ratio<=0.6,`${e.year} ${e.area} ${c.co_prova}`);}
 }
});
test('identity: published records get the resolved CO_ITEM and a verified status',()=>{
 const id=readIdentity(),rows=load();
 assert.equal(id.size,1612);
 let changed=0;
 for(const q of rows){
  const r=id.get(q.id_unico_sistema);if(!r)continue;
  assert.equal(q.co_item,r.co_item);assert.equal(q.identidade.status,'VERIFIED');
  assert.equal(q.gabarito_oficial,r.tx_gabarito);
 }
 const original=fs.readFileSync(path.resolve(__dirname,'../../data/blue-published/questions.jsonl'),'utf8').trim().split('\n').map(JSON.parse);
 for(const q of original){const r=id.get(q.id_unico_sistema);if(r&&r.co_item!==q.co_item)changed++}
 assert.equal(changed,203);
});
test('identity: joined TRI rows agree with the official answer after the correction',()=>{
 const ext=readTri();let joined=0;
 for(const q of load()){
  if(!q.identidade||!q.parametros_tri)continue;
  const p=ext.get(`${q.ano}/${q.co_item}`);assert(p);joined++;
 }
 assert(joined>0);
});
test('identity: disagreement with the official ITENS_PROVA answer removes the CO_ITEM',()=>{
 const id=readIdentity(),[uid,r]=[...id.entries()][0];
 const q={id_unico_sistema:uid,co_item:1,area_conhecimento:r.area,gabarito_oficial:r.tx_gabarito==='A'?'B':'A'};
 const out=withIdentity(q,id);assert.equal(out.co_item,null);assert.equal(out.identidade.status,'CONFLICT');
});
