'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),crypto=require('node:crypto');
const {recordDigest,scorable}=require('../audit-gate');
const q={id_unico_sistema:'2022_AZUL_D2_Q91',ano:2022,dia:2,posicao_prova:91,
 conteudo:{enunciado:'Verified stem.',alternativas:Object.fromEntries([...'ABCDE'].map(k=>[k,'Option '+k]))},gabarito_oficial:'A'};
const e={id:q.id_unico_sistema,year:2022,day:2,number:91,status:'CONFORME',publication_authorized:true,
 source_sha256:'a'.repeat(64),answer_source_sha256:'b'.repeat(64),answer_source_url:'https://download.inep.gov.br/key.pdf',
 record_sha256:recordDigest(q),audit:{text:true,options:true,graphics:true,credits:true,continuity:true,answer:true}};
test('rejects edited content, answers, identity, duplicate approval and absent answer evidence',()=>{
 assert.equal(scorable(q,[e]),true);
 for(const entry of [{...e,number:92},{...e,audit:{...e.audit,answer:false}},{...e,publication_authorized:false},{...e,answer_source_url:'https://example.org/key.pdf'}])assert.equal(scorable(q,[entry]),false);
 assert.equal(scorable({...q,gabarito_oficial:'B'},[e]),false);
 assert.equal(scorable({...q,conteudo:{...q.conteudo,enunciado:'Truncated'}},[e]),false);
 assert.equal(scorable(q,[e,e]),false);
});
test('HTTP fails closed for corrupt manifests, absent/edited graphics and unapproved file flags',async()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'enem-api-'));let server;
 try{
  for(const d of ['web','data/audit','data/blue-published','data/extracted/verified'])fs.mkdirSync(path.join(root,d),{recursive:true});
  for(const file of ['audit-gate.js','published-questions.js','question-presentation.js'])fs.copyFileSync(path.resolve(__dirname,'..',file),path.join(root,'web',file));
  const visual={...q,id_unico_sistema:'graphic',posicao_prova:92,conteudo:{...q.conteudo,metadados_visual:{contem_imagem:true,caminho_local_imagem:'/images/verified/test.png'}}};
  const asset=path.join(root,'data/extracted/verified/test.png');fs.writeFileSync(asset,'fixture');
  const ve={...e,id:'graphic',number:92,record_sha256:recordDigest(visual),asset_sha256:crypto.createHash('sha256').update('fixture').digest('hex')};
  const candidate={...q,id_unico_sistema:'candidate',posicao_prova:93,scoring_enabled:true};
  const mf=path.join(root,'data/audit/manifest.json');fs.writeFileSync(mf,JSON.stringify({schema_version:1,questions:[e,ve]}));
  for(const file of ['questions.jsonl','preview-questions.jsonl'])fs.writeFileSync(path.join(root,'data/blue-published',file),[q,candidate,visual].map(JSON.stringify).join('\n'));
  const express=require('express'),app=express();app.use('/api',require(path.join(root,'web/published-questions')).publishedRouter(express));
  server=app.listen(0,'127.0.0.1');await new Promise(r=>server.on('listening',r));const base='http://127.0.0.1:'+server.address().port+'/api';
  const get=async p=>await (await fetch(base+p)).json();
  assert.equal((await get('/questions')).total,2);
  const preview=await get('/preview/questions');assert.equal(preview.results[1].scoring_enabled,false);assert.equal(preview.results[1].gabarito_oficial,null);
  assert.equal((await fetch(base+'/questions/candidate')).status,404);
  assert.equal((await fetch(base+'/questions?year=bad')).status,400);
  assert.equal((await fetch(base+'/questions/random?year=2000')).status,404);
  assert.equal((await get('/questions/random?year=2022')).ano,2022);
  // A fresh checkout has no generated preview: merge only approved release content.
  const recovery=path.join(root,'data/audit/session-recovery');fs.mkdirSync(recovery,{recursive:true});
  fs.writeFileSync(path.join(recovery,'preview-questions.jsonl'),[q,candidate,{...visual,conteudo:{...visual.conteudo,enunciado:'Old pending stem'}}].map(JSON.stringify).join('\n'));
  fs.unlinkSync(path.join(root,'data/blue-published/preview-questions.jsonl'));
  const fresh=await get('/preview/questions');assert.equal(fresh.results.find(r=>r.id_unico_sistema==='graphic').conteudo.enunciado,visual.conteudo.enunciado);
  assert.equal(fresh.results.find(r=>r.id_unico_sistema==='candidate').scoring_enabled,false);
  fs.writeFileSync(asset,'changed');assert.equal((await get('/questions')).total,1);
  fs.unlinkSync(asset);assert.equal((await get('/questions')).total,1);
  fs.writeFileSync(mf,'{');assert.equal((await fetch(base+'/questions')).status,503);
 }finally{if(server)await new Promise(r=>server.close(r));fs.rmSync(root,{recursive:true,force:true})}
});
