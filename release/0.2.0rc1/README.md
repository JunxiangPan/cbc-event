# cbc-event 0.2.0rc1 — release candidate

**Status: 0.2.0rc1 candidate. No tag, no stable 0.2.0, no PyPI upload.**

Branch: `0.2.0-dev`. Source code commit: `6377d22` (docs may be later).

## Artifacts

| Artifact | SHA256 |
|---|---|
| `cbc_event-0.2.0rc1-py3-none-any.whl` | `ed74cb941819cd3cdb6dd4ae656f5ee9c4ba20f36b40679038543bdaf4d13d31` |
| `cbc_event-0.2.0rc1.tar.gz` | `17b140d0eee4d808ab776b665dc1ac7e6ecc64368f2b767b6e07546b4b34a001` |

The artifacts were built locally; they are not published.

## Scope

- opt-in `cbc-event/v2`: strict identity, event_type, chain_id;
- v1 remains the default emit format and remains readable;
- viewer dual-reads v1/v2, unknown version fail-closed;
- read-only only: no release, signing, publish, or upload tooling;
- no CBE/CBP/CBM runtime imports.

## Verification

| Check | Result |
|---|---|
| unit/e2e tests | 155 passed, 1 skipped (local) |
| protocol coverage | 92% |
| viewer coverage | 90% |
| clean-env wheel install | pass |
| clean-env `cbc-viewer` | 0.2.0rc1, pass |
| mixed v1/v2 event read | pass, `event-log/mixed` |
| 0.1.0 regression | existing suite green |
| F05 full CBS train | **NOT RUN / blocked** |
| PyPI | **not uploaded** |

Clean-env details: `docs/standalone-install.md`.
F05 evidence and blocker: `docs/f05-train-evidence.md`.
Spec: `docs/event-protocol-v2.md`; migration: `docs/migration-0.2.md`;
matrix: `docs/compatibility-matrix.md`.

## Status boundaries

- No stable 0.2.0 is declared.
- F05 is not a full-train PASS.
- No external adoption claim.
- v1 is not removed.
