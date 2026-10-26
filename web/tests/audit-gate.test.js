'use strict';
const assert = require('node:assert/strict');
const { test } = require('node:test');
const { approved, readManifest } = require('../audit-gate');
const base = { id: '2019-139', year: 2019, number: 139, status: 'CONFORME',
 source_sha256: 'a'.repeat(64), publication_authorized: true,
 audit: { text:true, options:true, graphics:true, credits:true, continuity:true } };
test('rejects unverified candidates by default', () => {
 assert.equal(approved({ ...base, publication_authorized: false }), false);
 assert.equal(approved({ ...base, status: 'INCONCLUSIVA' }), false);
 assert.equal(approved({ ...base, source_sha256: '' }), false);
});
test('requires all five audit dimensions', () => {
 for (const key of Object.keys(base.audit)) {
  assert.equal(approved({ ...base, audit: { ...base.audit, [key]: false } }), false);
 }
});
test('accepts only explicit fully audited record', () => {
 assert.equal(approved(base), true);
});
test('empty manifest when no audit data', () => {
 assert.deepEqual(readManifest('/path/that/does/not/exist'), { schema_version:1, questions:[] });
});
