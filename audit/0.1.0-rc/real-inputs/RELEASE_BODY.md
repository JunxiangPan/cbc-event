# cbc v0.1.0 — Release evidence

## Source excerpt (real CBC CHANGELOG)

Unreleased — cbc_viewer 0.1.0

- Added the read-only `cbc_viewer` package and `cbc-viewer` entry point:
  release/event-log hash-chain verification, body rendering, and a GET-only
  GitHub transport.
- Added `cbc-chain.schema.json` and `cbc-report.schema.json`; the first chain
  link is a manifest header binding version/tag/body-hash-scope/source commit.
  `link_count` includes the header/reports/controls/assets; `asset_link_count`
  counts only asset leaves.
- Added the `sealed-v1` body base/appendix rule and F6 NOT_UPLOADED rendering;
  broken chains include `cbc: NOT_UPLOADED`, `broken_link: #<index> <name> — <reason>`,
  and SKIPPED_INFRA materializes a dedicated `

## Honesty boundary

Assembled from the CBC repository at HEAD for the CBP R01-R19 feasibility run.
No official CBC release exists; the upload status is NOT_UPLOADED.

<!-- CBC-EVIDENCE-BEGIN -->
<!-- cbc-evidence {"schema":"cbc-body-anchor/v1","root_hash":"sha256:7351514c00461b205113d31f65972e4013bc6037dc4e179be872f6a5213e15df","link_count":7,"asset_link_count":0,"verified_link_count":7,"appendix_sha256":"sha256:fdfce1622b93b85fe5be8b653167511856697cd41839062cd0f2b65feb2516fd"} -->
## CBC evidence chain

- gate_status: **NOT_UPLOADED**
- cbc_chain_status: **PASS** (file integrity only; this is NOT a release PASS)
- root_hash: `sha256:7351514c00461b205113d31f65972e4013bc6037dc4e179be872f6a5213e15df`
- link_count: 7
- asset_link_count: 0
- broken_link: none
- upload_status: **NOT_UPLOADED**
- upload_blocked_reason: `not_uploaded`
- skip_accounting: CBC is not counted in the CBE/CBP SKIP ratio
<!-- CBC-EVIDENCE-END -->
