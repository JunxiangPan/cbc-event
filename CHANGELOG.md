# Changelog

## 0.1.0 — 2026-11-06

**`cbc-event 0.1.0` is the first formal protocol version of the CB ecosystem.**
Within `0.1.x` only optional fields may be appended. Existing required fields
must not be deleted, renamed, reordered, or have their type or meaning changed.
Once CBS 1.6.4 and CBP 0.1.0 begin consuming the protocol, the `0.1.0` schema and
canonicalization rules are frozen. Any breaking change must become `0.2.0` and
ship with a migration note.

- Initial `cbc-event/v1` schema.
- RFC 8785-style canonical serialization for event hashing.
- Append-only JSONL store with `prev_hash` / `event_hash` / `seq`.
- Zero-dependency client; disabled by default.
- Unknown-field tolerance with WARN.
- Chain-gap detection.
