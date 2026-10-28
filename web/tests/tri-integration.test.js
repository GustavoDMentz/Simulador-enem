'use strict';
const assert = require('node:assert/strict');
const test = require('node:test');
const {load,readExternalTri,withTri} = require('../published-questions');

test('all staged TRI rows are valid and unique', () => {
 const tri = readExternalTri();
 assert.equal(tri.size, 509);
});
test('published questions expose matched TRI parameters without changing answers', () => {
 const rows = load();
 assert.ok(rows && rows.length > 0);
 const tri = readExternalTri();
 for (const q of rows) {
  const p = tri.get(`${q.ano}/${q.co_item}`);
  if (!p) continue;
  assert.equal(q.parametros_tri.a, p.a);
  assert.equal(q.parametros_tri.b, p.b);
  assert.equal(q.parametros_tri.c, p.c);
  assert.equal(q.gabarito_oficial.length, 1);
 }
});
test('external answer disagreement does not block TRI join', () => {
 const q = {ano:2024,co_item:14475,area_conhecimento:'LC',gabarito_oficial:'C',id_unico_sistema:'sample',parametros_tri:null};
 const external = new Map([['2024/14475',{ano:2024,co_item:14475,area_conhecimento:'LC',a:2.3,b:-0.2,c:0.1,fonte:'test',status:'IDENTITY_MATCHED_EXTERNAL'}]]);
 const result = withTri(q,new Map(),external);
 assert.equal(result.gabarito_oficial,'C');
 assert.equal(result.parametros_tri.a,2.3);
});
test('area conflict still blocks join', () => {
 const q = {ano:2024,co_item:1,area_conhecimento:'MT',gabarito_oficial:'C',id_unico_sistema:'sample'};
 const external = new Map([['2024/1',{area_conhecimento:'LC',a:1,b:0,c:0.2,fonte:'test'}]]);
 assert.throws(()=>withTri(q,new Map(),external),/area mismatch/);
});
