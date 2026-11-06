# cbc-event

The shared event protocol for the CB ecosystem.

`cbc-event` is a standalone package: it has no dependency on CBS, CBP, CBR, CBM,
or CBC, and it does not open network ports. Producers append JSONL files; CBC
reads them.

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

## Usage

```python
from cbc_event import emit, Client

# Default: disabled, no directory, no thread, no socket.
client = Client(event_dir=os.path.expanduser("~/.cb/events"), enabled=False)

# Enable explicitly:
client = Client(event_dir=os.path.expanduser("~/.cb/events"), enabled=True,
                 source={"kind": "CBP", "name": "cbp-action",
                         "version": "0.1.0", "instance": "ci-01"})
client.emit("WARN", "coverage.fail", {"measurement": 79.4})
```

Reading:

```python
from cbc_event import read_events
events, warnings, problems = read_events(path)
```

- unknown fields: kept, reported as `WARN`, never fatal;
- chain gaps: reported in `problems`, never fatal to the reader;
- append-only: this package never rewrites or deletes event lines.

## Compatibility

`cbc-event 0.1.x` may only add fields. Existing field names and types are frozen.
Consumers must ignore unknown fields and emit a warning.

## Development

```bash
python -m unittest discover -s tests -v
```

No runtime third-party dependencies.
