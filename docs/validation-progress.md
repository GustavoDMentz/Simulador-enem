# ENEM audit checkpoint — 2026-10-25

## Verified work before runtime loss

- Original split ZIP reconstructed: 579094830 bytes.
- SHA-256: a2efb083c95057b71f698e25cd11da031703b2f7da4bd50d3d7e8dbe82371a97.
- unzip -t passed; 8908 entries inspected; 3253 regular files extracted. Dependency environments, symlinks, credentials and hooks excluded.
- Archive HEAD c268020; remote starting HEAD f35d51d3eeb00f9644e92fdfb0b73ea665860a47.
- All 123 REVIEW_ANSWER examined: 98 matching, 25 wrong answers.
- Expanded review: 309 answer keys compared; 41 answer corrections including two annulled questions, excluding six preexisting 2018 corrections.
- 59 questions fully compared with source PDFs and tested locally, including the initial 20, eight REVIEW_IMAGE cases, 13 short questions and 18 additional science questions.
- 454 questions remain unvalidated. The full preview contains 513.
- Essential graphics restored directly from PDF renderings, without redrawing. Rasterized supporting text is not selectable.
- Validation performed: Python compilation, 65 Python tests, six Node tests, HTTP API checks and actual Chromium selection/correct-answer checks for all 59 questions. Desktop/mobile preview loaded all 513; graphic requests returned HTTP 200.
- No database, production, main merge, paid service or credentials changed.

## Publication interruption

The Work execution environment changed during transfer. The checkout, generated images, ZIP and local commits were no longer available in the replacement runtime. Direct Git push had failed for lack of terminal credentials. Only the blobs now saved by this checkpoint reached GitHub.

Local commits made and tested, but NOT pushed:
- 21dbcd7: scoring approval and annulled-key parser.
- 935291f: 41 reviewed questions and recovered assets.
- 636a80e: 18 additional science questions and three source tables.

These local commit IDs are historical evidence, not usable GitHub commit links.

## What this checkpoint deliberately does

- Preserves answer/content correction evidence and ZIP integrity record.
- Saves the reviewed manifest and 513-record preview under data/audit/session-recovery, outside the live publisher/API.
- Does NOT activate the 59 scoring flags remotely: their associated code and image assets did not finish transferring.
- Leaves the live data/audit/manifest.json unchanged.

## Resume

Use the original uploaded ZIP parts and the saved evidence. Recreate the reviewed image assets from the original PDFs, restore the content-bound scoring guard, rebuild release rows from preview plus correction evidence, and rerun tests before making a live release. Do not copy the recovery manifest into the live manifest without restoring/verifying all referenced assets.
Remaining documentary gaps include the local 2024 day-1 answer PDF and multiline 2020 day-2 answer-key parsing.
