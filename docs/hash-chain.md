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
