# Audit gate — integration with existing ENEM simulator

The existing `data/fused/*.jsonl`, TRI ETL, ArangoDB and `web/public` remain authoritative and untouched.
This feature introduces a **separate, fail-closed audit registry**, not a second question bank.

## Routes

- `GET /api/audit/status`: number of candidates, approved and quarantined.
- `GET /api/audit/questions`: only explicitly approved entries.
- `GET /api/audit/questions/:id`: returns 404 for any unapproved item.

A record is eligible only when `publication_authorized: true`, `status: CONFORME`, the source SHA256 is present, and all five audit dimensions are true. Empty or missing manifests approve **zero** questions.

## Import the experimental 2018/2019/2024 audit

```bash
python3 scripts/import_audit_candidates.py --report /path/to/enem_audit_v3/results/report.json
cd web && node --test tests/audit-gate.test.js
```

Import deliberately sets **every candidate to INCONCLUSIVA and not authorized**. Pixel equality and label detection do not prove semantic correctness. The importer never modifies fused JSONL or TRI parameters and refuses to overwrite a manifest containing approvals.

## Not yet integrated

Question-level joining to existing ArangoDB `_key` / `CO_ITEM`, audited image assets, browser-side UI, and publication approval workflow require validated mapping. The original `/api/questions` remains a legacy development endpoint, not a public audited feed. Do not expose it publicly as a publication-approved catalog.
