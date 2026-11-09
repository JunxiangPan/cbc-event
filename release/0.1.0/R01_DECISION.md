# R01 strategy decision

## Decision: B — pre-release test release first, then official 0.1.0

R01 is a **pre-release acceptance gate**, not a post-release smoke test.

A local test index is useful but **never** counts as a GitHub R01 PASS. The
current `local_r01_result.json` is evidence for the code path only; its
`scope` field says `local test index, not GitHub`.

### Rejected: A (publish 0.1.0 first)

A would make R01 a post-release check. If R01 failed, the official 0.1.0 tag
and release would already be public and could only be withdrawn or corrected by
a new version/ERRATUM. That is the wrong order for a release gate.

### Chosen: B (pre-release test release)

1. After human approval, create a **pre-release** GitHub release:
   - tag: `v0.1.0-rc.1` (pre-release, **not** `v0.1.0`);
   - target commit: `49f85b03377b63bf1b4ea2917282d7d71b14b120`;
   - assets: the exact wheel/sdist below, plus the release body;
   - no PyPI upload for the test release.
2. Run the real GitHub R01 against it:
   ```bash
   cbc-viewer verify --release-dir <dir> \
     --remote JunxiangPan/cbc-event --tag v0.1.0-rc.1 --expect-uploaded
   ```
3. Only if that returns exit 0, `gate_status=PASS`, `upload_status=UPLOADED`,
   and chain PASS, create the official release:
   - tag `v0.1.0` at the same commit;
   - upload the **same bytes** (no rebuild);
   - mark `v0.1.0` as the official release.
4. Keep `v0.1.0-rc.1` as a pre-release audit trail (or delete it under the
   human-approved release policy); never move it to `v0.1.0`.

### R01 status now

| Item | Status |
|---|---|
| R01 local test index | PASS (not GitHub) |
| R01 real GitHub | **NOT RUN** |
| Official 0.1.0 tag | **NOT CREATED** |
| Test release | **NOT CREATED** |

## What must not be written

- Do not write "R01 PASS" without the real `--remote`/`--expect-uploaded` run.
- Do not present `local_r01_result.json` as a GitHub result.
- Do not call the F05 train-like run a full-train PASS.

## Gate sequence

```text
human approval
  -> pre-release v0.1.0-rc.1
  -> real GitHub R01 (expect exit 0 + UPLOADED)
  -> official v0.1.0 (same bytes)
  -> post-release verification / PyPI decision (separate)
```

No tag or release is created by this document.
