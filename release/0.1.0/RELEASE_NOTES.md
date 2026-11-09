# CBC 0.1.0 — release notes

**Status: RELEASED.** Official `v0.1.0` reuses the exact `v0.1.0-rc.2` bytes.
No PyPI upload.

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

- CBP 1.2.2 official manifest: `e16823ce2c3b5ccbede74358742948b310b706c8a05d123420ea2aab89858d50`
- R02–R19: **18/18 assertions passed** (R16 Windows SKIP, Linux CI covers)
- R01: real GitHub **PASS** on official `v0.1.0` (exit 0, PASS, UPLOADED),
  after the pre-release rc.2 PASS; local test index is separate and is not a
  GitHub PASS
- F05: train-like with real CBS source **OK**; full CBS v1.7 train **NOT RUN**
- CI: Ubuntu + Windows green on the candidate commit.

## Artifacts

- wheel: `cbc_event-0.1.0-py3-none-any.whl`
  - sha256 `d77648af4f7bf6c1d67e57ee5d07a5d6a116b92aecdf89df289b7b73189d3f33`
- sdist: `cbc_event-0.1.0.tar.gz`
  - sha256 `024c54b6e417d428910c74bfb4e46fa6237b01ae7f95c58c1df7779f24307e17`
- CBP quality manifest:
  - sha256 `e16823ce2c3b5ccbede74358742948b310b706c8a05d123420ea2aab89858d50`
- source commit: `5cdc9a1b0d9a06f7bb6d5ad87f5a736fa24c8439`

## Boundaries

- The official `v0.1.0` is a release; `v0.1.0-rc.2` remains the pre-release
audit trail. The local test-index result must never be presented as a GitHub
R01 PASS.
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
