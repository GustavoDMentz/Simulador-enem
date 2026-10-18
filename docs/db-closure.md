# Database closure (before extractor merge)

Keep existing fused JSONL, ArangoDB graph and TRI parameters. No rebuild of the question bank.

Run read-only integrity audit:

```bash
python3 scripts/audit_fused_db.py --fused data/fused --output /tmp/enem-db-integrity.json
```

The audit checks unique IDs, unique proof slots, item metadata conflicts, missing/invalid gabaritos, TRI, and alternatives. It does **not** certify PDF visual fidelity, compare against the official INEP CSV, inspect the live ArangoDB instance, or provide a backup.

Before declaring the DB closed: verify counts against the actual `data/fused` files and live ArangoDB, run idempotent loads in a disposable DB, check dangling graph edges and indexes, verify TRI against official microdata, perform a restore test, and fix hard-coded paths/unauthenticated DB credentials. Do not merge the draft PR as a completed database closure until these checks pass.

## Loader defects found and addressed in draft branch

- Fixed `QuestaoParamTRI` edge collection being confused with `ParametrosTRI` vertex collection.
- Changed `co_item` index definition to nonunique, since an INEP item may appear in multiple booklets. **Existing unique indexes are not migrated by this change**; inspect/drop/recreate only after a backup and review.
- Assigned deterministic edge keys for repeated loads. Validate the driver API and rerun on a disposable database before production.
- Added `scripts/check_arangodb_integrity.py`, an authenticated, read-only check of vertex/edge collections, dangling graph endpoints, missing TRI/CO_ITEM/positions and duplicate proof slots.

Run only against an authorized database:

```bash
export ARANGO_HOST=http://127.0.0.1:8529 ARANGO_DB=enem
export ARANGO_USER=... ARANGO_PASSWORD=...
python3 scripts/check_arangodb_integrity.py --output /tmp/enem-live-db-integrity.json
```

The live database is **not accessible from this workspace**. The checker has not been run against it; therefore the database is **not yet closed**. Existing loader and server still contain legacy unauthenticated/hardcoded defaults and require hardening.
