# Migration guide: cbc-event 0.1.x → 0.2.0rc3

`0.2.0rc3` is opt-in. Existing 0.1.x producers, readers, and consumers keep
working without editing their event stream.

## Compatibility promise

- `cbc-event/v1` events remain readable by the 0.2.x reader.
- `EventStore`, `Client`, and the module-level `emit()` still default to
  **v1**. Upgrading the package does not silently change the emitted schema.
- The v1 schema and canonicalization rules are unchanged.
- No v1 field is deleted, renamed, or re-typed in v2. v2 only adds fields.

## Producer: opt in to v2

```python
from cbc_event import EventStore

store = EventStore(
    "/var/lib/cb/events",
    source={"kind": "cbp", "name": "cbp-action", "version": "1.3.1", "instance": "ci-01"},
    enabled=True,
    protocol_version="v2",
    identity={
        "package_id": "cbc",
        "producer_id": "cbp",
        "package_version": "0.2.0",
    },
    chain_id="cbc-main",
)
store.emit(
    "INFO",
    "coverage.pass",
    {"coverage": 93.1},
    event_type="gate",
)
```

A v2 event must supply `event_type`. The store refuses to emit v2 without
`identity` and `chain_id`, and refuses `event_type` on a v1 store.

## Consumer: read both versions

```python
from cbc_event import read_events

events, warnings, problems = read_events("/var/lib/cb/events")
```

- v1 and v2 events are returned in one list.
- unknown fields are in `warnings`;
- an unknown schema is in `problems` and the event is not returned;
- chain breaks stay in `problems`/`CRITICAL`; nothing is repaired.

The viewer negotiates automatically:

```bash
cbc-viewer verify --scope event-log --event-dir ./events
```

`chain_profile` is `event-log/v1`, `event-log/v2`, or `event-log/mixed`;
`inputs.event_versions`, `inputs.event_chain_ids`, and
`inputs.event_warnings` expose the negotiation result.

## Identity mapping

| v1 | v2 |
|---|---|
| `source.kind/name/version/instance` | unchanged |
| none | `identity.package_id` |
| none | `identity.producer_id` |
| none | `identity.package_version` |
| none | `event_type` |
| none | `chain_id` |

`package_id` is the subject package, `producer_id` is the producer (for example
`cbc` and `cbp`). The event source remains traceability metadata.

## Migration window

- 0.2.x reads v1 and v2; no producer is forced to move.
- v2 is opt-in per event stream.
- CBE/CBP/CBS/CBM can stay on v1 indefinitely during 0.2.x.
- Removing v1 is not part of 0.2.x. A future removal would require a new
  protocol version and a separate migration decision.
- This release is `0.2.0rc3`; there is no stable 0.2.0 and no published PyPI
  stable artifact from this branch.

## Rollback

Set `protocol_version="v1"` (the default) and keep reading the mixed log. A v2
event already written is not rewritten or deleted; a v1-only reader will
fail-closed on it rather than misinterpret it.
