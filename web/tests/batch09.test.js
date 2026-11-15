'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('fs'),path=require('path');
const report=require('../../data/audit/batch-09-review.json');
const {scorable,readManifest}=require('../audit-gate');
const {presentation}=require('../question-presentation');
const rows=fs.readFileSync(path.resolve(__dirname,'../../data/blue-published/questions.jsonl'),'utf8').trim().split('\n').map(JSON.parse);
test('batch 09: all 64 new text-only items are scorable and presented as text',()=>{
 const entries=readManifest().questions;
 assert.equal(report.results.length,64);
 for(const r of report.results){
  const q=rows.find(q=>q.id_unico_sistema===r.id);assert(q,r.id);
  assert(scorable(q,entries),r.id);
  const p=presentation(q);assert(p,r.id);assert.equal(p.mode,'text');
  assert.equal(q.gabarito_oficial,r.official_answer);assert.equal(q.parametros_tri,null);
 }
});
test('batch 09: an edited answer or crop invalidates scoring',()=>{
 const r=report.results[0],q=structuredClone(rows.find(q=>q.id_unico_sistema===r.id));
 const entries=readManifest().questions;
 q.gabarito_oficial=q.gabarito_oficial==='A'?'B':'A';assert.equal(scorable(q,entries),false);
 const e=structuredClone(entries.find(e=>e.id===r.id));e.asset_sha256='0'.repeat(64);
 assert.equal(scorable(rows.find(x=>x.id_unico_sistema===r.id),[e]),false);
});
