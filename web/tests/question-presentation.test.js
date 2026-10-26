'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict');
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {presentation}=require('../question-presentation');
const rows=fs.readFileSync(path.resolve(__dirname,'../../data/blue-published/questions.jsonl'),'utf8').trim().split('\n').map(JSON.parse);
const get=id=>rows.find(q=>q.id_unico_sistema===id);
test('reviewed text cases use HTML; historical composition and geometry retain their visual meaning',()=>{
 for(const id of ['2024_AZUL_D2_Q137','2018_AZUL_D2_Q110','2024_AZUL_D2_Q111'])assert.equal(presentation(get(id)).mode,'text');
 assert.equal(presentation(get('2018_AZUL_D1_Q74')).mode,'composition');
 const p=presentation(get('2024_AZUL_D2_Q155'));
 assert.equal(p.mode,'figure');assert.match(p.after,/tipo IV: α = 60° e R = 16 m/);assert.match(p.after,/70 m²/);assert.match(p.after,/tipo V: α = 90° e R = 10 m/);
 assert.notEqual(p.figure,p.source);
});
test('unknown or edited evidence preserves the original presentation fallback',()=>{
 const q=get('2024_AZUL_D2_Q137');
 assert.equal(presentation({...q,conteudo:{...q.conteudo,texto_base:'Altered'}}),null);
 assert.equal(presentation({...q,id_unico_sistema:'unknown'}),null);
});
test('all 238 previous records and answers are byte-for-byte unchanged',()=>{
 const prior=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../../data/audit/batch-06-review.json'),'utf8')).previous_records_sha256;
 const lines=fs.readFileSync(path.resolve(__dirname,'../../data/blue-published/questions.jsonl'),'utf8').trimEnd().split('\n');
 const bytes=Buffer.from(lines.filter(line=>prior[JSON.parse(line).id_unico_sistema]).join('\n')+'\n');
 assert.equal(rows.length,328);
 assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'),'8351f7ef5c3508e9bc1277d7ad8fb6bd6d82113b897fd31db1c621dfdcc906d3');
});

test('source-checked figure without following prose remains visible and missing caption fails conservatively',()=>{
 const q=get('2021_AZUL_D2_Q91');
 assert.equal(presentation(q).mode,'figure');assert.equal(presentation(q).after,'');
 const entry=presentation(q);assert.equal(presentation(q,{schema_version:1,questions:{[q.id_unico_sistema]:{...entry,after:undefined}}}),null);
});
