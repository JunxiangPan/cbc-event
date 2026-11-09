# CBC 0.1.0 candidate — hashes and provenance

**Status: candidate only; no tag and no release.**

## Source

| Item | Value |
|---|---|
| CBC source commit | `49f85b03377b63bf1b4ea2917282d7d71b14b120` |
| Contract | v1.7.1 RC2, file sha256 `209d75b4c900f9a2d1ad8f5c377ac1b8a868cf3e4cd449970e61e3ff380c18f1` |
| CBP manifest producer | CBP 1.2.2 official (`cbp manifest`) |
| CBP wheel | `2b73b4a4c387e4eb0700a339235249d62accfbe0a14c505188c53c484df7d046` |
| CBP sdist | `91974398ea0bc850633919e287f546d48b53f08d0ca57befce3a4a091de092d5` |
| CBP release manifest | `228594d07d7a9906280e7b5ff12fa0b1bf70b22ffff4b3d25983a4bcc072a2c6` |

The candidate artifacts were rebuilt from the current HEAD after the RC2
validator change; the older `48d9762` artifacts are superseded.

## CBC artifacts

| Item | SHA256 |
|---|---|
| `cbc_event-0.1.0-py3-none-any.whl` | `25d5730152a50ee064be1f380ce0ce1f96290924c221f7b268feafa719990f59` |
| `cbc_event-0.1.0.tar.gz` | `ed6e8b1a0d5e471ea51fa9534c6b93129ef9b857a534c212e56af43677fc0c59` |
| `quality-manifest.json` | `a64555beb323099ff3810f23f5f45f09276233aa72c83866c806ae0513491b4c` |

## Evidence binding

| Field | Value |
|---|---|
| `package_id` | `cbc` |
| `producer_id` | `cbp` |
| `version` | `v0.1.0` |
| `body_hash_scope` | `base` |
| `release_body_hash` | `f0734b62439ea5830e3b2f8ad683f43088f5bd6dda489318724eeab92e3939b1` |
| `artifact_repository` | `JunxiangPan/cbc-event` / `local-cbc-build-once` / `cbc-build-once` |
| CBE report | `721f529b6a9f7b7126a492808d2056d1ba1794d246640d96335ef434ebee0b1d` |
| CBP gate report | `213e824392879ce539c6664725d5cd919b7f1d471de8d91b9f75d2557279e78b` |
| chain root | `sha256:95d104b5f99cabae5adc7dfd8dad6fda8be8a7a93faaf75fac8162901645688c` |
| `link_count` / `asset_link_count` | `7` / `2` |

The CBE report and CBP gate report are the retained official v0.1.0
evidence; they were generated before the validator-only source change and were
not regenerated in this release preparation. The manifest binds those files and
the rebuilt CBC artifacts.

`artifact_repository.run_id` is **local**, not a GitHub run. The RC2 object
shape is valid (the contract requires a run/artifact coordinate; a local CI run
has no GitHub run id). A real build-once run should be used before the official
release if the release policy requires remote coordinate verification.

## Results

| Gate | Status |
|---|---|
| R02–R19 | 18/18 assertions passed |
| R16 | Windows SKIP; Linux CI covers |
| R01 local test index | PASS (not GitHub) |
| R01 real GitHub | **NOT RUN** |
| F05 train-like | OK |
| F05 full CBS v1.7 train | **NOT RUN** |

R01 and F05 are **not** full PASS in the release sense. See
`R01_DECISION.md` and `RELEASE_CHECKLIST.md`.
