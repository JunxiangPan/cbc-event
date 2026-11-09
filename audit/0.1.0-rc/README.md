# CBC 0.1.0 RC audit — 2026-11-09

## Verdict

**BLOCKED at step 1 — no real R01–R19 run, no PASS claim.**

CBC can consume a v1.7 `quality-manifest` with `body_hash_scope: "base"`, but
CBP 1.2.0 RC does **not** expose a generic quality-manifest generator for an
external package. Its RC CLI emits gate reports / v12 rule reports; its
`dogfood_manifest.py` is CBP-self only (`package_id: "cbp"`, CBP's own nine
gates and release layout). There is no CBP-generated CBC manifest in the RC
artifact, so running R01–R19 now would require CBC to fabricate or hand-assemble
the CBP input. That is not accepted here.

## Baseline

- CBC repo: `D:\qq苏瑾言大肥鱼\cbc-event`
- HEAD at audit start: `ae18d0c`
- CI: run 42484903879, ubuntu + windows success
- local: 137 tests OK (1 skip: standalone F05)
- protocol coverage 98% / viewer 90%
- no tag, no GitHub Release, no PyPI upload

## Inputs inspected

- CBP 1.2.0 RC code: `5da8b87` (PR #1), RC build run `42539271566`, artifact
  `cbp-rc`
- CBP RC wheel: `40b0f5f827acefe4f5f9a5891a5d70be9d53557435acd721706c6a9f01fff320`
- CBP RC sdist: `e30fa8319103e31ec85e9c1f514c9a14de267c35067c263ae245d7eec5c32604`
- CBP RC `RC_ASSETS.sha256`: `4d18155845301544b90e87d671b759630dedd924b5db60266276b1845117802c`
- CBS v1.7.1 RC body-generator source: commits `04c9f8b` / `1ee6476` (current
  CBS HEAD does not contain that source file; see `F05.md`)

## What was actually executed

1. **CBP 1.2.0 RC v12 on CBC** — real run, 12/12 PASS; rerun after adding
   the audit package also 12/12 PASS (audit docs do not alter the gate).
   - raw: `raw/cbp-v12.stdout`, `raw/cbc-v12-report.json`,
     `raw/cbp-v12-after-audit.stdout`, `raw/cbc-v12-report-after-audit.json`
2. **CBP 1.2.0 RC normal gate on CBC** — real run, PASS with 1 applicable gate
   and 8 non-applicable skips; this is a gate report, not a v1.7 manifest.
   CBC correctly rejects it as an input: `input_error: CBP manifest missing field: artifact_hashes`.
   - raw: `raw/cbp-gates.stdout`, `raw/cbc-gate-report.json`,
     `raw/real-cbp-report-validation.stdout`
3. **Viewer scope/precondition paths** — S17/S18/F03 unit evidence.
   - raw: `raw/viewer-paths.stdout`
4. **F05 auxiliary check** — real CBS body-generator source from `1ee6476` and
   `04c9f8b` imported; exact CBC line accepted. This is not a full release-train
   execution.
   - raw: `raw/f05-cbs-source.stdout`

## Not executed

- R01–R19: **NOT RUN**; see `R01_R19.md`.
- Full CBS v1.7 release-train job: **NOT RUN**; see `F05.md`.
- No tag, release, upload, or PyPI action was taken.

## Files

- `CBP_RC_INPUTS.md` — provenance and hashes
- `CBP_MANIFEST_GAP.md` — why the real manifest is unavailable
- `R01_R19.md` — intended commands and blocked status
- `F05.md` — standalone skip vs train requirement and auxiliary evidence
- `VIEWER_PATHS.md` — three viewer error paths
- `raw/` — unedited command outputs
- `SHA256SUMS` — audit file hashes (this file excluded)
