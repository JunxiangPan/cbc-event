# CBC 0.1.0 — release notes (candidate)

**Status: NOT TAGGED, NOT PUBLISHED.** This file is the prepared release note;
the tag/release is created only after explicit human approval.

## What this release is

`cbc-event` / `cbc_viewer` 0.1.0 is the read-only CBC release-evidence viewer.
It verifies the `cbc-chain/v1` hash chain, renders the sealed-v1 body, and
exposes three viewer error paths. It does not upload, publish, or modify a
release.

## Changes in this candidate

- Accepts the contract v1.7.1 RC2 CBP quality-manifest shape:
  - `schema_version` is the string `"1"`;
  - `artifact_repository` is an object with exactly `repository`, `run_id`, and
    `artifact_name`; a bare string is rejected as legacy/noncanonical;
  - `body_hash_scope` is `base`;
  - `release_body_hash` is checked against the §5.3 canonical body.
- Retains the `link_count` / `asset_link_count` split: header, reports,
  controls, and assets are counted in `link_count`; only asset leaves in
  `asset_link_count`.
- Retains the `sealed-v1` base/appendix rule, `NOT_UPLOADED` rendering, and the
  three viewer error paths (`verify`, `show`, `render-body`).
- `cbc_event` protocol semantics are unchanged from 0.1.0.

## Test evidence for this candidate

- CBP 1.2.2 official manifest: `a64555beb323099ff3810f23f5f45f09276233aa72c83866c806ae0513491b4c`
- R02–R19: **18/18 assertions passed** (R16 Windows SKIP, Linux CI covers)
- R01: local test index **PASS**; real GitHub R01 **NOT RUN** (pending a real
  uploaded release)
- F05: train-like with real CBS source **OK**; full CBS v1.7 train **NOT RUN**
- CI: Ubuntu + Windows green on the candidate commit.

## Artifacts

- wheel: `cbc_event-0.1.0-py3-none-any.whl`
  - sha256 `25d5730152a50ee064be1f380ce0ce1f96290924c221f7b268feafa719990f59`
- sdist: `cbc_event-0.1.0.tar.gz`
  - sha256 `ed6e8b1a0d5e471ea51fa9534c6b93129ef9b857a534c212e56af43677fc0c59`
- CBP quality manifest:
  - sha256 `a64555beb323099ff3810f23f5f45f09276233aa72c83866c806ae0513491b4c`
- source commit: `49f85b03377b63bf1b4ea2917282d7d71b14b120`

## Boundaries

- R01 is **not** a GitHub PASS yet. The local test-index result must never be
  presented as a GitHub R01 PASS.
- F05 is **not** a full-train PASS. The full CBS v1.7 release train was not
  available.
- This release does not include a tag or a GitHub Release until the human
  approval step in `RELEASE_CHECKLIST.md`.

## Verification commands

```bash
cbc-viewer verify <release-dir> --expect-gate PASS --expect-uploaded
cbc-viewer show <release-dir>
cbc-viewer render-body <release-dir> --out /tmp/cbc-body.md
```

`--expect-uploaded` is intentionally not satisfied for a local, non-uploaded
directory; R01 covers the uploaded case.
