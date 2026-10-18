# Database closure (before extractor merge)

Keep existing fused JSONL, ArangoDB graph and TRI parameters. No rebuild of the question bank.

Run read-only integrity audit:

```bash
python3 scripts/audit_fused_db.py --fused data/fused --output /tmp/enem-db-integrity.json
```

The audit checks unique IDs, unique proof slots, item metadata conflicts, missing/invalid gabaritos, TRI, and alternatives. It does **not** certify PDF visual fidelity, compare against the official INEP CSV, inspect the live ArangoDB instance, or provide a backup.

Before declaring the DB closed: verify counts against the actual `data/fused` files and live ArangoDB, run idempotent loads in a disposable DB, check dangling graph edges and indexes, verify TRI against official microdata, perform a restore test, and fix hard-coded paths/unauthenticated DB credentials. Do not merge the draft PR as a completed database closure until these checks pass.
