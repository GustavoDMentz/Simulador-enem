'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

// Audited overlays never replace existing TRI or question data.
// Only an explicitly approved, source-matched record can be published.
const MANIFEST = path.resolve(__dirname, '../data/audit/manifest.json');
function readManifest(file = MANIFEST) {
  if (!fs.existsSync(file)) return { schema_version: 1, questions: [] };
  const data = JSON.parse(fs.readFileSync(file, 'utf8'));
  if (data.schema_version !== 1 || !Array.isArray(data.questions)) {
    throw new Error('Invalid audit manifest');
  }
  return data;
}
function approved(entry) {
  return Boolean(entry &&
    entry.publication_authorized === true &&
    entry.status === 'CONFORME' &&
    /^[a-f0-9]{64}$/i.test(entry.source_sha256 || '') &&
    entry.audit && entry.audit.text === true &&
    entry.audit.options === true &&
    entry.audit.graphics === true &&
    entry.audit.credits === true &&
    entry.audit.continuity === true);
}

function recordDigest(q) {
  function sorted(v) {
    if (Array.isArray(v)) return v.map(sorted);
    if (v && typeof v === 'object') return Object.fromEntries(Object.keys(v).sort().map(k => [k, sorted(v[k])]));
    return v;
  }
  return crypto.createHash('sha256').update(JSON.stringify(sorted({id:q.id_unico_sistema,
    year:q.ano,day:q.dia,position:q.posicao_prova,content:q.conteudo,answer:q.gabarito_oficial}))).digest('hex');
}
function scorable(q, entries = readManifest().questions) {
  const matches = entries.filter(e => e.id === q.id_unico_sistema);
  if (matches.length !== 1) return false;
  const e = matches[0], c = q.conteudo || {}, opts = c.alternativas || {};
  if (!approved(e) || e.audit.answer !== true || e.year !== q.ano || e.day !== q.dia || e.number !== q.posicao_prova ||
      !/^[a-f0-9]{64}$/i.test(e.answer_source_sha256 || '') ||
      !/^https:\/\/(download\.inep\.gov\.br|www\.gov\.br)\//.test(e.answer_source_url || '') ||
      !/^[ABCDE]$/.test(q.gabarito_oficial || '') || !String(c.enunciado || '').trim() ||
      Object.keys(opts).sort().join('') !== 'ABCDE' || ![...'ABCDE'].every(k => typeof opts[k] === 'string' && opts[k].trim()) ||
      e.record_sha256 !== recordDigest(q)) return false;
  const visual = c.metadados_visual || {};
  if (visual.contem_imagem || visual.caminho_local_imagem) {
    const name = visual.caminho_local_imagem;
    if (typeof name !== 'string' || !/^\/images\/verified\/[\w-]+\.png$/.test(name)) return false;
    const file = path.resolve(__dirname, '../data/extracted', name.slice('/images/'.length));
    if (!fs.existsSync(file) || crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex') !== e.asset_sha256) return false;
  }
  return true;
}
function forScoring(q, entries) {
  const enabled = scorable(q, entries);
  return {...q,scoring_enabled:enabled,gabarito_oficial:enabled?q.gabarito_oficial:null,parametros_tri:null};
}

function safeId(value) {
  return typeof value === 'string' && /^[a-zA-Z0-9_-]{1,100}$/.test(value);
}
function auditRouter(express) {
  const router = express.Router();
  router.get('/status', (_req, res) => {
    try {
      const all = readManifest().questions;
      res.json({ total: all.length, approved: all.filter(approved).length,
        quarantined: all.filter(x => !approved(x)).length,
        publication_default: false });
    } catch (e) { res.status(503).json({ error: 'Audit manifest unavailable' }); }
  });
  router.get('/questions', (req, res) => {
    try {
      const records = readManifest().questions.filter(approved);
      res.json({ total: records.length, results: records.map(x => ({
        id: x.id, year: x.year, number: x.number,
        source_sha256: x.source_sha256, status: x.status
      })) });
    } catch (e) { res.status(503).json({ error: 'Audit manifest unavailable' }); }
  });
  router.get('/questions/:id', (req, res) => {
    if (!safeId(req.params.id)) return res.status(400).json({ error: 'Invalid id' });
    try {
      const item = readManifest().questions.find(x => x.id === req.params.id);
      if (!approved(item)) return res.status(404).json({ error: 'Not approved' });
      res.json(item);
    } catch (e) { res.status(503).json({ error: 'Audit manifest unavailable' }); }
  });
  return router;
}
module.exports = { readManifest, approved, auditRouter, recordDigest, scorable, forScoring };
