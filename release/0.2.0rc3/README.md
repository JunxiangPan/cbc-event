# cbc-event 0.2.0rc3 — candidate

**Status: 0.2.0rc3 candidate. No stable 0.2.0, no PyPI upload.**

rc2 is the tagged pre-release. rc3 adds the optional semantic-verdict reader and
must not reuse or move the rc2 tag.

## Artifacts

| Artifact | SHA256 |
|---|---|
| `cbc_event-0.2.0rc3-py3-none-any.whl` | `63b75571fa5b5725fa3d6b950b8c5273c641c76cb9326d830d29dc4a7794bd87` |
| `cbc_event-0.2.0rc3.tar.gz` | `e6d608796569b8314f8423c6e69eb5da34c99ec6b9d618979fc43bd5f9b22a88` |

## Changes from rc2

- Optional, read-only `semantic-verdict/v1` reader:
  - verdict / confidence / findings / policy / evidence hash;
  - default text and `--json` view;
  - unknown schema and hash mismatch fail closed;
  - explicitly a semantic signal, not factual proof or gate PASS;
  - no CBF/CBP/CBE/CBM import.

## Verification

| Check | Result |
|---|---|
| semantic valid/hash/tamper/schema tests | pass |
| CBF adapter tests | pass |
| 178 tests, 1 local skip; protocol 92% / viewer 90% | pass |
| clean-env rc3 install + semantic/CBF CLI | pass |
| F05 full train | **NOT RUN / blocked** |
| PyPI | **not uploaded** |

## Boundaries

- No stable 0.2.0.
- F05 is not a full-train PASS.
- No CBF PASS; CBF is not released.
- rc1/rc2 tags are not moved.
