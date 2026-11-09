# CBP manifest gap — historical, resolved by CBP 1.2.0 official

Status: **RESOLVED** by the `cbp manifest` command in the official CBP 1.2.0
release. This document is kept as the record of the earlier blocker.

CBC's `validate_cbp()` requires the contract §5 quality manifest, including
`artifact_hashes`, `release_body_hash`, `evidence_sha256`, gate counts, and
`body_hash_scope`. The earlier `5da8b87` RC used for the first audit attempt exposed no
command that generated that document for an arbitrary external package.

## Evidence 1 — `--report-json` is a gate report, not a manifest

The RC CLI writes this shape in its `--report-json` branch:

```text
schema_version, package_id, producer_id, version, gate_status, exit_code,
applicable_gate_count, skip_count, skip_ratio, blocking_skip,
body_hash_scope, package_type, gates
```

It does **not** write `artifact_hashes`, `release_body_hash`, or
`evidence_sha256`. The real CBC run produced exactly that shape
(`raw/cbc-gate-report.json`).

## Evidence 2 — `--v12-report` is a rule report, not a manifest

The RC v12 report schema is `cbp-v12-rule-report/v1` with `rules`, `summary`,
and `expired_entries`. It has no manifest fields at all
(`raw/cbc-v12-report.json`).

## Evidence 3 — the RC dogfood manifest generator is CBP-self only

In that earlier RC, the only full-manifest generator was hardcoded to CBP:

```python
# CBP report schema constants
PACKAGE_ID = "cbp"
PRODUCER_ID = "cbp"

# CBP dogfood manifest builder
"package_id": report_schema.PACKAGE_ID,
"producer_id": report_schema.PRODUCER_ID,
applicable = len(report_schema.ALL_GATES)
```

It also:

- loads the RC package config and CBP's coverage/release configuration;
- runs CBP's nine gates (coverage, dependency, comments, docs, binary, encoding,
  custom, upgrade, claims), not CBC's release evidence;
- builds CBP's own release body via the RC release-body generator;
- requires CBP's release wheel/notes/claims layout.

Running it against CBC would produce a manifest labelled `package_id: "cbp"`
with CBP's gate set, and would require reconstructing CBP's release layout. That
would not be a CBP-generated **CBC** manifest.

## Evidence 4 — RC artifact contains no manifest

The `cbp-rc` artifact from the earlier run `42539271566` contained only:

```text
cbp_action-1.2.0-py3-none-any.whl
cbp_action-1.2.0.tar.gz
RC_ASSETS.sha256
```

No `quality-manifest.json`, no CBC-specific manifest.

## Historical consequence (before the official release)

The earlier RC only had:

1. CBP adds a generic target-package manifest command/artifact (for example
   `--package-manifest-out` with target `package_id`, artifact hashes, and base
   body hash); or
2. the release owner explicitly approves a CBC-side audit adapter that combines
   CBP's real gate report with real CBC artifact/body hashes, and labels the
   provenance as an adapter, not as a CBP-emitted manifest.

That blocker is now resolved by the official CBP 1.2.0 release; the
executable R02–R19 run uses official manifest `32462de2…` (see `R01_R19.md`).
