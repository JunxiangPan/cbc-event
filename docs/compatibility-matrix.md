# Compatibility matrix

Status: `cbc-event` / `cbc_viewer` **0.2.0rc1**; `0.1.0` remains the stable
release. No stable 0.2.0 is declared.

## Event readers

| Input | 0.1.x reader | 0.2.0rc1 reader | Behavior |
|---|---|---|---|
| `cbc-event/v1` event | PASS | PASS | v1 remains frozen |
| `cbc-event/v2` event | fail-closed | PASS | unknown fields are warnings, schema is negotiated |
| mixed v1/v2 log | fail-closed | PASS | `event-log/mixed`; seq continuity across versions |
| `cbc-event/v3` / unknown schema | fail-closed | fail-closed (exit 2) | `UNSUPPORTED_EVENT_VERSION`; never read as v1 |
| v2 with unknown future field | n/a | PASS + warning | event retained; warning in report inputs |
| v2 with bad identity/type/chain_id | n/a | event problem | fail-closed; no repair |
| v2 chain_id inconsistent | n/a | exit 3 | `chain_identity_mismatch` |
| v1 with unknown future field | PASS + warning | PASS + warning | unchanged |

## Producers

| Producer API | Default schema | Opt-in | Notes |
|---|---|---|---|
| `EventStore` 0.1.x | v1 | n/a | unchanged |
| `EventStore` 0.2.0rc1 | v1 | `protocol_version="v2"` | requires `identity`, `chain_id`, `event_type` |
| `Client` 0.2.0rc1 | v1 | v2 kwargs | disabled by default |
| `emit()` 0.2.0rc1 | v1 | v2 kwargs | disabled unless enabled |

## Viewer scopes

| Scope | 0.2.0rc1 |
|---|---|
| release chain | unchanged from 0.1.0 (sealed-v1) |
| event log v1 | PASS |
| event log v2 | PASS |
| event log mixed | PASS |
| event log unknown version | exit 2 fail-closed |
| write/publish/sign | not supported (read-only) |

## Dependencies

| Requirement | Status |
|---|---|
| CBE installed | not required |
| CBP installed | not required |
| CBM installed | not required |
| CBS installed | not required for event/release reading |
| CBE/CBP/CBM imports in `cbc_event`/`cbc_viewer` | none |
| third-party runtime dependency | none |
| network listener | none |

## F05

F05 is an external CBS release-train integration case. `train-like` coverage is
not a full-train PASS. See `docs/f05-train-evidence.md` for the exact command,
inputs, outputs, and remaining blocker.

## Version policy

- `0.1.x` consumers continue to work.
- `0.2.0rc1` is opt-in.
- `v1` events are never silently rewritten.
- `v1` removal is not part of 0.2.x.
