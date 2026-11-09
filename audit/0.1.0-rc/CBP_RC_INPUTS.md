# CBP 1.2.0 RC inputs

## Identity

| item | value |
|---|---|
| CBP repo | `JunxiangPan/cbp-action` |
| code commit | `5da8b87` (PR #1 head at audit time) |
| PR | <https://github.com/JunxiangPan/cbp-action/pull/1> |
| RC build run | `42539271566` (success) |
| code commit for run | `5da8b87bc92d5fbac5d24f434e97c672ed1bbd68` |
| artifact name | `cbp-rc` |

The CBP 1.2.0 version is **RC only**: no v1.2.0 tag, no v1.2.0 GitHub Release,
no PyPI 1.2.0. The RC artifact is not a published package.

## Artifact hashes

From the downloaded `cbp-rc` artifact (raw `raw/CBP_RC_ASSETS.sha256` and
`raw/CBP_RC_ARTIFACT.sha256`):

```text
40b0f5f827acefe4f5f9a5891a5d70be9d53557435acd721706c6a9f01fff320  cbp_action-1.2.0-py3-none-any.whl
e30fa8319103e31ec85e9c1f514c9a14de267c35067c263ae245d7eec5c32604  cbp_action-1.2.0.tar.gz
4d18155845301544b90e87d671b759630dedd924b5db60266276b1845117802c  RC_ASSETS.sha256
```

The wheel was installed only into a temporary target directory for execution;
no CBP repository file was changed.

## Real CBP execution on CBC

### v12 rule report

```bash
PYTHONPATH=<temp-cbp-rc-lib> python -m cbp.cli \
  --root cbc-event --v12 --v12-report <audit>/cbc-v12-report.json
```

Result: `CBP_V12_RESULT=PASS rules=12 blocking_failed=false warning_failed=false`.
Raw: `raw/cbp-v12.stdout`, `raw/cbc-v12-report.json`.

### Normal gate report

```bash
PYTHONPATH=<temp-cbp-rc-lib> python -m cbp.cli \
  --root cbc-event --mode audit \
  --report-json <audit>/cbc-gate-report.json
```

Result: `CBP_GATE_STATUS=PASS`, `CBP_APPLICABLE=1`, `CBP_SKIP_RATIO=0.000000`,
`CBP_BLOCKING_SKIP=false`. Eight gates were `SKIPPED (not configured)`; the
only applicable gate was `encoding=PASS`. Raw: `raw/cbp-gates.stdout`,
`raw/cbc-gate-report.json`.

This report has `body_hash_scope: "base"` but **does not** contain
`artifact_hashes`, `release_body_hash`, or `evidence_sha256`; it is not a
contract §5 quality manifest. CBC rejects it explicitly as
`input_error: CBP manifest missing field: artifact_hashes`
(`raw/real-cbp-report-validation.stdout`).

## Why this input cannot be passed to CBC as a manifest

See `CBP_MANIFEST_GAP.md`.

## Post-audit re-run

After the audit package was added, the same CBP 1.2.0 RC v12 command was rerun
to prove the evidence package does not change the gate result: **12/12 PASS**
(`raw/cbp-v12-after-audit.stdout`, `raw/cbc-v12-report-after-audit.json`).
