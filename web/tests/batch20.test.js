'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('fs'),path=require('path');
const report=require('../../data/audit/batch-20-review.json');
const {scorable,readManifest}=require('../audit-gate');
const {presentation}=require('../question-presentation');
const {readIdentity}=require('../published-questions');
const identity=readIdentity();
const rows=fs.readFileSync(path.resolve(__dirname,'../../data/blue-published/questions.jsonl'),'utf8').trim().split('\n').map(JSON.parse);
test('batch 20: all 9 new figure items are scorable and presented as the original crop (composition)',()=>{
 const entries=readManifest().questions;
 assert.equal(report.results.length,9);
 for(const r of report.results){
  const q=rows.find(q=>q.id_unico_sistema===r.id);assert(q,r.id);
  assert(scorable(q,entries),r.id);
  const p=presentation(q);assert(p,r.id);assert.equal(p.mode,'composition');assert.equal(p.includes_command,true);
  assert.equal(q.gabarito_oficial,r.official_answer);assert.equal(q.parametros_tri,null);assert.equal(q.co_item,identity.get(r.id).co_item);assert.equal(identity.get(r.id).tx_gabarito,r.official_answer);
 }
});
test('batch 20: an edited answer or crop invalidates scoring',()=>{
 const r=report.results[0],q=structuredClone(rows.find(q=>q.id_unico_sistema===r.id));
 const entries=readManifest().questions;
 q.gabarito_oficial=q.gabarito_oficial==='A'?'B':'A';assert.equal(scorable(q,entries),false);
 const e=structuredClone(entries.find(e=>e.id===r.id));e.asset_sha256='0'.repeat(64);
 assert.equal(scorable(rows.find(x=>x.id_unico_sistema===r.id),[e]),false);
});
