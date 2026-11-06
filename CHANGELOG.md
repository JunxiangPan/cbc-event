# Changelog

## 0.1.0 — 2026-11-06

- Initial `cbc-event/v1` schema.
- RFC 8785-style canonical serialization for event hashing.
- Append-only JSONL store with `prev_hash` / `event_hash` / `seq`.
- Zero-dependency client; disabled by default.
- Unknown-field tolerance with WARN.
- Chain-gap detection.
