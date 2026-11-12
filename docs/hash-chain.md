# Hash chain rules

Every event has:

- `seq`: monotonically increasing integer, starting at 1;
- `prev_hash`: `sha256:` + previous `event_hash`, or the genesis value
  `sha256:` + 64 zeroes for the first event;
- `event_hash`: `sha256:` + SHA256 of
  `prev_hash || "\n" || canonical_json(event_without_event_hash)`.

`canonical_json` is the RFC 8785-style canonical form implemented by
`cbc_event.canonical`: sorted object keys, no insignificant whitespace,
UTF-8, and ECMAScript-compatible finite number formatting for the values the
protocol uses.

The reader verifies:

- sequence continuity;
- `prev_hash` equality;
- recalculated `event_hash`.

A mismatch is reported as a chain problem. The reader does not silently repair
or rewrite the log.

## v2 note (0.2.0rc1)

The hash algorithm above is unchanged for `cbc-event/v2`. v2 adds
`identity`, `event_type`, and `chain_id` to the canonical event body, so those
fields are covered by `event_hash`. A reader must negotiate the schema before
validating fields; an unsupported schema is a fail-closed version error, not an
unknown field. All v2 events in one log must share `chain_id`.
