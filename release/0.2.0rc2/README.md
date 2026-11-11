# cbc-event 0.2.0rc2 — candidate

**Status: 0.2.0rc2 candidate. No rc2 tag yet, no stable 0.2.0, no PyPI upload.**

rc1 remains the tagged pre-release (`v0.2.0rc1`); rc2 is the CBF-adapter
candidate and requires review/approval before any tag.

## Artifacts

| Artifact | SHA256 |
|---|---|
| `cbc_event-0.2.0rc2-py3-none-any.whl` | `de7b45949e254085dd66d8335e782f99b88f643d339a6dc51d4aff20371517c1` |
| `cbc_event-0.2.0rc2.tar.gz` | `75b9a89859faba34f2ae1e4df21c867371982baac358100596e1f3ec4aeecddb` |

## Changes from rc1

- Optional `cbf-evidence/v1` adapter:
  - normalized `cbc-cbf-view/v1` view;
  - pure conversion to `cbc-event/v2`;
  - no CBF import and no runtime dependency;
  - documented CBF 0.1.0 `summary`-after-sealing hash status.
- 168 tests; protocol coverage 93%; viewer coverage 90%.

## Verification

| Check | Result |
|---|---|
| rc1 regression + v2 tests | pass |
| CBF real fixture read | pass (`verified_without_summary`) |
| CBF CLI view/event | pass |
| clean-env rc2 wheel install | pass |
| 0.1.0 compatibility | pass |
| F05 full train | **NOT RUN / blocked** |
| PyPI | **not uploaded** |

Evidence: `docs/standalone-install.md`, `docs/cbf-adapter.md`,
`docs/f05-train-evidence.md`.

## Boundaries

- Not a stable 0.2.0.
- F05 is not a full-train PASS.
- No external adoption claim.
- rc1 tag is not moved.
