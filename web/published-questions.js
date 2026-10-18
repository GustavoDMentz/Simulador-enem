'use strict';
const fs=require('fs');
const path=require('path');
const SOURCE=path.resolve(__dirname,'../data/blue-published/questions.jsonl');
function publishedRouter(express){
 const router=express.Router();
 function load(){
  if(!fs.existsSync(SOURCE))return null;
  const rows=fs.readFileSync(SOURCE,'utf8').split(/\r?\n/).filter(Boolean).map((line,i)=>{
   try{return JSON.parse(line)}catch(e){throw Error('Invalid published JSONL at line '+(i+1))}
  });
  return rows;
 }
 router.get('/questions',(req,res)=>{
  try{
   const all=load();
   if(!all)return res.status(503).json({error:'Published file not generated',source:'data/blue-published/questions.jsonl'});
   const year=req.query.year===undefined?null:Number(req.query.year);
   const day=req.query.day===undefined?null:Number(req.query.day);
   const position=req.query.position===undefined?null:Number(req.query.position);
   if([year,day,position].some(v=>v!==null&&(!Number.isInteger(v)||v<1)))return res.status(400).json({error:'Invalid filter'});
   const matches=all.filter(q=>(year===null||q.ano===year)&&(day===null||q.dia===day)&&(position===null||q.posicao_prova===position));
   const page=Math.max(1,Math.min(100000,Number.parseInt(req.query.page,10)||1));
   const limit=Math.max(1,Math.min(100,Number.parseInt(req.query.limit,10)||10));
   res.json({total:matches.length,page,limit,totalPages:Math.ceil(matches.length/limit),results:matches.slice((page-1)*limit,page*limit)});
  }catch(err){res.status(500).json({error:err.message})}
 });
 router.get('/questions/random',(req,res)=>{
  try{
   const all=load();
   if(!all)return res.status(503).json({error:'Published file not generated'});
   if(!all.length)return res.status(404).json({error:'No published questions'});
   res.json(all[Math.floor(Math.random()*all.length)]);
  }catch(err){res.status(500).json({error:err.message})}
 });
 return router;
}
module.exports={publishedRouter};
