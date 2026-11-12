# CBC 0.2.0rc1 — pre-release notes

**Status: pre-release. Not `0.2.0` stable. F05 is NOT RUN.**

## What is in this candidate

- `cbc-event/v2` opt-in protocol:
  - strict `identity` (`package_id`, `producer_id`, `package_version`);
  - `event_type`, `chain_id`, UUID `event_id`;
  - v1 remains the default emit format.
- Dual-read viewer:
  - v1, v2, and mixed event logs;
  - unknown schema fails closed (`UNSUPPORTED_EVENT_VERSION`);
  - unknown fields are warnings, not silent drops.
- Read-only: no release, signing, publish, or upload tooling.
- No CBE/CBP/CBM runtime import.

## Artifacts

| Artifact | SHA256 |
|---|---|
| `cbc_event-0.2.0rc1-py3-none-any.whl` | `ed74cb941819cd3cdb6dd4ae656f5ee9c4ba20f36b40679038543bdaf4d13d31` |
| `cbc_event-0.2.0rc1.tar.gz` | `17b140d0eee4d808ab776b665dc1ac7e6ecc64368f2b767b6e07546b4b34a001` |

## Verification

- 155 tests passed, 1 local skip.
- Protocol coverage 92%; viewer coverage 90%.
- Clean-environment wheel install and `cbc-viewer 0.2.0rc1` verified.
- Mixed v1/v2 event read verified (`event-log/mixed`).
- 0.1.0 regression suite green.

## Known boundaries

- **F05 full CBS v1.7 release train: NOT RUN.** No full-train PASS is claimed.
  The exact blocker and attempted commands are in `docs/f05-train-evidence.md`.
- No stable 0.2.0 release.
- No PyPI upload for 0.2.0rc1.
- CBF adapter is not part of rc1; it is planned for rc2/final.

## Migration

`0.1.x` remains supported. `0.2.0rc1` is opt-in. See
`docs/migration-0.2.md` and `docs/compatibility-matrix.md`.
