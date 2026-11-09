# Viewer paths — scope errors vs upload precondition

These are fixture-based executable checks (not a real CBP manifest). They verify
the viewer's control flow and exit/status mapping after the error-code changes.

Raw: `raw/viewer-paths.stdout`

| check | test | expected |
|---|---|---|
| CBP manifest missing `body_hash_scope` | S17 | exit 2, `gate_status=FAIL`, `error.code=MISSING_BODY_HASH_SCOPE`, `cbc_chain_status=PASS` |
| CBP `body_hash_scope=full` | S18 | exit 2, `gate_status=FAIL`, `error.code=UNSUPPORTED_BODY_HASH_SCOPE` |
| `--expect-uploaded` without confirmation | F03 | exit 2, `gate_status=PRECONDITION_FAIL`, `error.code=expect_uploaded_unmet`, `upload_status=NOT_UPLOADED` |

Command:

```bash
python -m unittest \
  tests.e2e.test_exit_contract.ExitContractTests.test_s17_missing_body_hash_scope_is_2_fail_not_precondition \
  tests.e2e.test_exit_contract.ExitContractTests.test_s18_full_body_hash_scope_is_2_unsupported \
  tests.e2e.test_f6.F6Tests.test_f03_expect_uploaded_without_remote_is_2 -v
```

Result: `Ran 3 tests ... OK`.

The real CBP report from RC (`raw/cbc-gate-report.json`) has
`body_hash_scope: "base"`, so it cannot exercise the missing/full branches. Those
branches remain unit-verified until a real malformed CBP manifest is supplied.
