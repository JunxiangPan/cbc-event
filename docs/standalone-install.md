# Standalone install / CLI check

Candidate: `cbc-event` / `cbc_viewer` **0.2.0rc2**. Not uploaded to PyPI.

## Artifacts built locally

| Artifact | SHA256 |
|---|---|
| `cbc_event-0.2.0rc2-py3-none-any.whl` | `a96e26713014dafaae20b48c1f1890c0d7b7bbf11829fd2a5ebb9880286b3c0e` |
| `cbc_event-0.2.0rc2.tar.gz` | `cd674028272b374dfa44fa69b5806c206ace257d815c90bcf98c1d2ba9799129` |

The wheel is one distribution containing `cbc_event` and `cbc_viewer`; the
viewer has no third-party runtime dependency and does not import CBE/CBP/CBM.

## Clean environment

```text
$ python -m venv /tmp/cbc-020rc2-venv
$ /tmp/cbc-020rc2-venv/bin/pip install --no-deps cbc_event-0.2.0rc2-py3-none-any.whl
Successfully installed cbc-event-0.2.0rc2
$ python -c "import cbc_event,cbc_viewer; print(cbc_event.__version__, cbc_viewer.__version__)"
0.2.0rc2 0.2.0rc2
$ cbc-viewer --version
cbc-viewer 0.2.0rc2
$ python -c "import importlib.util; print({m: bool(importlib.util.find_spec(m)) for m in ('cbe','cbp','cbm','cbs')})"
{'cbe': False, 'cbp': False, 'cbm': False, 'cbs': False}
```

The dependency check was run from a directory outside the workspace so sibling
repositories could not be imported as namespace packages.

## Dual-read CLI check

Generated one v1 event and one v2 event, then ran the installed viewer:

```text
$ cbc-viewer verify --scope event-log --event-dir /tmp/cbc-events --json
{
  "exit_code": 0,
  "gate_status": "PASS",
  "cbc_chain_status": "PASS",
  "chain_profile": "event-log/mixed",
  "inputs": {
    "event_versions": ["cbc-event/v1", "cbc-event/v2"],
    "event_chain_ids": ["cbc-clean"]
  }
}
```

## CBF adapter check

```text
$ cbc-viewer cbf-evidence --evidence cbf.json
CBF evidence: PASS
policy_sha256: ...
findings: 0
$ cbc-viewer cbf-evidence --evidence cbf.json --json
cbc-cbf-view/v1 PASS verified_without_summary
$ cbc-viewer cbf-evidence --evidence cbf.json --event --chain-id cbc-main --seq 1
cbc-event/v2 gate INFO cbc-main
```

This uses `cbf-evidence/v1` as JSON only; CBF is not imported.

## Install forms

| Goal | Command |
|---|---|
| protocol client only | `pip install cbc-event==0.2.0rc2` |
| protocol + viewer CLI | same wheel; `cbc-viewer` entry point is included |
| no CBE/CBP needed | confirmed by the clean environment above |

The `viewer` extra remains empty on purpose: there is no third-party viewer
runtime dependency.
