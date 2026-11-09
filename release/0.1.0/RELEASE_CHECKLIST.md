# CBC 0.1.0 release checklist

**Current state: RELEASED — official `v0.1.0`; no PyPI upload.**

## 0. Human approval

- [x] Human approved the 0.1.0 candidate and the R01 strategy (B).
- [x] Human approved creating a pre-release.
- [x] Human approved the final `v0.1.0` release after R01 passed.

The official actions below were performed after the corresponding approval.

## 1. Candidate inputs

- Source commit: `5cdc9a1b0d9a06f7bb6d5ad87f5a736fa24c8439`
- wheel: sha256 `d77648af4f7bf6c1d67e57ee5d07a5d6a116b92aecdf89df289b7b73189d3f33`
- sdist: sha256 `024c54b6e417d428910c74bfb4e46fa6237b01ae7f95c58c1df7779f24307e17`
- manifest: sha256 `e16823ce2c3b5ccbede74358742948b310b706c8a05d123420ea2aab89858d50`
- CBP producer: 1.2.2 official; contract v1.7.1 RC2.

- [ ] Reconfirm artifacts are the ones from the release commit (no rebuild).
- [ ] Reconfirm `cbc_viewer.validate_cbp` PASS on the manifest.
- [ ] Reconfirm R02–R19 result is the 18/18 run with these exact hashes.

## 2. Pre-release test release

- [x] Create a **GitHub pre-release** `v0.1.0-rc.2` at the source commit.
- [x] Upload the exact wheel and sdist above.
- [x] Upload the release body that matches `release_body_hash`.
- [ ] Do **not** upload the test release to PyPI.
- [ ] Do **not** move or reuse `v0.1.0`.

## 3. Real GitHub R01 (pre-release acceptance)

```bash
cbc-viewer verify --release-dir <dir> \
  --remote JunxiangPan/cbc-event --tag v0.1.0-rc.2 --expect-uploaded
```

PASS requires all of:

- exit code 0
- `gate_status` PASS
- `upload_status` UPLOADED
- `cbc_chain_status` PASS
- remote body and both asset digests match

- [ ] Record the raw stdout JSON and the release URL.
- [ ] Confirm `local_r01_result.json` was **not** substituted for this run.

If R01 fails: do not create `v0.1.0`; fix and repeat with a new pre-release tag.

## 4. Official 0.1.0 release

Preconditions:

- [x] Real GitHub R01 for `v0.1.0-rc.2` passed.
- [x] R02–R19 18/18 still tied to the same hashes.
- [x] Human approval for the official release.
- [x] F05 boundary is disclosed; full CBS v1.7 train is not claimed.

Actions:

- [x] Create `v0.1.0` at the same source commit.
- [x] Upload the **same bytes** (no rebuild, no rehash).
- [x] Mark `v0.1.0` as the official release.
- [x] Keep `v0.1.0-rc.1` and `v0.1.0-rc.2` as pre-release audit trails (or
      delete them only under the approved release policy; never retag them).

## 5. Post-release (not a substitute for pre-release R01)

- [x] Optionally rerun `cbc-viewer verify --remote ... --tag v0.1.0
      --expect-uploaded` against the official release as a post-release smoke
      check.
- [ ] PyPI publication is a separate decision; this checklist does not upload
      to PyPI.

## 6. Rollback rule

If the official release is found bad after publishing, do not force-move
`v0.1.0`; publish a new version/ERRATUM under the contract rules.

## 7. Explicit non-claims

- R01 local test index is **not** GitHub R01 PASS.
- F05 train-like is **not** full-train PASS.
- The current state is **0.1.0 RC PARTIAL**, not a completed release.
