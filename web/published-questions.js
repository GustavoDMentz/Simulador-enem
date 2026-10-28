'use strict';
const fs=require('fs');
const path=require('path');
const {scorable,forScoring,readManifest}=require('./audit-gate');
const SOURCE=path.resolve(__dirname,'../data/blue-published/questions.jsonl');
const PREVIEW=path.resolve(__dirname,'../data/blue-published/preview-questions.jsonl');
const RECOVERY=path.resolve(__dirname,'../data/audit/session-recovery/preview-questions.jsonl');
const TRI=path.resolve(__dirname,'../data/tri/parametros-oficiais.jsonl');
const TRI_EXTERNAL=path.resolve(__dirname,'../data/tri/external-staging/tri-joined-2018-2025.jsonl');
function readTri(){
 const result=new Map();
 if(!fs.existsSync(TRI))return result;
 for(const line of fs.readFileSync(TRI,'utf8').split(/\r?\n/).filter(Boolean)){
  const p=JSON.parse(line),key=`${p.ano}/${p.co_item}`;
  if(p.status!=='VERIFIED'||!Number.isInteger(p.ano)||!Number.isInteger(Number(p.co_item))||!['LC','CH','CN','MT'].includes(p.area_conhecimento)||!['A','B','C','D','E'].includes(p.gabarito_oficial)||!['a','b','c'].every(k=>typeof p[k]==='number'&&Number.isFinite(p[k]))||p.a<=0||p.c<0||p.c>1||!p.fonte)throw Error('Invalid TRI record: '+key);
  if(result.has(key))throw Error('Duplicate TRI record: '+key);
  result.set(key,p);
 }
 return result;
}
function readExternalTri(){
 const result=new Map();
 if(!fs.existsSync(TRI_EXTERNAL))return result;
 for(const line of fs.readFileSync(TRI_EXTERNAL,'utf8').split(/\r?\n/).filter(Boolean)){
  const p=JSON.parse(line),key=`${p.ano}/${p.co_item}`;
  if(p.status!=='IDENTITY_MATCHED_EXTERNAL'||!Number.isInteger(p.ano)||!Number.isInteger(p.co_item)||!['LC','CH','CN','MT'].includes(p.area_conhecimento)||!['a','b','c'].every(k=>typeof p[k]==='number'&&Number.isFinite(p[k]))||p.a<=0||p.c<0||p.c>1||!p.fonte)throw Error('Invalid external TRI: '+key);
  if(result.has(key))throw Error('Duplicate external TRI: '+key);
  result.set(key,p);
 }
 return result;
}
function withTri(q,tri,external=new Map()){
 const ext=external.get(`${q.ano}/${q.co_item}`);
 const verified=tri.get(`${q.ano}/${q.co_item}`);
 const p=verified||ext;
 if(!p)return q;
 if(p.area_conhecimento!==q.area_conhecimento)throw Error('TRI item area mismatch: '+q.id_unico_sistema);
 if(verified&&p.gabarito_oficial!==q.gabarito_oficial)throw Error('Verified TRI answer mismatch: '+q.id_unico_sistema);
 return {...q,parametros_tri:{a:p.a,b:p.b,c:p.c,fonte:p.fonte,status:verified?'VERIFIED':'IDENTITY_MATCHED_EXTERNAL'}};
}
function load(file=SOURCE){
 if(!fs.existsSync(file))return null;
 let rows=fs.readFileSync(file,'utf8').split(/\r?\n/).filter(Boolean).map(JSON.parse);
 if(file===RECOVERY){const release=new Map((load(SOURCE)||[]).map(q=>[q.id_unico_sistema,q]));rows=rows.map(q=>release.get(q.id_unico_sistema)||q)}
 const ids=rows.map(q=>q.id_unico_sistema);
 const keys=rows.map(q=>`${q.ano}/${q.dia}/${q.posicao_prova}`);
 if(new Set(ids).size!==ids.length||new Set(keys).size!==keys.length)throw Error('Duplicate question identity');
 const entries=readManifest().questions;
 const tri=readTri(),external=readExternalTri();
 const display=require('./question-presentation'), displayData=display.readPresentation();
 return (file===SOURCE?rows.filter(q=>scorable(q,entries)):rows).map(q=>{const scored=forScoring(q,entries);const joined=withTri(scored,tri,external);return {...joined,_key:q._key||q.id_unico_sistema,presentation:display.presentation(q,displayData)};});
}
function filter(rows,query){
 for(const name of ['year','day','position'])if(query[name]!==undefined&&(!Number.isInteger(Number(query[name]))||Number(query[name])<1))throw Error('Invalid filter');
 return rows.filter(q=>(!query.year||q.ano===Number(query.year))&&(!query.day||q.dia===Number(query.day))&&
  (!query.position||q.posicao_prova===Number(query.position))&&(!query.area||q.area_conhecimento===query.area)&&
  (query.has_image!=='true'||q.conteudo?.metadados_visual?.contem_imagem===true));
}
function publishedRouter(express){
 const router=express.Router();
 router.get('/preview/questions',(req,res)=>{
  try{
   const rows=load(fs.existsSync(PREVIEW)?PREVIEW:RECOVERY);
   if(!rows)return res.status(503).json({error:'Preview unavailable'});
   const all=filter(rows,req.query),page=Math.max(1,parseInt(req.query.page,10)||1),limit=Math.max(1,Math.min(100,parseInt(req.query.limit,10)||10));
   res.json({total:all.length,page,limit,preview:true,certified:false,results:all.slice((page-1)*limit,page*limit)});
  }catch(e){res.status(e.message==='Invalid filter'?400:503).json({error:e.message})}
 });
 router.get('/metadata',(_req,res)=>{
  try{
   const all=load();if(!all)return res.status(503).json({error:'Approved release unavailable'});
   res.json({anos:[...new Set(all.map(q=>q.ano))],dias:[...new Set(all.map(q=>q.dia))],areas:[...new Set(all.map(q=>q.area_conhecimento))],total:all.length,images:all.filter(q=>q.conteudo?.metadados_visual?.contem_imagem).length});
  }catch(e){res.status(503).json({error:e.message})}
 });
 router.get('/questions',(req,res)=>{
  try{
   const rows=load();if(!rows)return res.status(503).json({error:'Approved release unavailable'});
   const all=filter(rows,req.query),page=Math.max(1,Math.min(100000,parseInt(req.query.page,10)||1)),limit=Math.max(1,Math.min(100,parseInt(req.query.limit,10)||10));
   res.json({total:all.length,page,limit,totalPages:Math.ceil(all.length/limit),results:all.slice((page-1)*limit,page*limit)});
  }catch(e){res.status(e.message==='Invalid filter'?400:503).json({error:e.message})}
 });
 router.get('/questions/random',(req,res)=>{
  try{
   const rows=load();if(!rows)return res.status(503).json({error:'Approved release unavailable'});
   const all=filter(rows,req.query);if(!all.length)return res.status(404).json({error:'No approved questions'});
   res.json(all[Math.floor(Math.random()*all.length)]);
  }catch(e){res.status(e.message==='Invalid filter'?400:503).json({error:e.message})}
 });
 router.get('/questions/:id',(req,res)=>{
  try{
   const rows=load();if(!rows)return res.status(503).json({error:'Approved release unavailable'});
   const q=rows.find(q=>q.id_unico_sistema===req.params.id||q._key===req.params.id);
   if(!q)return res.status(404).json({error:'No approved question'});res.json(q);
  }catch(e){res.status(503).json({error:e.message})}
 });
 return router;
}
module.exports={publishedRouter,load,filter,readTri,readExternalTri,withTri};
