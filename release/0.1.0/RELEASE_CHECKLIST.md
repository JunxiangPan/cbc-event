# CBC 0.1.0 release checklist

**Current state: NOT APPROVED — no tag, no release, no PyPI upload.**

## 0. Human approval

- [ ] Human approves the 0.1.0 candidate and the R01 strategy (B).
- [ ] Human approves creating the pre-release `v0.1.0-rc.1`.
- [ ] Human approves the final `v0.1.0` release after R01 passes.

No tag/release action is performed before the corresponding approval.

## 1. Candidate inputs

- Source commit: `49f85b03377b63bf1b4ea2917282d7d71b14b120`
- wheel: sha256 `25d5730152a50ee064be1f380ce0ce1f96290924c221f7b268feafa719990f59`
- sdist: sha256 `ed6e8b1a0d5e471ea51fa9534c6b93129ef9b857a534c212e56af43677fc0c59`
- manifest: sha256 `a64555beb323099ff3810f23f5f45f09276233aa72c83866c806ae0513491b4c`
- CBP producer: 1.2.2 official; contract v1.7.1 RC2.

- [ ] Reconfirm artifacts are the ones from the release commit (no rebuild).
- [ ] Reconfirm `cbc_viewer.validate_cbp` PASS on the manifest.
- [ ] Reconfirm R02–R19 result is the 18/18 run with these exact hashes.

## 2. Pre-release test release

- [ ] Create a **GitHub pre-release** `v0.1.0-rc.1` at the source commit.
- [ ] Upload the exact wheel and sdist above.
- [ ] Upload the release body that matches `release_body_hash`.
- [ ] Do **not** upload the test release to PyPI.
- [ ] Do **not** move or reuse `v0.1.0`.

## 3. Real GitHub R01 (pre-release acceptance)

```bash
cbc-viewer verify --release-dir <dir> \
  --remote JunxiangPan/cbc-event --tag v0.1.0-rc.1 --expect-uploaded
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

- [ ] Real GitHub R01 for `v0.1.0-rc.1` passed.
- [ ] R02–R19 18/18 still tied to the same hashes.
- [ ] Human approval for the official release.
- [ ] F05 boundary is disclosed; full CBS v1.7 train is not claimed.

Actions:

- [ ] Create `v0.1.0` at the same source commit.
- [ ] Upload the **same bytes** (no rebuild, no rehash).
- [ ] Mark `v0.1.0` as the official release.
- [ ] Keep `v0.1.0-rc.1` as a pre-release audit trail (or delete it only under
      the approved release policy; never retag it).

## 5. Post-release (not a substitute for pre-release R01)

- [ ] Optionally rerun `cbc-viewer verify --remote ... --tag v0.1.0
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
