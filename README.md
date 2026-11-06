# cbc-event

The shared event protocol for the CB ecosystem.

`cbc-event` is a standalone package: it has no dependency on CBS, CBP, CBR, CBM,
or CBC, and it does not open network ports. Producers append JSONL files; CBC
reads them.

## Version freeze

**`cbc-event 0.1.0` is the first formal protocol version of the CB ecosystem.**
Within `0.1.x` only optional fields may be appended. Existing required fields
must not be deleted, renamed, reordered, or have their type or meaning changed.

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

## Compatibility

`cbc-event 0.1.x` may only add fields. Existing field names and types are frozen.
Consumers must ignore unknown fields and emit a warning.

## Development

```bash
python -m unittest discover -s tests -v
python -m coverage run --branch --source=cbc_event -m unittest discover -s tests
python -m coverage report --fail-under=90
```

No runtime third-party dependencies. `pytest` and `coverage` are optional test
dependencies.
