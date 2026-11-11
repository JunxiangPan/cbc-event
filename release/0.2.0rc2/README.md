# cbc-event 0.2.0rc2 — candidate

**Status: 0.2.0rc2 candidate. No rc2 tag yet, no stable 0.2.0, no PyPI upload.**

rc1 remains the tagged pre-release (`v0.2.0rc1`); rc2 is the CBF-adapter
candidate and requires review/approval before any tag.

## Artifacts

| Artifact | SHA256 |
|---|---|
| `cbc_event-0.2.0rc2-py3-none-any.whl` | `a96e26713014dafaae20b48c1f1890c0d7b7bbf11829fd2a5ebb9880286b3c0e` |
| `cbc_event-0.2.0rc2.tar.gz` | `cd674028272b374dfa44fa69b5806c206ace257d815c90bcf98c1d2ba9799129` |

## Changes from rc1

- Optional `cbf-evidence/v1` adapter:
  - normalized `cbc-cbf-view/v1` view;
  - pure conversion to `cbc-event/v2`;
  - no CBF import and no runtime dependency;
  - documented CBF 0.1.0 `summary`-after-sealing hash status.
- 169 tests; protocol coverage 93%; viewer coverage 90%.

## Verification

| Check | Result |
|---|---|
| rc1 regression + v2 tests | pass |
| CBF real fixture read | pass (`verified_without_summary`) |
| CBF CLI text/JSON view/event | pass |
| clean-env rc2 wheel install | pass |
| 0.1.0 compatibility | pass |
| F05 full train | **NOT RUN / blocked** |
| PyPI | **not uploaded** |

Evidence: `docs/standalone-install.md`, `docs/cbf-adapter.md`,
`docs/f05-train-evidence.md`.

## CBF status

CBF is **PENDING_CBF_0.1.0**. The adapter reads `cbf-evidence/v1`, but it is
**not** a CBF gate and creates no CBF PASS. Phase 0 is documented in
`docs/CBF_ADOPTION.md`.

## Boundaries

- Not a stable 0.2.0.
- F05 is not a full-train PASS.
- No external adoption claim.
- rc1 tag is not moved.
