# cbc-event

The shared event protocol for the CB ecosystem.

`cbc-event` is a standalone package: it has no dependency on CBS, CBP, CBR, CBM,
or CBC, and it does not open network ports. Producers append JSONL files; CBC
reads them.

## Version freeze and 0.2.0rc2

**`cbc-event 0.1.0` is the first formal protocol version of the CB ecosystem.**
Within `0.1.x` only optional fields may be appended. Existing required fields
must not be deleted, renamed, reordered, or have their type or meaning changed.

`0.2.0rc2` adds an opt-in `cbc-event/v2` protocol and keeps v1 as the default
emit format. v1 events remain readable; unknown schemas fail closed. See
[`docs/event-protocol-v2.md`](docs/event-protocol-v2.md), the
[`migration guide`](docs/migration-0.2.md), the
[`compatibility matrix`](docs/compatibility-matrix.md), and the
[`optional CBF adapter`](docs/cbf-adapter.md).

Once CBS 1.6.4 and CBP 0.1.0 begin consuming `cbc-event`, the `0.1.0` schema and
canonicalization rules are frozen. Any breaking change must become `0.2.0` with
a migration note.

## Event

```json
{
  "schema": "cbc-event/v1",
  "event_id": "4b7d2e42-6f0e-4f8f-9f0d-6a7d3c1e9b21",
  "timestamp": "2026-11-06T15:30:00.123Z",
  "source": {
    "kind": "CBP",
    "name": "cbp-action",
    "version": "0.1.0",
    "instance": "ci-01"
  },
  "level": "WARN",
  "action": "coverage.fail",
  "detail": {"summary": "coverage below floor", "measurement": 79.4},
  "evidence_hash": "sha256:...",
  "prev_hash": "sha256:...",
  "event_hash": "sha256:...",
  "seq": 1842
}
```

## Minimal integration

Three lines:

```python
from cbc_event import Client
client = Client(enabled=True, source={"kind": "CBR", "name": "cbr", "version": "0.1.0", "instance": "local"})
client.emit("WARN", "hallucinated_package", {"package": "example"})
```

Default is disabled:

```python
from cbc_event import Client
client = Client()  # no directory, no thread, no socket
```

## Reading

```python
from cbc_event import read_events
events, warnings, problems = read_events(path)
```

Reader behavior:

- missing required fields -> `problems`;
- unknown fields -> `warnings`, event is retained;
- chain break or hash mismatch -> `problems`/`CRITICAL`, already-read events are
  retained, nothing is silently repaired.

`validate_event()` is exported for consumers that do not use the emit client:

```python
from cbc_event import validate_event
report = validate_event(event, expected_seq=1, prev_hash="sha256:" + "0" * 64)
report["problems"], report["warnings"], report["critical"]
```

## CBC read-only viewer (`cbc_viewer 0.2.0rc2`)

The viewer is in the same repository but is a separate package/entry point. It
uses only the standard library and `cbc_event.canonical`; `pip install
cbc-event` does not pull a third-party viewer dependency.

```bash
pip install -e ".[viewer]"

cbc-viewer verify --scope release --release-dir ./release
cbc-viewer verify --scope event-log --event-dir ~/.cb/events --chain ./events/cbc-chain.json
cbc-viewer show --report ./cbc-chain-report.json
cbc-viewer render-body --report ./cbc-chain-report.json --format appendix
```

The viewer is **read-only**: there is no upload, publish, delete, tag, release
edit, or force-update command. Its GitHub transport accepts only `GET`/`HEAD`;
`verify` may write one report outside the verified source directory, and
`render-body` is stdout-only (no `--report-out`, no write path). See
[`docs/release-chain.md`](docs/release-chain.md) for the chain format, exit
codes, tamper-detection matrix, and the body base/appendix rule.
`docs/standalone-install.md` records the clean-environment wheel/CLI check.

Event logs may mix v1 and v2; `chain_profile` is `event-log/v1`,
`event-log/v2`, or `event-log/mixed`, and unknown fields are warnings. Unknown
schemas are exit 2 `UNSUPPORTED_EVENT_VERSION`.

Two integration facts are deliberate:

- CBC binds identity by **version + tag**, not `package_id`; CBE/CBP may still
  write the producer id there. This will be tightened only after CBE/CBP define
  the target-package semantics (tracked as a v1.8 TODO).
- The release body hash must declare `body_hash_scope`. `sealed-v1` accepts
  `base` only: CBP hashes the base body, then the CBC appendix is appended and
  binds the chain root. A missing `body_hash_scope` or `full` is an input error,
  never a silent fallback.

Reports and body blocks carry both counts: `link_count` includes the manifest
header and every link, while `asset_link_count` counts only `kind=asset` leaves.
Consumers must not compare `link_count` to the number of assets.

`F05` (real CBS body-generator compatibility) is still **not a full-train PASS**.
The standalone CI cannot provide the CBS v1.7 release train; train-like coverage
is recorded separately and the complete train remains an external blocker. See
[`docs/f05-train-evidence.md`](docs/f05-train-evidence.md).

## Compatibility

`cbc-event 0.1.x` may only add fields. Existing field names and types are frozen.
Consumers must ignore unknown fields and emit a warning.

`0.2.x` reads v1 and v2. v2 is opt-in; v1 remains the default emit format.
Unknown versions are fail-closed (`UNSUPPORTED_EVENT_VERSION`), never treated as
v1 and never skipped.

## Development

```bash
python -m unittest discover -s tests -v
# POSIX:
COVERAGE_FILE=.coverage.protocol python -m coverage run --branch --source=./cbc_event -m unittest discover -s tests
COVERAGE_FILE=.coverage.protocol python -m coverage report --fail-under=90
COVERAGE_FILE=.coverage.viewer python -m coverage run --branch --source=./cbc_viewer -m unittest discover -s tests
COVERAGE_FILE=.coverage.viewer python -m coverage report --fail-under=90
# Windows PowerShell:
# $env:COVERAGE_FILE=".coverage.protocol"; python -m coverage run --branch --source=./cbc_event -m unittest discover -s tests
# $env:COVERAGE_FILE=".coverage.protocol"; python -m coverage report --fail-under=90
# $env:COVERAGE_FILE=".coverage.viewer"; python -m coverage run --branch --source=./cbc_viewer -m unittest discover -s tests
# $env:COVERAGE_FILE=".coverage.viewer"; python -m coverage report --fail-under=90
```

No runtime third-party dependencies. `pytest` and `coverage` are optional test
dependencies.

## CBF privacy gate (Phase 0)

**CBF is not integrated yet.** Status: `PENDING_CBF_0.1.0`; there is **no CBF
PASS** for this project or its releases. The `cbf-privacy-gate` job name is reserved as a manual-only
workflow that fails closed until CBF is installed; it is not a PR check and has
no `continue-on-error` / `if: false` placeholder. See [`docs/CBF_ADOPTION.md`](docs/CBF_ADOPTION.md).

Once CBF 0.1.0rc1 is available, this project must pin a CBF policy and run
`cbf gate --surface git` before upload/release. Until then, do not describe the
project as CBF-compatible or CBF-passed.

