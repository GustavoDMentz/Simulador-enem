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

## Compatibility review (2026-10-18)

Retain existing `scripts/etl_tri.py`, `scripts/fuse.py`, `scripts/load_arangodb.py`, `web/server.js`, and `web/public`; do not duplicate their functionality. Existing `scripts/crop_and_link_images.py` can serve as a fallback for legacy images, but its PDF lookup, absolute paths, and geometric cropping are not a fidelity certification.

Use `scripts/link_audit_to_fused.py` for a **read-only**, source-hash-verified join of audit candidates with existing `data/fused/*.jsonl`. Matches remain `MATCHED_UNVERIFIED`; missing and ambiguous matches must be resolved before any promotion. Example:

```bash
python3 scripts/link_audit_to_fused.py \
  --report /path/to/enem_audit_v3/results/report.json \
  --fused data/fused \
  --pdf-2018 /path/to/2018_PV_impresso_D2_CD7.pdf \
  --pdf-2019 /path/to/2019_PV_impresso_D2_CD7.pdf \
  --pdf-2024 /path/to/2024_PV_impresso_D1_CD1.pdf \
  --output /tmp/enem-audit-link-report.json
python3 -m unittest discover -s scripts/tests -p 'test_link_audit_to_fused.py'
```

**Merge blocker:** the new `segmenter_v2.py`, `audit_independent.py`, `verify_source.py` and their native regression suite are currently in the standalone v3 package, not yet committed in this branch. The API also has not been tested end-to-end against a real ArangoDB dataset. The legacy `/api/questions` route still returns development records without audit filtering. Do not merge as a completed production integration until these gaps are resolved.
