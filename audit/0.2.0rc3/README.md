# CBC 0.2.0rc3 — reader evidence

This directory records the optional CBF and semantic readers. It does **not**
claim a CBF gate PASS for CBC, F05 PASS, or stable 0.2.0.

## Real CBF 0.1.0rc1 evidence read — PASS

Source: CBF repository `.cbf/evidence/20261112T055207Z-git-PASS.json` from CBF
0.1.0rc1 (tag `v0.1.0rc1`, commit `b9baf3f`; release
https://github.com/JunxiangPan/cbf/releases/tag/v0.1.0rc1).

| Field | Value |
|---|---|
| CBF evidence schema | `cbf-evidence/v1` |
| CBF tool/version | `cbf` / `0.1.0rc1` |
| policy version | `0.1.1` |
| CBF project | `cbf` (not CBC) |
| surface | `git` |
| result | **PASS** |
| evidence_sha256 | `08567f171362f4fa8cb42855f0caab842738975ae2104078912374f1a3fabd7c` |
| raw file sha256 | `b476390e432682f78dfd5840e83a29c01eca17dad2f9bdf88112171d35cb85d7` |
| CBC hash status | `verified` |

Files:

- `cbf-evidence-v1.json` — raw real evidence (0 findings; safe)
- `cbf-read.stdout` — human-readable CBC viewer output
- `cbf-read.stderr` — empty
- `cbf-view.json` — normalized `cbc-cbf-view/v1`
- `reader-tests.stdout` — 22 reader tests (CBF + semantic), all pass

Boundary: this is **interoperability evidence**. It proves CBC can read a real
CBF 0.1.0rc1 evidence document. It is not a CBF gate PASS for CBC, because CBC
has not run CBF gate and CBF is not a CBC runtime dependency.

## Semantic verdict reader — PASS (unit/CLI)

- `semantic-verdict/v1` valid document read;
- verdict / confidence / findings / policy / evidence hash displayed;
- unknown schema fail-closed;
- hash mismatch fail-closed;
- no CBF/CBP/CBE/CBM import;
- clean-env CLI text and `--json` verified.

No external semantic verdict was supplied; this is reader/interop verification,
not a claim that any semantic model ran or that a verdict is factual.

## Gate / F05 status

| Item | Status |
|---|---|
| CBC CBF gate | **NOT RUN** |
| CBF PASS for CBC | **NONE** |
| F05 full CBS v1.7 train | **NOT RUN** |
| stable 0.2.0 | **NOT RELEASED** |
| PyPI 0.2.0rc3 | **not uploaded** |

The rc3 pre-release is tagged `v0.2.0rc3`; tags `v0.1.0`, `v0.2.0rc1`, and
`v0.2.0rc2` are not moved.
