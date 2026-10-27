'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {test}=require('node:test');
const {readTri,withTri}=require('../web/published-questions');
const FILE=path.resolve(__dirname,'../data/tri/parametros-oficiais.jsonl');
const original=fs.readFileSync(FILE,'utf8');
const item={ano:2023,co_item:123,area_conhecimento:'MT',gabarito_oficial:'C',parametros_tri:null};
const valid={ano:2023,co_item:123,area_conhecimento:'MT',gabarito_oficial:'C',a:1.25,b:-0.7,c:0.2,fonte:'INEP ITENS_PROVA',status:'VERIFIED'};
function withFile(rows,fn){try{fs.writeFileSync(FILE,rows.map(r=>JSON.stringify(r)).join('\n')+'\n');return fn();}finally{fs.writeFileSync(FILE,original);}}
test('empty TRI database leaves questions unchanged',()=>withFile([],()=>assert.equal(withTri(item,readTri()).parametros_tri,null)));
test('verified TRI joins exact identity',()=>withFile([valid],()=>assert.deepEqual(withTri(item,readTri()).parametros_tri,{a:1.25,b:-0.7,c:0.2})));
test('wrong area or answer blocks join',()=>withFile([valid],()=>{assert.throws(()=>withTri({...item,area_conhecimento:'LC'},readTri()),/identity mismatch/);assert.throws(()=>withTri({...item,gabarito_oficial:'B'},readTri()),/identity mismatch/);}));
test('duplicate CO_ITEM/year rejected',()=>withFile([valid,valid],()=>assert.throws(()=>readTri(),/Duplicate TRI/)));
test('unverified or invalid TRI rejected',()=>{for(const change of [{status:'PENDING'},{a:0},{c:1.1},{b:null},{fonte:''}])withFile([{...valid,...change}],()=>assert.throws(()=>readTri(),/Invalid TRI/));});
test('different year or item never joins',()=>withFile([valid],()=>assert.equal(withTri({...item,ano:2022},readTri()).parametros_tri,null)));
