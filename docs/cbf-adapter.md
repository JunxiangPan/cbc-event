# Optional CBF evidence adapter

Status: `0.2.0rc2` candidate interface. CBF is **optional**; CBC does not import
it and does not require it to run.

## Input

The adapter accepts a JSON document with:

```text
schema == "cbf-evidence/v1"
```

Required fields are validated locally: `tool`, `version`, `policy_version`,
`policy_sha256`, `policy_effective_sha256`, `project`, `repo`, `commit`,
`ref`, `surface`, `result`, `findings`, `scanned`, `generated_at`,
`evidence_sha256`.

Unknown schemas fail closed with `CbfEvidenceError`; the adapter never guesses
another CBF version.

## Python API

```python
from cbc_event import load_cbf_evidence

evidence = load_cbf_evidence(".cbf/evidence/20261112T053000Z-git-PASS.json")
view = evidence.view()          # cbc-cbf-view/v1
event = evidence.to_cbc_event(  # pure conversion, no append
    chain_id="cbc-main",
    seq=1,
)
```

`to_cbc_event()` returns a valid `cbc-event/v2` event with:

- `event_type="gate"` by default;
- `identity.producer_id="cbf"`, `identity.package_id` from the CBF project;
- `level`: PASS→INFO, BLOCK→WARN, ERROR→CRITICAL;
- a digest of the CBF evidence in `evidence_hash`;
- `detail` carries surface, result, policy hashes, declared evidence hash,
  hash status, findings count, and scan counts.

It does not append to an event store. The caller must supply a real
`chain_id`, `seq`, and `prev_hash` and must choose the append policy.

## CLI

```bash
cbc-viewer cbf-evidence --evidence .cbf/evidence/20261112T053000Z-git-PASS.json
cbc-viewer cbf-evidence --evidence .cbf/evidence/... --event \
  --chain-id cbc-main --seq 1
```

It is read-only: stdout only, no write/publish/sign operation.

## Hash status

`view["hash_status"]` is one of:

| status | meaning |
|---|---|
| `verified` | canonical digest (without `evidence_sha256`) matches |
| `verified_without_summary` | CBF 0.1.0 compatibility: the digest was sealed before the `summary` field was added |
| `mismatch` | digest does not match; the document is still readable but the mismatch is never hidden |

The `verified_without_summary` case is documented because CBF 0.1.0 adds
`summary` after sealing the digest. CBC does not import CBF to work around it.
A `mismatch` is readable in `view()` for diagnosis, but CLI conversion and
`to_cbc_event()` refuse it (fail-closed).

## Boundaries

- CBF is not required at install time.
- CBC does not replace CBF's gate or claim CBF PASS.
- The adapter does not verify CBF policy semantics; it parses the evidence
  interface only.
- `cbf.cbc-event/v1` envelopes are not required; `cbf-evidence/v1` is the
  input contract.
