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

## Confirmed CI integration evidence (2026-10-18)

The `arangodb-integration` GitHub Actions job uses ArangoDB 3.12,
`data/fused/questoes_enem_2025_AZUL_D1.jsonl` (89 records) and authenticated
credentials only within a disposable CI container.

Successful checks: default loader dry-run creates no database; first import and
second import leave all expected counts unchanged; each of the four question-edge
collections has 89 edges, and there are 89 TRI vertices; read-only checker
matches source JSONL metadata; injecting a valid-but-wrong item link or a wrong
TRI value is detected and reverted; a duplicate proof slot is rejected by the
unique composite index; `arangodump` and `arangorestore` recover 11 collections
in a second database, preserving counts and graph integrity.

These successes **do not certify the live local database**; it may have a legacy
unique `co_item` index, randomly generated edge keys or records not in GitHub.
Run the read-only steps in [db-local-checklist.md](db-local-checklist.md) first.
**No automatic migration or production merge is authorized.**
