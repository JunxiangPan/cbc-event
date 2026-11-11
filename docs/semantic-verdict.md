# Optional semantic-verdict/v1 reader

Status: `0.2.0rc3` candidate. Read-only; no semantic model is run by CBC.

CBC reads the standalone JSON sidecar defined by CBM's
`semantic-verdict/v1` contract. It does not import CBF/CBP/CBE/CBM and does not
require any of them to be installed.

## Important boundary

A semantic verdict is a **semantic signal**, not a factual proof, not a CBF
result, and not a CBC gate PASS. CBC displays it with an explicit disclaimer.
Do not use it as evidence that a release is correct, secure, or approved.

## Schema

Required:

- `schema`: `semantic-verdict/v1`
- `verdict`: `PASS` / `FAIL` / `NOT_RUN`
- `subject.package_id`
- `subject.artifact_sha256` (64 hex)
- `generated_at`
- `evidence_sha256`: canonical SHA-256 excluding this field

Optional:

- `confidence` (0..1)
- `subject.version`
- `findings` (array of objects; a finding may carry `confidence`)
- `policy` (object)

Unknown schemas fail closed. A hash mismatch fails closed. Unknown fields are
retained in the raw `evidence` view, not silently discarded.

## Viewer

```bash
cbc-viewer semantic-verdict --evidence semantic-verdict.json
cbc-viewer semantic-verdict --evidence semantic-verdict.json --json
```

Default output shows:

- verdict;
- confidence (or `not provided`);
- subject package/version/artifact hash;
- evidence hash;
- findings with severity/rule/path/line/confidence;
- the disclaimer that it is a semantic signal, not factual proof.

`--json` emits the full normalized `cbc-semantic-view/v1`, including the
original evidence document and policy object.

## Python

```python
from cbc_event import SemanticVerdict, load_semantic_verdict

verdict = load_semantic_verdict("semantic-verdict.json")
view = verdict.view()
```

## Non-goals

- No CBF/CBP/CBE/CBM import.
- No semantic model execution.
- No write, upload, release, or gate action.
- No conversion into a CBC PASS or CBF PASS.
