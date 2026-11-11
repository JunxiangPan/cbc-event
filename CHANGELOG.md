# Changelog

## 0.2.0rc1 — unreleased candidate

- Added opt-in `cbc-event/v2`: strict `identity` (package_id / producer_id /
  package_version), `event_type`, `chain_id`, UUID `event_id`, and lowercase
  hashes. v1 is still the default emit format.
- Added fail-closed version negotiation; unknown schemas raise
  `UNSUPPORTED_EVENT_VERSION` (viewer exit 2) and are never read as v1.
- Viewer now dual-reads v1/v2 and reports `event-log/v1`, `event-log/v2`, or
  `event-log/mixed`; unknown fields are warnings, chain_id mismatch is exit 3.
- Added protocol spec, migration guide, compatibility matrix, and v2 schema.
- F05 full CBS v1.7 train remains unrun; no full-train PASS is claimed.

## Unreleased — cbc_viewer 0.1.0

- Added the read-only `cbc_viewer` package and `cbc-viewer` entry point:
  release/event-log hash-chain verification, body rendering, and a GET-only
  GitHub transport.
- Added `cbc-chain.schema.json` and `cbc-report.schema.json`; the first chain
  link is a manifest header binding version/tag/body-hash-scope/source commit.
  `link_count` includes the header/reports/controls/assets; `asset_link_count`
  counts only asset leaves.
- Added the `sealed-v1` body base/appendix rule and F6 NOT_UPLOADED rendering;
  broken chains include `cbc: NOT_UPLOADED`, `broken_link: #<index> <name> — <reason>`,
  and SKIPPED_INFRA materializes a dedicated `## Infrastructure failures` block.
- Distinguished CBP `MISSING_BODY_HASH_SCOPE` / `UNSUPPORTED_BODY_HASH_SCOPE`
  (exit 2, `FAIL`) from `expect_uploaded_unmet` (exit 2, `PRECONDITION_FAIL`).
- Accept the contract v1.7.1 RC2 `artifact_repository` object and reject a bare
  string; check `release_body_hash` against the §5.3 canonical body.
- Allow a pre-release remote tag (for example `v0.1.0-rc.1`) via `--tag` or
  `--remote-tag` while keeping the chain's release tag authoritative.
- Documented that F05 skips in standalone `cbc-event` CI but must execute in
  the CBS v1.7 release-train integration CI.
- `cbc_event` 0.1.0 protocol semantics are unchanged.

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
