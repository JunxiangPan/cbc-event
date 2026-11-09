# CBC 0.1.0 — final closeout

**Status: RELEASED and CLOSED for code.**
**Code frozen at `5cdc9a1`; no code changes after the release.**
**No PyPI upload.**

## Official release

| Item | Value |
|---|---|
| tag | `v0.1.0` |
| tag target | `5cdc9a1b0d9a06f7bb6d5ad87f5a736fa24c8439` |
| release URL | https://github.com/JunxiangPan/cbc-event/releases/tag/v0.1.0 |
| release type | official (not pre-release, not draft, Latest) |
| wheel | `d77648af4f7bf6c1d67e57ee5d07a5d6a116b92aecdf89df289b7b73189d3f33` |
| sdist | `024c54b6e417d428910c74bfb4e46fa6237b01ae7f95c58c1df7779f24307e17` |
| body | `b4960fa648101e231c54604665b866e94ee1424953911828322c6c9ec5a289f5` |
| CBP 1.2.2 manifest | `e16823ce2c3b5ccbede74358742948b310b706c8a05d123420ea2aab89858d50` |
| chain root | `sha256:bfc29f6676171615bb15be34968b6c01f4324128d00984ac89c973519ab60e87` |
| `link_count` / `asset_link_count` | `7` / `2` |

The official assets are byte-for-byte the `v0.1.0-rc.2` assets; no rebuild or
rehash was performed.

## Pre-releases retained (not moved)

| Tag | Target | Assets | Status |
|---|---|---|---|
| `v0.1.0-rc.1` | `49f85b0` | wheel `25d573…`, sdist `ed6e8b1a…` | pre-release, retained |
| `v0.1.0-rc.2` | `5cdc9a1` | wheel `d77648af…`, sdist `024c54b6…` | pre-release, retained |

`v0.1.0-rc.1` records the first R01 input-validation failure and the later
viewer fix; `v0.1.0-rc.2` is the source of the official bytes. Neither was
deleted, retagged, or moved.

## R01 evidence

Post-release official R01:

```text
exit_code = 0
gate_status = PASS
upload_status = UPLOADED
cbc_chain_status = PASS
root_hash = sha256:bfc29f66…b60e87
```

Evidence:

- `raw/r01-official.stdout`
- `raw/r01-official-release.json`
- rc.2 pre-release evidence: `raw/r01-rc2.stdout`
- rc.1 failure/fix history: `raw/r01-rc1-input-failure.stdout`,
  `raw/r01-rc1-after-fix.stdout`

The local test-index result (`local_r01_result.json`) remains local-only and is
never a GitHub R01 PASS.

## Gate status

| Gate | Status |
|---|---|
| R02–R19 | 18/18 assertions passed |
| R16 | Windows SKIP; Linux CI covers |
| R01 official | PASS |
| F05 train-like | OK |
| F05 full CBS v1.7 train | **NOT RUN / pending** |
| PyPI | **not uploaded** |

F05 remains the only open integration boundary. The train-like check used real
CBS source, but the full CBS v1.7 release train has not run; do not write
"F05 full PASS".

## Repository state

- code commit: `5cdc9a1`
- final docs before this closeout: `21860bb`
- CI: ubuntu + windows green; no tag/release moves during closeout
- no CBS/CBE/CBP/CBM changes
- `release/0.1.0/` holds RELEASE_NOTES, HASHES, R01_DECISION, RELEASE_CHECKLIST,
  APPROVAL, TAG_NOTE, manifest, body, and checksums

## Closeout rule

No further code changes. Reopen only for a new version/ERRATUM under the
contract; do not move `v0.1.0`, `v0.1.0-rc.1`, or `v0.1.0-rc.2`, and do not
upload to PyPI without a separate approved decision.
