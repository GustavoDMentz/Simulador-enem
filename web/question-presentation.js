'use strict';
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {recordDigest}=require('./audit-gate');
const root=path.resolve(__dirname,'..');
function readPresentation(){
 try{return JSON.parse(fs.readFileSync(path.join(root,'data/audit/question-presentation.json'),'utf8'))}catch{return null}
}
function presentation(q, data=readPresentation()){
 try{
  const e=data?.questions?.[q.id_unico_sistema];
  if(data?.schema_version!==1||!e||!['text','figure','composition'].includes(e.mode)||e.record_sha256!==recordDigest(q))return null;
  const digest=url=>{
   if(!/^\/images\/verified\/[\w-]+\.png$/.test(url||''))throw Error('Unsafe display asset');
   return crypto.createHash('sha256').update(fs.readFileSync(path.join(root,'data/extracted',url.slice('/images/'.length)))).digest('hex');
  };
  if(e.source!==q.conteudo?.metadados_visual?.caminho_local_imagem||digest(e.source)!==e.source_sha256)return null;
  if(e.mode==='text'&&!q.conteudo.texto_base?.trim())return null;
  if(e.mode==='figure'&&(typeof e.before!=='string'||typeof e.after!=='string'||digest(e.figure)!==e.figure_sha256))return null;
  return e;
 }catch{return null} // Display metadata can never remove a question or weaken the audit gate.
}
module.exports={presentation,readPresentation};
