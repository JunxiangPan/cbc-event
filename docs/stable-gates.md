# Stable 0.2.0 gates

`0.2.0rc1` and `0.2.0rc2` are release candidates. Nothing below is a stable
release until **all** gates pass.

| Gate | Current status |
|---|---|
| 0.1.0 regression suite | PASS |
| 0.2.0rc1 install + dual-read | PASS |
| 0.2.0rc2 CBF adapter | PASS (candidate; review pending) |
| F05 real CBS v1.7 full train | **NOT RUN** |
| Stable tag `v0.2.0` | **NOT CREATED** |
| PyPI stable 0.2.0 | **NOT UPLOADED** |

## Required before stable

1. 0.1.x regression suite green on the release commit.
2. rc candidate installs in a clean environment and reads v1/v2/mixed event logs.
3. CBF adapter reads a real `cbf-evidence/v1` document without importing CBF.
4. CBF Phase 1/2 gate runs and yields a real `cbf-evidence/v1` PASS.
5. F05 runs on the real CBS v1.7 release train with real CBE/CBP/CBC/CBM
   products; record run URL, inputs, and outputs. Mock or train-like output does
   not count.
6. Human approval for the stable release.

## Explicitly not enough

- local test-index R01;
- train-like F05;
- mock CBE/CBP workflows;
- external adoption statements without evidence.

## Current blockers

- CBF is not released; CBF gate is PENDING, not PASS.

- F05 full train is blocked by the absence of an executable CBS v1.7
  release-train workflow in this environment (see
  `docs/f05-train-evidence.md`).
- rc2 has not been tagged or approved.
