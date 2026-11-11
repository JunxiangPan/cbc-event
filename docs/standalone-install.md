# Standalone install / CLI check

Candidate: `cbc-event` / `cbc_viewer` **0.2.0rc1**. Not uploaded to PyPI.

## Artifacts built locally

| Artifact | SHA256 |
|---|---|
| `cbc_event-0.2.0rc1-py3-none-any.whl` | `ed74cb941819cd3cdb6dd4ae656f5ee9c4ba20f36b40679038543bdaf4d13d31` |
| `cbc_event-0.2.0rc1.tar.gz` | `17b140d0eee4d808ab776b665dc1ac7e6ecc64368f2b767b6e07546b4b34a001` |

The wheel is one distribution containing `cbc_event` and `cbc_viewer`; the
viewer has no third-party runtime dependency and does not import CBE/CBP/CBM.

## Clean environment

```text
$ python -m venv /tmp/cbc-020rc1-venv
$ /tmp/cbc-020rc1-venv/bin/pip install --no-deps cbc_event-0.2.0rc1-py3-none-any.whl
Successfully installed cbc-event-0.2.0rc1
$ python -c "import cbc_event,cbc_viewer; print(cbc_event.__version__, cbc_viewer.__version__)"
0.2.0rc1 0.2.0rc1
$ cbc-viewer --version
cbc-viewer 0.2.0rc1
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

## Install forms

| Goal | Command |
|---|---|
| protocol client only | `pip install cbc-event==0.2.0rc1` |
| protocol + viewer CLI | same wheel; `cbc-viewer` entry point is included |
| no CBE/CBP needed | confirmed by the clean environment above |

The `viewer` extra remains empty on purpose: there is no third-party viewer
runtime dependency.
