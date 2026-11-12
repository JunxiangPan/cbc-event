# F05 — real CBS release-train evidence

**Status: NOT RUN — full train blocked. No full-train PASS is claimed.**

F05 is the full CBS v1.7 release-train integration case, not the standalone
body-generator test. This document records the commands attempted on
2026-11-12 and why the full train could not be executed in this workspace.

## 1. Local train runner

```text
$ command -v act
act-not-found
$ command -v docker
docker-not-found
```

There is no local GitHub Actions runner, so the reusable train workflow cannot
be executed locally.

## 2. CBS workflow inventory

Repository: `JunxiangPan/Cyber-Butler-Security` (the local `public-release`
checkout). The reusable train file exists in the working tree but is not on the
default branch's active workflow list:

```text
$ gh workflow list -R JunxiangPan/Cyber-Butler-Security
build-unsigned, cbp-action-verify, release-finalize, release-repack,
release-signfix, security-tests, sign-artifact, vm-ops, vm-proof,
vm-proof-collect, vm-proof, Dependency Graph
```

`gh run list` shows `security-tests` runs on `v1.7.0-integration`, not a
`reusable-v17-release` train run. Attempting to fetch the workflow by name
returned:

```text
HTTP 404: workflow reusable-v17-release.yml not found on the default branch
```

## 3. Workflow defaults are mock

`public-release/.github/workflows/reusable-v17-release.yml` defaults to mock
producers, not real CBE/CBP:

```text
mock_mode: {type: string, default: "pass"}
CBE_CLI: ${{ vars.CBE_CLI || 'python tests/v17/mock/cbe_cli.py' }}
CBP_CLI: ${{ vars.CBP_CLI || 'python tests/v17/mock/cbp_cli.py' }}
```

Running it without the real repository variables would be a mock train, not
F05. This run did not trigger any external workflow (that would write to
another repository and is outside this task's boundary).

## 4. Real products available, but no train

Real CBE/CBP/CBC/CBM 0.1.x products exist locally (CBE report, CBP quality
manifest, CBC 0.1.0 wheel, CBM 0.1.0 report). They are not a 0.2.0rc1 CBS
train and feeding them into the F05 body generator would not be a full-train
PASS. They are therefore not used to claim F05.

## 5. What is proven instead

- The standalone F05 body-generator test runs in `tests/e2e/test_f6.py` when a
  real CBS checkout is present (`train-like`).
- That test is auxiliary: it uses the real CBS body generator but a
  synthetic/minimal report. It is **not** the full train.

## 6. Remaining blocker

To close F05, a human/environment with the CBS v1.7 release-train workflow must
run it with real `CBE_CLI`/`CBP_CLI` variables and real CBE/CBP/CBC/CBM products,
then attach the workflow run URL, inputs, and outputs here. Until then:

- F05 = **NOT RUN**;
- no F05 full PASS;
- CBC 0.2.0rc1 remains a release candidate, not a stable release.

## Reproduction of the blocker

```bash
command -v act || echo act-not-found
command -v docker || echo docker-not-found
gh workflow list -R JunxiangPan/Cyber-Butler-Security
gh run list -R JunxiangPan/Cyber-Butler-Security --limit 5
sed -n '1,100p' public-release/.github/workflows/reusable-v17-release.yml
```
