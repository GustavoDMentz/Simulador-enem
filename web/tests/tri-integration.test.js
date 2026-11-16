'use strict';
const assert = require('node:assert/strict');
const test = require('node:test');
const {load,readTri,withTri} = require('../published-questions');

test('official TRI rows are valid, unique and VERIFIED', () => {
 const tri = readTri();
 assert.equal(tri.size, 1586);
 for (const p of tri.values()) assert.equal(p.status, 'VERIFIED');
});
test('published questions expose the official TRI parameters without changing answers', () => {
 const rows = load();
 assert.ok(rows && rows.length > 0);
 const tri = readTri();
 let joined = 0;
 for (const q of rows) {
  const p = tri.get(`${q.ano}/${q.co_item}`);
  if (!p) { assert.ok(!q.parametros_tri); continue; }
  joined++;
  assert.equal(q.parametros_tri.a, p.a);
  assert.equal(q.parametros_tri.b, p.b);
  assert.equal(q.parametros_tri.c, p.c);
  assert.equal(q.parametros_tri.status, 'VERIFIED');
  assert.equal(p.gabarito_oficial, q.gabarito_oficial);
 }
 assert.equal(joined, 1209);
});
test('an answer that disagrees with the official row blocks the join', () => {
 const q = {ano:2024,co_item:14475,area_conhecimento:'LC',gabarito_oficial:'C',id_unico_sistema:'sample'};
 const tri = new Map([['2024/14475',{area_conhecimento:'LC',gabarito_oficial:'D',a:2.3,b:-0.2,c:0.1,fonte:'test'}]]);
 assert.throws(()=>withTri(q,tri),/answer mismatch/);
});
test('area conflict still blocks join', () => {
 const q = {ano:2024,co_item:1,area_conhecimento:'MT',gabarito_oficial:'C',id_unico_sistema:'sample'};
 const tri = new Map([['2024/1',{area_conhecimento:'LC',gabarito_oficial:'C',a:1,b:0,c:0.2,fonte:'test'}]]);
 assert.throws(()=>withTri(q,tri),/area mismatch/);
});
