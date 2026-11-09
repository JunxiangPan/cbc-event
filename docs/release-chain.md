# CBC release hash chain and read-only viewer

Status: implementation note for `cbc_viewer 0.1.0` (CBC base). It consumes the
frozen v1.7 contract; it does not redefine F1–F6.

## Scope

Two independent verification scopes share the same evidence fields:

| scope | inputs | purpose |
|---|---|---|
| `release` | assets, CBE report, CBP quality manifest, `RELEASE_BODY.md` | release/upload evidence |
| `event-log` | `*.jsonl`, `head.json`, optional event manifest | CBC's native event-chain read |

A run verifies one scope. A release report is never merged with an event-log
report.

## Release chain (`cbc-chain/v1`, `sealed-v1`)

`cbc-chain.json` lists the expected evidence in a fixed order:

1. `manifest` header link (`kind=manifest`, binds package/version/tag/body hash scope/source commit)
2. `cbe-report.json` (`gate_report/cbe`)
3. `quality-manifest.json` (`gate_report/cbp`)
4. `RELEASE_ASSETS.sha256` (`control/assets_manifest`)
5. `WHEEL_SHA256` (`control/wheel_digest`)
6. every asset listed by `RELEASE_ASSETS.sha256`, sorted by UTF-8 name bytes

`RELEASE_BODY.md`, `cbc-chain.json`, `cbc-chain-report.json`, and
`CBC_BODY_BLOCK.md` are allowed in the directory but are **not** links.

```text
link_core = link without link_hash
link_hash = "sha256:" + sha256(prev_hash + "\n" + canonical_json(link_core))
root_hash = links[-1].link_hash
genesis   = "sha256:" + 64 * "0"
```

`canonical_json` is `cbc_event.canonical` (RFC 8785-style). No second
canonicalizer.

The verifier checks, in order:

- `index` continuity and `prev_hash` continuity;
- link hash recomputation;
- duplicate/unsafe names and symlinks;
- file presence, size, and raw-byte SHA-256;
- `root_hash`, `link_count`, and `asset_link_count`;
- no unlisted file in the release directory;
- cross-check: chain = `RELEASE_ASSETS.sha256` = CBP `artifact_hashes`, and
  `WHEEL_SHA256` = wheel in the chain.

Two counts are deliberately separate:

```text
link_count        = all links, including the manifest header, gate reports,
                    control files, and assets
asset_link_count  = only links with kind == "asset"
```

The body prints both. A consumer that needs the asset count (for example a
CBP `--artifact-type zip-bundle` check) must use `asset_link_count`, never
compare `link_count` to the number of assets.

## Body base/appendix rule

CBP's `release_body_hash` covers the **base body**, i.e. the bytes before:

```text
<!-- CBC-EVIDENCE-BEGIN -->
```

CBC appends the appendix after CBP has hashed the base body:

```text
<!-- CBC-EVIDENCE-BEGIN -->
<!-- cbc-evidence {"schema":"cbc-body-anchor/v1","root_hash":"sha256:...","link_count":7,"asset_link_count":2,"verified_link_count":7,"appendix_sha256":"sha256:..."} -->
## CBC evidence chain
...
<!-- CBC-EVIDENCE-END -->
```

Why: the root includes the CBP report; the CBP report includes the base body
hash. Hashing the appendix into the CBP body would create
`root ← CBP report ← body ← root`. The split is the only non-circular order.
`appendix_sha256` covers every appendix line except the anchor itself, so a
naive status-line edit is detectable. It is a self-check, not an external
signature: a deliberate rewrite that recomputes it is a fully consistent local
rewrite and falls under the trust boundary below. The base body stays
CBP-bound.

`body_hash_scope` must exist in the CBP manifest:

- `base` — accepted by `sealed-v1`;
- `full` — rejected with exit 2, `gate_status=FAIL`, error code
  `UNSUPPORTED_BODY_HASH_SCOPE`;
- missing — exit 2, `gate_status=FAIL`, error code
  `MISSING_BODY_HASH_SCOPE`. This is the CBP P0-06 dependency; CBC does not
  guess.

The `FAIL` here is distinct from `--expect-uploaded` being unconfirmed, which
is `exit 2` + `gate_status=PRECONDITION_FAIL` + error code
`expect_uploaded_unmet`. A malformed/missing CBP field is an input failure, not
a caller precondition.

### CBP 1.2.2 RC2 manifest shape

For contract v1.7.1 RC2, CBC requires:

- `schema_version` is the string `"1"`;
- `artifact_repository` is an object with exactly
  `repository`, `run_id`, and `artifact_name` (non-empty strings). A bare
  string is rejected as legacy/noncanonical, exit 2;
- `body_hash_scope` is exactly `base`;
- `release_body_hash` is checked against the §5.3 canonical body: UTF-8 with
  leading BOM dropped, CRLF and lone CR normalized to LF, trailing newlines
  stripped, and exactly one LF appended when non-empty.

## What `appendix_sha256` protects

- **Protects against accidental edits:** if the appendix is modified without
  recomputing the field, parsing fails with `body_anchor_mismatch`.
- **Does not protect against deliberate rewrite:** an attacker who rewrites the
  appendix and recomputes `appendix_sha256` produces a locally consistent body;
  the self-check cannot distinguish it.
- **Real tamper resistance comes from the remote anchor:** GitHub release body,
  asset `digest`, and tag→commit. Those are checked only in remote mode; local
  mode reports `anchor_scope=local` and cannot claim otherwise.

## Body fragments

`render-body --format cbs-not-uploaded-entry` emits the line for CBS's
`## NOT_UPLOADED` section:

```text
# clean, declared attached:
cbc: NOT_UPLOADED — declared as attached but not uploaded

# broken chain, declared attached:
cbc: NOT_UPLOADED — declared as attached but not uploaded; broken_link: #5 cbc-0.1.0-py3-none-any.whl — hash_mismatch

# not declared:
cbc: NOT_UPLOADED (not attached)
```

`render-body --format appendix` emits the full evidence block:

- PASS + UPLOADED: `## CBC evidence chain` + anchor + `upload_status: UPLOADED`;
- NOT_UPLOADED: `gate_status: NOT_UPLOADED`, `upload_status: NOT_UPLOADED`,
  and the exact phrase when declared;
- broken chain: `## CBC chain failure`, `broken_link: #<index> <name> — <reason>`,
  `upload_status: NOT_UPLOADED`, no `CBC PASS`;
- SKIPPED_INFRA: `## Infrastructure failures` with `SKIPPED_INFRA` and
  `upload_status: NOT_UPLOADED`.

## Evidence fields

Every report contains:

```json
{
  "cbc_chain_status": "PASS|FAIL|SKIPPED_INFRA",
  "root_hash": "sha256:...|null",
  "link_count": 7,
  "asset_link_count": 2,
  "broken_link": null,
  "upload_status": "UPLOADED|NOT_UPLOADED"
}
```

`cbc_chain_status` is file integrity only. `gate_status` is the component
status. `NOT_UPLOADED` never becomes `PASS`; `UPLOADED` is only written when a
read-only remote check confirms the release body and every chain asset
(`digest` or an explicit re-hash). A local file's presence is not upload proof.

## Exit codes

| situation | exit | gate_status |
|---|---:|---|
| clean + uploaded | 0 | `PASS` |
| clean + not uploaded | 0 | `NOT_UPLOADED` |
| missing/malformed top-level input | 2 | `FAIL` |
| CBP `body_hash_scope` missing/unsupported | 2 | `FAIL` (`MISSING_BODY_HASH_SCOPE` / `UNSUPPORTED_BODY_HASH_SCOPE`) |
| `--expect-uploaded` not confirmed | 2 | `PRECONDITION_FAIL` (`expect_uploaded_unmet`) |
| chain/body/remote evidence failure | 3 | `FAIL` |
| upstream `SKIPPED_INFRA` or CBC infra failure | 3 | `SKIPPED_INFRA` |
| blocking skip | 3 | `FAIL` |
| skip ratio > 0.20 | 4 | `FAIL` |

Precedence: input 2 > hard/infra 3 > skip 4 > expect-uploaded 2 > 0.

`--expect-uploaded` is a caller expectation, not a gate verdict. It is
deliberately `exit 2 + PRECONDITION_FAIL`, matching the contract's preflight
style; it is never `exit 3 + NOT_UPLOADED`.

## Tamper matrix

| injection | detected by | `broken_link.reason` |
|---|---|---|
| asset replaced (same name) | chain hash / `RELEASE_ASSETS.sha256` / CBP | `hash_mismatch` |
| extra asset | strict directory scan / remote asset set | `unexpected_asset` |
| manifest entry missing | declared file absent / checksum entry without file | `missing_asset`, `manifest_entry_missing` |
| body base rewritten | base hash vs CBP `release_body_hash` | `body_hash_mismatch` |
| body appendix rewritten | root/anchor or `appendix_sha256` | `body_anchor_mismatch` |
| chain manifest rewritten | link/root/count checks | `chain_*` |
| tag moved | remote tag commit vs `source_commit` (when supplied) | `tag_mismatch` |

## Identity policy

CBC binds `version` + `tag` only. It records `package_id` but does not require
it to equal `cbc`: CBE/CBP may currently write the producer id (`cbe`/`cbp`).
Tightening this waits for CBE/CBP target-package semantics.

```text
TODO(v1.8): when CBE/CBP reports define package_id = target package,
add package_id == "cbc" check with reason=REPORT_IDENTITY_MISMATCH.
```

## Upload boundary

CBC does not upload in this package. A separate uploader, if added later, may
run only when:

```text
cbe.gate_status == PASS and cbp.gate_status == PASS
and no blocking_skip and no SKIPPED_INFRA
and cbe/cbp skip_ratio <= 0.20
and cbc_chain_status == PASS
and body anchor OK
and version/tag consistent
```

It may only upload assets; no delete, no release-body edit, no tag creation or
force-update. A failed upload leaves evidence and requires a new version +
ERRATUM.

## Read-only viewer

`cbc-viewer` has `verify`, `show`, `render-body` only. The GitHub transport
exposes `get_release`, `get_tag_commit`, `get_asset_bytes`; its private request
method rejects anything except `GET`/`HEAD`. The package contains no
`subprocess`, `requests`, or `httpx`; source files are opened read-only; a
report may be written only outside the verified directory. `render-body` has no
`--report-out` and writes stdout only. The AST test suite asserts these
properties, including the `render-body` call path.

## F05 integration boundary

`F05` compares the CBC NOT_UPLOADED line against the real CBS
`release_body_v17.build()` implementation. It is skipped in the standalone
`cbc-event` CI because that repository does not contain the sibling
`public-release` checkout. That skip is an environment condition, **not a
waiver**: the CBS v1.7 release-train integration CI must run F05 with the CBS
checkout present. If the CBC job in that train also skips F05, integration
acceptance is incomplete.

## Trust boundary

Local-only verification detects single-file/subset tampering, missing/extra
files, and body edits. It cannot distinguish a fully consistent local rewrite
(all files, chain, root, body) from the original; only a remote anchor (release
body, asset digests, tag commit) can. Reports carry `anchor_scope=local|remote`.

## E2E matrix

- `CBC-E2E-R01..R19`: release chain happy path and tamper cases
- `CBC-E2E-S01..S18`: input, upstream, skip, and exit-code contract
- `CBC-E2E-F01..F11`: F6 NOT_UPLOADED and body rendering
- `CBC-E2E-V01..V09`: read-only/AST/report-path boundaries
- `CBC-E2E-D01..D05`: determinism and no-bypass
- `CBC-E2E-L01..L08`: event-log chain

Run them with `python -m unittest discover -s tests -v`.
