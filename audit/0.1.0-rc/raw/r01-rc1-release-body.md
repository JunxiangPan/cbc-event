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

Assembled from CBC 11943f14 for the CBP external-manifest E2E.
Not an official GitHub Release body; upload status is NOT_UPLOADED.

<!-- CBC-EVIDENCE-BEGIN -->
<!-- cbc-evidence {"schema":"cbc-body-anchor/v1","root_hash":"sha256:95d104b5f99cabae5adc7dfd8dad6fda8be8a7a93faaf75fac8162901645688c","link_count":7,"asset_link_count":2,"verified_link_count":7,"appendix_sha256":"sha256:64673a3db61bbcf97f7f61f9c3821cbf3a4ceb17ddcc37c8108843d0733d240c"} -->
## CBC evidence chain

- gate_status: **NOT_UPLOADED**
- cbc_chain_status: **PASS** (file integrity only; this is NOT a release PASS)
- root_hash: `sha256:95d104b5f99cabae5adc7dfd8dad6fda8be8a7a93faaf75fac8162901645688c`
- link_count: 7
- asset_link_count: 2
- broken_link: none
- upload_status: **NOT_UPLOADED**
- upload_blocked_reason: `not_uploaded`
- declared_attached: true
- declared as attached but not uploaded
- skip_accounting: CBC is not counted in the CBE/CBP SKIP ratio
<!-- CBC-EVIDENCE-END -->
