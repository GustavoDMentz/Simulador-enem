'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('fs'),path=require('path');
const report=require('../../data/audit/batch-08-review.json');
const {scorable,readManifest}=require('../audit-gate');
const {presentation}=require('../question-presentation');
const rows=fs.readFileSync(path.resolve(__dirname,'../../data/blue-published/questions.jsonl'),'utf8').trim().split('\n').map(JSON.parse);
test('all recovered items are selectable and blocked decisions never enter scoring',()=>{
 const entries=readManifest().questions;assert.equal(rows.length,509);
 for(const r of report.results){const q=rows.find(q=>q.id_unico_sistema===r.id);
  if(r.status!=='APPROVED'){assert.equal(q,undefined);continue;}
  assert(scorable(q,entries));const p=presentation(q);assert(p);assert.equal(p.mode,r.presentation_metadata.mode);
  if(p.options)assert.deepEqual(Object.keys(p.options).sort(),[...'ABCDE']);
 }
});
test('damaged or absent option images invalidate presentation and scoring',()=>{
 const q=rows.find(q=>q.id_unico_sistema==='2021_AZUL_D2_Q126');
 const p=presentation(q),changed=structuredClone(p);changed.options.B.sha256='0'.repeat(64);
 assert.equal(presentation(q,{schema_version:1,questions:{[q.id_unico_sistema]:changed}}),null);
 const e=structuredClone(readManifest().questions.find(e=>e.id===q.id_unico_sistema));e.display_assets_sha256[p.options.B.image]='0'.repeat(64);
 assert.equal(scorable(q,[e]),false);
 e.display_assets_sha256['/images/verified/missing-batch08.png']='1'.repeat(64);assert.equal(scorable(q,[e]),false);
});
test('poetry retains line breaks while simple prose remains HTML',()=>{
 assert.equal(presentation(rows.find(q=>q.id_unico_sistema==='2021_AZUL_D1_Q02')).preserve_line_breaks,true);
 assert.equal(presentation(rows.find(q=>q.id_unico_sistema==='2020_AZUL_D2_Q123')).mode,'text');
});
