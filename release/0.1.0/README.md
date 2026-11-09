# CBC 0.1.0 release package — released

**Status: RELEASED — official `v0.1.0` published from the exact `v0.1.0-rc.2` bytes; no PyPI upload.**

This directory is the 0.1.0 release package. The official tag is `v0.1.0` at
`5cdc9a1`; the package/hash documentation is at `153088c`, with a later
`TAG_NOTE.md`. `v0.1.0-rc.2` remains as the pre-release audit trail.

| File | Purpose |
|---|---|
| `RELEASE_NOTES.md` | candidate release notes and artifact hashes |
| `HASHES.md` | source, artifacts, manifest, CBE/chain provenance |
| `R01_DECISION.md` | strategy B: pre-release R01, then official 0.1.0 |
| `RELEASE_CHECKLIST.md` | approval, pre-release, R01, official release |
| `quality-manifest.json` | CBP 1.2.2 RC2 manifest used by this candidate |
| `RELEASE_BODY.md` | body used for the manifest/body hash |

## Current gate status

| Gate | Status |
|---|---|
| R02–R19 | 18/18 assertions |
| R16 | Windows SKIP; Linux CI covers |
| R01 local test index | PASS (not GitHub) |
| R01 real GitHub | **PASS** on official `v0.1.0` |
| F05 train-like | OK |
| F05 full CBS train | **NOT RUN** |
| CI | Ubuntu + Windows green |

## R01 decision

**B — pre-release test release first, then official 0.1.0.** R01 is a
pre-release acceptance gate; the real pre-release run passed. Local R01 is
never written as GitHub R01 PASS. Official `v0.1.0` was created after the pre-release R01 passed.

## Source and artifacts

- source: `5cdc9a1b0d9a06f7bb6d5ad87f5a736fa24c8439`
- wheel: `d77648af4f7bf6c1d67e57ee5d07a5d6a116b92aecdf89df289b7b73189d3f33`
- sdist: `024c54b6e417d428910c74bfb4e46fa6237b01ae7f95c58c1df7779f24307e17`
- manifest: `e16823ce2c3b5ccbede74358742948b310b706c8a05d123420ea2aab89858d50`

## Boundaries

- Official tag/release created; no PyPI action in this package.
- F05 full-train PASS is not claimed.
- The manifest's `artifact_repository.run_id` is local
  (`local-cbc-build-once`), not a GitHub run; the RC2 object shape is valid but
  remote build-once coordinate verification remains a release-policy question.
