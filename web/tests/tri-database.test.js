'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const {test}=require('node:test');
const {readTri,withTri}=require('../published-questions');
const item={ano:2023,co_item:123,area_conhecimento:'MT',gabarito_oficial:'C',parametros_tri:null};
const valid={ano:2023,co_item:123,area_conhecimento:'MT',gabarito_oficial:'C',a:1.25,b:-0.7,c:0.2,fonte:'INEP ITENS_PROVA',status:'VERIFIED'};
let FILE;
function withFile(rows,fn){const dir=fs.mkdtempSync(path.join(os.tmpdir(),'tri-'));FILE=path.join(dir,'p.jsonl');try{fs.writeFileSync(FILE,rows.map(r=>JSON.stringify(r)).join('\n')+'\n');return fn();}finally{fs.rmSync(dir,{recursive:true,force:true});}}
test('empty TRI database leaves questions unchanged',()=>withFile([],()=>assert.equal(withTri(item,readTri(FILE)).parametros_tri,null)));
test('verified TRI joins exact identity',()=>withFile([valid],()=>assert.deepEqual(withTri(item,readTri(FILE)).parametros_tri,{a:1.25,b:-0.7,c:0.2,fonte:'INEP ITENS_PROVA',status:'VERIFIED'})));
test('wrong area or answer blocks join',()=>withFile([valid],()=>{assert.throws(()=>withTri({...item,area_conhecimento:'LC'},readTri(FILE)),/area mismatch/);assert.throws(()=>withTri({...item,gabarito_oficial:'B'},readTri(FILE)),/Verified TRI answer mismatch/);}));
test('duplicate CO_ITEM/year rejected',()=>withFile([valid,valid],()=>assert.throws(()=>readTri(FILE),/Duplicate TRI/)));
test('unverified or invalid TRI rejected',()=>{for(const change of [{status:'PENDING'},{a:0},{c:1.1},{b:null},{fonte:''}])withFile([{...valid,...change}],()=>assert.throws(()=>readTri(FILE),/Invalid TRI/));});
test('different year or item never joins',()=>withFile([valid],()=>assert.equal(withTri({...item,ano:2022},readTri(FILE)).parametros_tri,null)));
