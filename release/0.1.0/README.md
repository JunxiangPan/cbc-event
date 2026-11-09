# CBC 0.1.0 release package — candidate

**Status: PARTIAL / NOT RELEASED. No tag, no GitHub Release, no PyPI upload.**

This directory is the prepared 0.1.0 release package. It is intentionally not
tagged. Human approval is required before the pre-release and before the
official release.

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
| R01 real GitHub | **NOT RUN** |
| F05 train-like | OK |
| F05 full CBS train | **NOT RUN** |
| CI | Ubuntu + Windows green |

## R01 decision

**B — pre-release test release first, then official 0.1.0.** R01 is a
pre-release acceptance gate. Local R01 is never written as GitHub R01 PASS.

## Source and artifacts

- source: `49f85b03377b63bf1b4ea2917282d7d71b14b120`
- wheel: `25d5730152a50ee064be1f380ce0ce1f96290924c221f7b268feafa719990f59`
- sdist: `ed6e8b1a0d5e471ea51fa9534c6b93129ef9b857a534c212e56af43677fc0c59`
- manifest: `a64555beb323099ff3810f23f5f45f09276233aa72c83866c806ae0513491b4c`

## Boundaries

- No tag/release/PyPI action in this package.
- F05 full-train PASS is not claimed.
- The manifest's `artifact_repository.run_id` is local
  (`local-cbc-build-once`), not a GitHub run; the RC2 object shape is valid but
  remote build-once coordinate verification remains a release-policy question.
