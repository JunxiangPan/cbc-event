# cbc-event protocol v2 (0.2.0rc1)

Status: **release candidate, opt-in**. `cbc-event/v1` remains supported and is
still the default emit format in this release.

This protocol is transport-neutral JSONL with a per-file hash chain. It is not
a release tool, not a signing tool, and has no network listener.

## Version negotiation

| schema | read by 0.2.x | emit default |
|---|---|---|
| `cbc-event/v1` | yes (frozen 0.1.x format) | **yes** |
| `cbc-event/v2` | yes (opt-in) | no; opt-in only |
| any other schema | **fail-closed** | no |

Version negotiation happens before field validation. The viewer reports an
unknown version as exit `2`, `gate_status=FAIL`, error
`UNSUPPORTED_EVENT_VERSION`; it never treats the event as v1 and never skips it.
The library `validate_event()` reports `unsupported event schema: ...` as an
error, and `read_events()` returns it in `problems` without retaining the
event.

## v2 required fields

A v2 event contains every v1 field plus:

```json
{
  "schema": "cbc-event/v2",
  "event_id": "4b7d2e42-6f0e-4f8f-9f0d-6a7d3c1e9b21",
  "identity": {
    "package_id": "cbc",
    "producer_id": "cbp",
    "package_version": "0.2.0"
  },
  "event_type": "observation",
  "chain_id": "cbc-main"
}
```

Strict rules:

- `event_id` is a UUID (required in v2; optional in v1).
- `identity.package_id` and `identity.producer_id` are lowercase package ids
  (`^[a-z][a-z0-9._-]*$`).
- `identity.package_version` is `X.Y.Z` (no leading `v`).
- `source.version` is also `X.Y.Z` in v2.
- `event_type` is one of: `observation`, `decision`, `gate`, `release`,
  `error`.
- `chain_id` is 1–128 characters of `[A-Za-z0-9._:-]`, starting
  alphanumeric.
- Hash values are lowercase `sha256:<64 hex>`.
- All events in one event-log directory that are v2 must share one
  `chain_id`. A mismatch is `chain_identity_mismatch` (exit 3), not repaired.

v1 events do not have `identity`, `event_type`, or `chain_id`. They remain
valid; unknown fields in either version are warnings and the event is retained.

## Chain semantics

The hash-chain algorithm is unchanged from v1:

```text
event_hash = "sha256:" + sha256(prev_hash + "\n" + canonical_json(event without event_hash))
```

- `seq` starts at 1 and is contiguous across v1/v2 events.
- `prev_hash` starts at `sha256:` + 64 zeros.
- `head.json` remains the same shape.
- Mixed v1/v2 logs are supported; `chain_profile` is
  `event-log/mixed`. A v2-only log is `event-log/v2`; a v1-only log is
  `event-log/v1`.
- Unknown fields are warnings; chain errors are never warnings and never
  trigger a repair.

## Error categories

| category | examples | result |
|---|---|---|
| version | unknown schema | exit 2, `UNSUPPORTED_EVENT_VERSION` |
| structure | missing field, bad JSON, bad type | exit 2/3; reported, not repaired |
| identity | bad package id, bad version, missing identity | event problem; fail-closed |
| chain | seq gap, prev hash, event hash, chain_id mismatch | exit 3, chain failure |
| unknown field | future field | warning; event retained |

Release-scope body/appendix classification is unchanged and lives in
`docs/release-chain.md`; event v2 does not alter the release chain.

## Non-goals

- No event deletion, rewriting, signing, release publishing, or upload.
- No dependency on CBE/CBP/CBM.
- v2 is not a CBE/CBP replacement or a forced migration.

See `migration-0.2.md` and `compatibility-matrix.md`.
