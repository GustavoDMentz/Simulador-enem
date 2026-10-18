'use strict';
const fs = require('fs');
const path = require('path');

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
module.exports = { readManifest, approved, auditRouter };
