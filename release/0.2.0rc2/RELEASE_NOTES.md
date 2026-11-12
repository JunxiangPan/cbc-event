# CBC 0.2.0rc2 — pre-release notes

**Status: pre-release candidate. F05 is NOT RUN. Not `0.2.0` stable. No PyPI upload.**

## Changes from rc1

- Optional `cbf-evidence/v1` reader/adapter:
  - human-readable viewer output: result, findings, policy hashes;
  - `--json` normalized view;
  - pure conversion to `cbc-event/v2`;
  - no CBF import, no CBF runtime dependency;
  - unknown CBF schema fails closed.
- CBF Phase 0 adoption status: `PENDING_CBF_0.1.0`; no CBF PASS.
  The adapter is visualization, not a CBF gate.

## Artifacts

| Artifact | SHA256 |
|---|---|
| `cbc_event-0.2.0rc2-py3-none-any.whl` | `a96e26713014dafaae20b48c1f1890c0d7b7bbf11829fd2a5ebb9880286b3c0e` |
| `cbc_event-0.2.0rc2.tar.gz` | `cd674028272b374dfa44fa69b5806c206ace257d815c90bcf98c1d2ba9799129` |

## Verification

- 169 tests passed, 1 local skip.
- Protocol coverage 93%; viewer coverage 90%.
- CBF adapter tests: real fixture read, unknown schema fail-closed, no `cbf`
  import.
- Clean-env rc2 wheel install and CBF text/JSON view verified.
- 0.1.x regression and dual-read remain green.

## Boundaries

- **F05 full CBS v1.7 train: NOT RUN.** No full-train PASS is claimed.
- No stable 0.2.0.
- No PyPI upload.
- CBF is not released; no CBF PASS exists.
- `v0.1.0` and `v0.2.0rc1` tags are not moved.
