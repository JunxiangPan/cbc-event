# CBF adoption — CBC

Status: **PENDING_CBF_0.1.0**

- surfaces: `git` / `api` / `local-ai`
- planned gate: `cbf gate --surface git`
- planned CI job: `cbf-privacy-gate`
- evidence format: `cbf-evidence/v1`

CBC has **not** integrated CBF. There is **no CBF PASS**, and CBC does not
claim CBF compatibility. CBF is an independent project; CBC does not import
it and does not require it to be installed.

## Phase 0 (current)

- Adoption documented here.
- A fail-closed `cbf-privacy-gate` workflow is reserved; it exits 1 with
  `CBF_PENDING_0.1.0` and does not produce a PASS.
- Existing CI does not fake a CBF result and does not use `continue-on-error`
  or `if: false` to bypass it.
- No GitHub Release, PyPI upload, or git push is claimed to have CBF evidence.

## Phase 1 (after CBF 0.1.0rc1)

- Add `cbf.policy.json` pinned to the CBF policy version/hash.
- Wire `cbf-privacy-gate` into the release/upload path and add the local
  pre-push `cbf gate --surface git`.
- Block upload/release on CBF failure; record `cbf-evidence/v1`.

## Boundary

CBC will read cbf-evidence/v1 as an optional evidence reader/adapter; CBF is not a runtime dependency.
