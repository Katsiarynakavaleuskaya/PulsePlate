<!-- markdownlint-disable MD013 MD031 MD032 -->

# Frontend npm Browserslist and qs finite security batch

## Authority and bounded claim

The historical Browserslist filename is retained to preserve the existing PR
and review carrier. This file is the sole transition-evidence owner for the
operator-authorized exact finite batch:

```text
B = {npm:browserslist, npm:qs}
P_batch = P_browserslist AND P_qs
```

The operator directly confirmed this exact two-identity expansion on 3 September
2026 after a terminal full-repository npm scanner snapshot derived the same
all-and-only set. That confirmation grants no third identity, future batch,
suppression, override, direct pin, alert dismissal, force push, provider claim,
or merge authority. Canonical admission policy is the
`dependency-remediation-admission:v2` block at `AGENTS.md:2324`.

For each `D` in `B`, this owner records an independent `S_base`, `S_head`,
`F_cutoff`, non-empty `A`, authored `I_R`, replay-proven `C_R`, and universal
`P`. The permanent data-driven guard is
`tests/test_frontend_dependency_guards.py:1623`.

## Exact base, material head, and governed surfaces

The exact authorized base and merge-base are:

```text
863d16ea2328dd32fa6fec6cef4d8f117b6edf85
```

The dependency/guard and false-green test material head preceding this final
batch-evidence refresh is:

```text
6897a711cb8d92864ec0cfd7a1c9d68e7dff1a21
```

This material head contains the ancestry-preserving base sync plus the refreshed
npm-generated resolver closure. Generated detect-secrets line-number refreshes
remain isolated in their dedicated hook commits. The tracked surface enumerator at
`tests/test_frontend_dependency_guards.py:1108` discovers exactly five
base/head npm surfaces:

| Surface | Base SHA-256 | Candidate SHA-256 | Reconciliation |
| --- | --- | --- | --- |
| `package.json` | `9bcbc2307471c1eb4be4c87cffeb88587339e911e6a4898d5c9234fff7b0766c` | same | executable absence; unchanged |
| `package-lock.json` | `a1c5411b103a80fc78b293c628d0fd8d6f47de065d2c75a208d06e40c683d9e8` | same | executable absence; unchanged |
| `frontend/package.json` | `234beaabd47ec019090e28a26cc4e56fdda4b745d5d75c89c12ec958a03eed5d` | same | no direct batch owner; unchanged |
| `frontend/package-lock.json` | `3584251c809e21a7d2606cbce3d904c8b90e591bb87818d744c5262ce017daae` | `4b6649721614c6a937d3d1dd445301d1e905700df814a63ea5d6e8fa28bfb615` | two `I_R` plus Browserslist `C_R` |
| `scripts/business_collateral/package.json` | `8005a3491db7d92f36ac66369861589f9c47123d3a7c71e643fc2c06168cd45a` | same | executable absence; unchanged |

Base occurrences are `browserslist@4.28.2` and `qs@6.15.2`, both in
`frontend/package-lock.json`. Candidate occurrences are `browserslist@4.28.8`
at `frontend/package-lock.json:4743` and `qs@6.16.0` at
`frontend/package-lock.json:8938`. All manifest and root npm bytes are
unchanged from the exact base.

## Terminal scanner snapshot and complete GAD receipt

At `2026-09-03T03:39:19Z`, authenticated GAD pagination returned 3 Browserslist
records / 3 range rows and 10 qs records / 21 range rows. The terminal
full-repository npm audit snapshot returned a clean root lock and exactly two
vulnerable frontend identities. Its canonical SHA-256 is:

```text
c3aec6d46c57b693d2a9860838921fd51a16644dd76f32507a2aa3d8852419d4
```

That immutable scanner receipt retains its original audited base
`2bfb7ff96dfcc98a806de9c113eff5242bfbe479`. The synchronized base
`863d16ea2328dd32fa6fec6cef4d8f117b6edf85` has byte-identical contents for
all five governed npm surfaces, including the vulnerable base lock SHA-256
`3584251c809e21a7d2606cbce3d904c8b90e591bb87818d744c5262ce017daae`.
At `2026-09-04T10:44:52Z`, authenticated GAD and Dependabot pagination again
returned the exact `3/3` Browserslist, `10/21` qs, and sole open alert `#273`
projections. A fresh root-lock audit exited `0` with zero findings. Two bounded
fresh frontend base-audit attempts timed out at 120 and 180 seconds, so no new
frontend base-audit timestamp or PASS is claimed; base applicability remains
bound by the byte-identical retained receipt plus the fresh unchanged GAD
ranges.

Canonical batch receipt SHA-256:

```text
ad87c0e16f1cf4cc3ab847175fc3d5d6865b941b9b7540816b4dec0711367d8f
```

The receipt below is the complete normalized retained payload.
The retained normalized batch receipt is:

```json
{
  "authorized_dependency_identities": [
    "npm:browserslist",
    "npm:qs"
  ],
  "gad_cutoff": "2026-09-03T03:39:19Z",
  "operator_authorization": "exact_finite_batch_confirmed_2026-09-03",
  "scanner_snapshot": {
    "base_sha": "2bfb7ff96dfcc98a806de9c113eff5242bfbe479",
    "observed_at": "2026-09-03T03:39:19Z",
    "roots": [
      {
        "command": "npm audit --package-lock-only --json",
        "exit_code": 0,
        "lock": "package-lock.json",
        "project": ".",
        "severity_counts": {
          "critical": 0,
          "high": 0,
          "info": 0,
          "low": 0,
          "moderate": 0,
          "total": 0
        },
        "vulnerability_keys": []
      },
      {
        "command": "npm audit --package-lock-only --json",
        "exit_code": 1,
        "lock": "frontend/package-lock.json",
        "project": "frontend",
        "severity_counts": {
          "critical": 0,
          "high": 1,
          "info": 0,
          "low": 0,
          "moderate": 1,
          "total": 2
        },
        "vulnerability_keys": [
          "browserslist",
          "qs"
        ]
      }
    ],
    "terminal": true,
    "vulnerable_dependency_identities": [
      "npm:browserslist",
      "npm:qs"
    ]
  },
  "scanner_snapshot_sha256": "c3aec6d46c57b693d2a9860838921fd51a16644dd76f32507a2aa3d8852419d4",
  "schema": "pulseplate.frontend-npm-security-batch-gad-receipt/v1",
  "targets": {
    "browserslist": {
      "cutoff": "2026-09-03T03:39:19Z",
      "next_page": null,
      "observed_at": "2026-09-03T03:39:19Z",
      "page_count": 1,
      "query": "GET /advisories?ecosystem=npm&affects=browserslist&per_page=100",
      "range_count": 3,
      "record_count": 3,
      "records": [
        {
          "cve_id": "CVE-2026-73088",
          "ghsa_id": "GHSA-73wf-gq98-2v4g",
          "published_at": "2026-09-01T16:41:54Z",
          "severity": "high",
          "updated_at": "2026-09-01T16:41:55Z",
          "vulnerabilities": [
            {
              "ecosystem": "npm",
              "first_patched_version": "4.28.7",
              "package": "browserslist",
              "vulnerable_version_range": "<=4.28.6"
            }
          ],
          "withdrawn_at": null
        },
        {
          "cve_id": "CVE-2026-73089",
          "ghsa_id": "GHSA-c83g-rgw3-j3cx",
          "published_at": "2026-09-01T16:42:13Z",
          "severity": "high",
          "updated_at": "2026-09-01T16:42:15Z",
          "vulnerabilities": [
            {
              "ecosystem": "npm",
              "first_patched_version": "4.28.7",
              "package": "browserslist",
              "vulnerable_version_range": "<=4.28.6"
            }
          ],
          "withdrawn_at": null
        },
        {
          "cve_id": "CVE-2021-23364",
          "ghsa_id": "GHSA-w8qv-6jwh-64r5",
          "published_at": "2021-05-24T19:52:40Z",
          "severity": "medium",
          "updated_at": "2023-08-17T05:02:30Z",
          "vulnerabilities": [
            {
              "ecosystem": "npm",
              "first_patched_version": "4.16.5",
              "package": "browserslist",
              "vulnerable_version_range": ">=4.0.0,<4.16.5"
            }
          ],
          "withdrawn_at": null
        }
      ]
    },
    "qs": {
      "cutoff": "2026-09-03T03:39:19Z",
      "next_page": null,
      "observed_at": "2026-09-03T03:39:19Z",
      "page_count": 1,
      "query": "GET /advisories?ecosystem=npm&affects=qs&per_page=100",
      "range_count": 21,
      "record_count": 10,
      "records": [
        {
          "cve_id": "CVE-2026-82417",
          "ghsa_id": "GHSA-4mjr-xmp4-gh2g",
          "published_at": "2026-09-02T14:45:13Z",
          "severity": "medium",
          "updated_at": "2026-09-02T14:45:15Z",
          "vulnerabilities": [
            {
              "ecosystem": "npm",
              "first_patched_version": "6.16.0",
              "package": "qs",
              "vulnerable_version_range": ">=2.2.5,<6.16.0"
            }
          ],
          "withdrawn_at": null
        },
        {
          "cve_id": "CVE-2025-15284",
          "ghsa_id": "GHSA-6rw7-vpxm-498p",
          "published_at": "2025-12-30T21:02:54Z",
          "severity": "medium",
          "updated_at": "2026-03-02T22:05:33Z",
          "vulnerabilities": [
            {
              "ecosystem": "npm",
              "first_patched_version": "6.14.1",
              "package": "qs",
              "vulnerable_version_range": "<6.14.1"
            }
          ],
          "withdrawn_at": null
        },
        {
          "cve_id": null,
          "ghsa_id": "GHSA-crvj-3gj9-gm2p",
          "published_at": "2018-10-09T00:44:29Z",
          "severity": "high",
          "updated_at": "2023-01-09T05:02:51Z",
          "vulnerabilities": [
            {
              "ecosystem": "npm",
              "first_patched_version": "1.0.0",
              "package": "qs",
              "vulnerable_version_range": "<1.0.0"
            }
          ],
          "withdrawn_at": "2020-06-16T21:32:53Z"
        },
        {
          "cve_id": "CVE-2014-10064",
          "ghsa_id": "GHSA-f9cm-p3w6-xvr3",
          "published_at": "2018-10-09T00:38:48Z",
          "severity": "high",
          "updated_at": "2023-01-09T05:02:52Z",
          "vulnerabilities": [
            {
              "ecosystem": "npm",
              "first_patched_version": "1.0.0",
              "package": "qs",
              "vulnerable_version_range": "<1.0.0"
            }
          ],
          "withdrawn_at": null
        },
        {
          "cve_id": "CVE-2017-1000048",
          "ghsa_id": "GHSA-gqgv-6jq5-jjj9",
          "published_at": "2020-04-30T17:16:47Z",
          "severity": "high",
          "updated_at": "2023-01-09T05:02:30Z",
          "vulnerabilities": [
            {
              "ecosystem": "npm",
              "first_patched_version": "6.0.4",
              "package": "qs",
              "vulnerable_version_range": "<6.0.4"
            },
            {
              "ecosystem": "npm",
              "first_patched_version": "6.1.2",
              "package": "qs",
              "vulnerable_version_range": ">=6.1.0,<6.1.2"
            },
            {
              "ecosystem": "npm",
              "first_patched_version": "6.2.3",
              "package": "qs",
              "vulnerable_version_range": ">=6.2.0,<6.2.3"
            },
            {
              "ecosystem": "npm",
              "first_patched_version": "6.3.2",
              "package": "qs",
              "vulnerable_version_range": ">=6.3.0,<6.3.2"
            }
          ],
          "withdrawn_at": null
        },
        {
          "cve_id": "CVE-2022-24999",
          "ghsa_id": "GHSA-hrpp-h998-j3pp",
          "published_at": "2022-11-27T00:30:50Z",
          "severity": "high",
          "updated_at": "2025-04-29T15:41:45Z",
          "vulnerabilities": [
            {
              "ecosystem": "npm",
              "first_patched_version": "6.2.4",
              "package": "qs",
              "vulnerable_version_range": "<6.2.4"
            },
            {
              "ecosystem": "npm",
              "first_patched_version": "6.10.3",
              "package": "qs",
              "vulnerable_version_range": ">=6.10.0,<6.10.3"
            },
            {
              "ecosystem": "npm",
              "first_patched_version": "6.3.3",
              "package": "qs",
              "vulnerable_version_range": ">=6.3.0,<6.3.3"
            },
            {
              "ecosystem": "npm",
              "first_patched_version": "6.4.1",
              "package": "qs",
              "vulnerable_version_range": ">=6.4.0,<6.4.1"
            },
            {
              "ecosystem": "npm",
              "first_patched_version": "6.5.3",
              "package": "qs",
              "vulnerable_version_range": ">=6.5.0,<6.5.3"
            },
            {
              "ecosystem": "npm",
              "first_patched_version": "6.6.1",
              "package": "qs",
              "vulnerable_version_range": ">=6.6.0,<6.6.1"
            },
            {
              "ecosystem": "npm",
              "first_patched_version": "6.7.3",
              "package": "qs",
              "vulnerable_version_range": ">=6.7.0,<6.7.3"
            },
            {
              "ecosystem": "npm",
              "first_patched_version": "6.8.3",
              "package": "qs",
              "vulnerable_version_range": ">=6.8.0,<6.8.3"
            },
            {
              "ecosystem": "npm",
              "first_patched_version": "6.9.7",
              "package": "qs",
              "vulnerable_version_range": ">=6.9.0,<6.9.7"
            }
          ],
          "withdrawn_at": null
        },
        {
          "cve_id": "CVE-2014-7191",
          "ghsa_id": "GHSA-jjv7-qpx3-h62q",
          "published_at": "2017-10-24T18:33:36Z",
          "severity": "high",
          "updated_at": "2023-04-11T00:27:35Z",
          "vulnerabilities": [
            {
              "ecosystem": "npm",
              "first_patched_version": "1.0.0",
              "package": "qs",
              "vulnerable_version_range": "<1.0.0"
            }
          ],
          "withdrawn_at": null
        },
        {
          "cve_id": "CVE-2026-8723",
          "ghsa_id": "GHSA-q8mj-m7cp-5q26",
          "published_at": "2026-05-22T17:27:19Z",
          "severity": "medium",
          "updated_at": "2026-05-22T17:27:20Z",
          "vulnerabilities": [
            {
              "ecosystem": "npm",
              "first_patched_version": "6.15.2",
              "package": "qs",
              "vulnerable_version_range": ">=6.11.1,<=6.15.1"
            }
          ],
          "withdrawn_at": null
        },
        {
          "cve_id": "CVE-2026-2391",
          "ghsa_id": "GHSA-w7fw-mjwx-w883",
          "published_at": "2026-02-12T17:04:39Z",
          "severity": "low",
          "updated_at": "2026-02-12T20:08:00Z",
          "vulnerabilities": [
            {
              "ecosystem": "npm",
              "first_patched_version": "6.14.2",
              "package": "qs",
              "vulnerable_version_range": ">=6.7.0,<=6.14.1"
            }
          ],
          "withdrawn_at": null
        },
        {
          "cve_id": "CVE-2026-82562",
          "ghsa_id": "GHSA-x5fp-wj9c-mxmx",
          "published_at": "2026-09-02T14:46:57Z",
          "severity": "medium",
          "updated_at": "2026-09-02T14:46:58Z",
          "vulnerabilities": [
            {
              "ecosystem": "npm",
              "first_patched_version": "6.16.0",
              "package": "qs",
              "vulnerable_version_range": ">=6.14.2,<=6.15.3"
            }
          ],
          "withdrawn_at": null
        }
      ]
    }
  }
}
```

The authenticated query inputs were:

```text
GET /advisories?ecosystem=npm&affects=browserslist&per_page=100
GET /advisories?ecosystem=npm&affects=qs&per_page=100
pages: 1 per target
next_page: null per target
exit: 0 per query
```

The content-binding tests at `tests/test_frontend_dependency_guards.py:3400`
and `tests/test_frontend_dependency_guards.py:3548` reject duplicate JSON
keys, wrong batch/scanner identities, record/range omissions, changed package
or ecosystem projections, first-patched drift, and withdrawal drift.

## Per-identity applicability

### npm:browserslist

`D = npm:browserslist`; `S_base` contains one comparable `4.28.2` occurrence.
`F_cutoff` contains three records. Derived `A` is exactly:

```text
GHSA-73wf-gq98-2v4g / CVE-2026-73088
GHSA-c83g-rgw3-j3cx / CVE-2026-73089
```

`GHSA-w8qv-6jwh-64r5` is non-applicable at base because `4.28.2` is above
`>=4.0.0,<4.16.5`, but remains in universal `P_browserslist`.

### npm:qs

`D = npm:qs`; `S_base` contains one comparable `6.15.2` occurrence.
`F_cutoff` contains ten records / twenty-one ranges. Derived `A` is exactly:

```text
GHSA-x5fp-wj9c-mxmx / CVE-2026-82562
GHSA-4mjr-xmp4-gh2g / CVE-2026-82417
```

The other eight records are non-applicable at base because all their affected
ranges end before `6.15.2`. `GHSA-q8mj-m7cp-5q26` ends at `6.15.1`.
`GHSA-crvj-3gj9-gm2p` is retained with `cve_id=null`, affected `<1.0.0`, and
`withdrawn_at=2020-06-16T21:32:53Z`; retention in frozen `F_cutoff` and
universal `P_qs` is not a claim that the withdrawn record is an active current
vulnerability. All twenty-one row boundaries are executable at
`tests/test_frontend_dependency_guards.py:3357`.

## Resolver actions and exact disjoint partition

Runtime and configuration:

```text
base: 863d16ea2328dd32fa6fec6cef4d8f117b6edf85
node: v24.18.1
npm: 11.16.0
registry: https://registry.npmjs.org/
lockfileVersion: 3
flags: --package-lock-only --ignore-scripts --no-audit --no-fund
execution boundary: repository wrapper with cwd set to each isolated package root
```

Each fresh external temp directory reconstructed both frontend npm files from
the exact base. This is the complete reproducible replay setup and the exact
repository-wrapper invocation sequence; every simple or opposite-order
composite replay exited `0`:

```bash
set -e
task_repo_root="$PWD"
task_base="863d16ea2328dd32fa6fec6cef4d8f117b6edf85" # pragma: allowlist secret
task_replay_root="$(mktemp -d)"
task_template="$task_replay_root/template"
task_b1="$task_replay_root/B1"
task_b2="$task_replay_root/B2"
task_q1="$task_replay_root/Q1"
task_q2="$task_replay_root/Q2"
task_bq1="$task_replay_root/BQ1"
task_bq2="$task_replay_root/BQ2"
mkdir -p "$task_template" "$task_b1" "$task_b2" "$task_q1" "$task_q2" "$task_bq1" "$task_bq2"
git archive "$task_base" frontend/package.json frontend/package-lock.json |
  tar -x -C "$task_template"
for task_dir in "$task_b1" "$task_b2" "$task_q1" "$task_q2" "$task_bq1" "$task_bq2"; do
  cp "$task_template/frontend/package.json" "$task_dir/package.json"
  cp "$task_template/frontend/package-lock.json" "$task_dir/package-lock.json"
done

(cd "$task_b1" && "$task_repo_root/scripts/frontend_npm.sh" update browserslist --package-lock-only --ignore-scripts --no-audit --no-fund)
printf 'B1_exit=0\n'
(cd "$task_b2" && "$task_repo_root/scripts/frontend_npm.sh" update browserslist --package-lock-only --ignore-scripts --no-audit --no-fund)
printf 'B2_exit=0\n'
(cd "$task_q1" && "$task_repo_root/scripts/frontend_npm.sh" update qs --package-lock-only --ignore-scripts --no-audit --no-fund)
printf 'Q1_exit=0\n'
(cd "$task_q2" && "$task_repo_root/scripts/frontend_npm.sh" update qs --package-lock-only --ignore-scripts --no-audit --no-fund)
printf 'Q2_exit=0\n'
(
  cd "$task_bq1"
  "$task_repo_root/scripts/frontend_npm.sh" update browserslist --package-lock-only --ignore-scripts --no-audit --no-fund
  printf 'BQ1_browserslist_exit=0\n'
  "$task_repo_root/scripts/frontend_npm.sh" update qs --package-lock-only --ignore-scripts --no-audit --no-fund
  printf 'BQ1_qs_exit=0\n'
)
(
  cd "$task_bq2"
  "$task_repo_root/scripts/frontend_npm.sh" update qs --package-lock-only --ignore-scripts --no-audit --no-fund
  printf 'BQ2_qs_exit=0\n'
  "$task_repo_root/scripts/frontend_npm.sh" update browserslist --package-lock-only --ignore-scripts --no-audit --no-fund
  printf 'BQ2_browserslist_exit=0\n'
)
```

The cwd boundary is material. With npm `11.16.0`, invoking `npm update` from
the repository root with `--prefix` pointing at an external temp directory
rewrote lock paths as temp-local `file:` records; that failed pair equality and
was rejected. The accepted replay and tracked application run the repository
wrapper from inside the package root. The tracked transaction also reconstructs
the exact base lock before both resolver actions; applying an update on top of
the previous safe candidate does not refresh already-satisfied child ranges.

The record-level oracle was run with the repository interpreter resolved by
`scripts/hooks/repo_python.sh`. It loads the exact-base lock using the absolute
PATH-resolved Git binary, computes each delta from the union of all
`packages` keys, and compares the complete before/after JSON record pairs:

```bash
VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"
"$VENV_PYTHON" - "$task_b1" "$task_b2" "$task_q1" "$task_q2" "$task_bq1" "$task_bq2" <<'PY'
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

base_sha = "863d16ea2328dd32fa6fec6cef4d8f117b6edf85"  # pragma: allowlist secret
git = shutil.which("git")
assert git is not None
base = json.loads(subprocess.check_output([git, "show", f"{base_sha}:frontend/package-lock.json"]))
base_package_bytes = subprocess.check_output([git, "show", f"{base_sha}:frontend/package.json"])
directories = dict(zip(("B1", "B2", "Q1", "Q2", "BQ1", "BQ2"), sys.argv[1:]))
paths = {
    name: Path(directory) / "package-lock.json"
    for name, directory in directories.items()
}
documents = {name: json.loads(path.read_bytes()) for name, path in paths.items()}
manifest_paths = {
    name: Path(directory) / "package.json"
    for name, directory in directories.items()
}
missing = object()

def delta(candidate):
    before = base["packages"]
    after = candidate["packages"]
    keys = set(before) | set(after)
    return {
        key: (
            before[key] if key in before else missing,
            after[key] if key in after else missing,
        )
        for key in keys
        if (before[key] if key in before else missing)
        != (after[key] if key in after else missing)
    }

deltas = {name: delta(document) for name, document in documents.items()}
expected_b_keys = {
    "node_modules/baseline-browser-mapping",
    "node_modules/browserslist",
    "node_modules/caniuse-lite",
    "node_modules/electron-to-chromium",
    "node_modules/node-releases",
    "node_modules/update-browserslist-db",
}
expected_q_keys = {"node_modules/qs"}
expected_transitions = {
    "node_modules/browserslist": ("4.28.2", "4.28.8"),
    "node_modules/qs": ("6.15.2", "6.16.0"),
}
assert paths["B1"].read_bytes() == paths["B2"].read_bytes()
assert paths["Q1"].read_bytes() == paths["Q2"].read_bytes()
assert paths["BQ1"].read_bytes() == paths["BQ2"].read_bytes()
assert set(deltas["B1"]) == expected_b_keys
assert set(deltas["Q1"]) == expected_q_keys
assert set(deltas["B1"]).isdisjoint(deltas["Q1"])
assert deltas["BQ1"] == (deltas["B1"] | deltas["Q1"])
assert all(document["packages"][""] == base["packages"][""] for document in documents.values())
assert all(
    {key: value for key, value in document.items() if key != "packages"}
    == {key: value for key, value in base.items() if key != "packages"}
    for document in documents.values()
)
assert all(path.read_bytes() == base_package_bytes for path in manifest_paths.values())
for path, (before_version, after_version) in expected_transitions.items():
    assert base["packages"][path]["version"] == before_version
    assert documents["BQ1"]["packages"][path]["version"] == after_version
for name in ("B1", "B2", "Q1", "Q2", "BQ1", "BQ2"):
    print(f"{name}_sha256={hashlib.sha256(paths[name].read_bytes()).hexdigest()} delta_records={len(deltas[name])}")
print(f"b_delta_keys={sorted(deltas['B1'])}")
print(f"q_delta_keys={sorted(deltas['Q1'])}")
print("delta_key_intersection=[]")
print("combined_full_record_union=true")
print("root_record_equal=true")
print("top_level_metadata_equal=true")
print("all_frontend_package_json_bytes_equal=true")
print("target_transitions=browserslist:4.28.2->4.28.8,qs:6.15.2->6.16.0")
PY

cmp -s frontend/package-lock.json "$task_bq1/package-lock.json"
printf 'tracked_lock_cmp=%s\n' "$?"
git show "$task_base:frontend/package.json" | cmp -s - "$task_bq1/package.json"
printf 'frontend_package_json_cmp=%s\n' "$?"
```

Raw oracle output (`exit=0`):

```text
B1_exit=0
B2_exit=0
Q1_exit=0
Q2_exit=0
BQ1_browserslist_exit=0
BQ1_qs_exit=0
BQ2_qs_exit=0
BQ2_browserslist_exit=0
B1_sha256=df48a425d696879209aea5d749af309daa462f5cbfdf83738f3c167fadd75f2e delta_records=6
B2_sha256=df48a425d696879209aea5d749af309daa462f5cbfdf83738f3c167fadd75f2e delta_records=6
Q1_sha256=5141041123a72476ca429f6de5303a03e7580496727327c5828433a6a82da8c2 delta_records=1
Q2_sha256=5141041123a72476ca429f6de5303a03e7580496727327c5828433a6a82da8c2 delta_records=1
BQ1_sha256=4b6649721614c6a937d3d1dd445301d1e905700df814a63ea5d6e8fa28bfb615 delta_records=7
BQ2_sha256=4b6649721614c6a937d3d1dd445301d1e905700df814a63ea5d6e8fa28bfb615 delta_records=7
b_delta_keys=['node_modules/baseline-browser-mapping', 'node_modules/browserslist', 'node_modules/caniuse-lite', 'node_modules/electron-to-chromium', 'node_modules/node-releases', 'node_modules/update-browserslist-db']
q_delta_keys=['node_modules/qs']
delta_key_intersection=[]
combined_full_record_union=true
root_record_equal=true
top_level_metadata_equal=true
all_frontend_package_json_bytes_equal=true
target_transitions=browserslist:4.28.2->4.28.8,qs:6.15.2->6.16.0
exit=0
tracked_lock_cmp=0
frontend_package_json_cmp=0
```

Complete delta:

| Class | Identity / record | Base | Candidate | Notes |
| --- | --- | ---: | ---: | --- |
| `I_R[browserslist]` | `browserslist` | `4.28.2` | `4.28.8` | authored target replacement |
| `C_R[browserslist]` | `baseline-browser-mapping` | `2.10.37` | `2.11.21` | resolver closure |
| `C_R[browserslist]` | `caniuse-lite` | `1.0.30001799` | `1.0.30001810` | resolver closure |
| `C_R[browserslist]` | `electron-to-chromium` | `1.5.372` | `1.5.422` | resolver closure |
| `C_R[browserslist]` | `node-releases` | `2.0.47` | `2.0.54` | resolver closure |
| `C_R[browserslist]` | `update-browserslist-db` | `1.2.3` | `1.3.2` | resolver closure |
| `I_R[qs]` | `qs` | `6.15.2` | `6.16.0` | full record also changes `side-channel ^1.1.0 -> ^1.1.1` and adds `es-define-property ^1.0.1` |

`C_R[qs]` is empty: the two dependency-map changes belong to the same authored
`node_modules/qs` record; no child package record moved. Complete before/after
record equality—not versions alone—establishes the partition.

## Audit results

Exact-base terminal frontend audit:

```text
$ npm audit --package-lock-only --json
exit: 1
vulnerability_keys: browserslist, qs
moderate: 1
high: 1
critical: 0
total: 2
```

The prior combined candidate
`155f75cf12988ded917d7c4a36b36da2b06c3b9d4bd5870811d5067ef718e5c0`
had the following terminal audit receipt before the later deterministic child
patch drift:

```text
$ npm audit --package-lock-only --json
exit: 0
vulnerabilities: {}
info: 0
low: 0
moderate: 0
high: 0
critical: 0
total: 0

$ npm audit --package-lock-only --audit-level=moderate
exit: 0
found 0 vulnerabilities

$ npm audit --package-lock-only --audit-level=high
exit: 0
found 0 vulnerabilities
```

For the refreshed candidate
`4b6649721614c6a937d3d1dd445301d1e905700df814a63ea5d6e8fa28bfb615`,
the full dependency guard passes and authenticated GAD queries at
`2026-09-04T11:01:55Z` return zero advisory records for the two changed closure
identities `baseline-browser-mapping@2.11.21` and
`electron-to-chromium@1.5.422`. Initial npm bulk-audit attempts timed out or
returned `503 Service Unavailable`; they were retained as infrastructure
diagnostics and never treated as PASS. A later unchanged-lock retry completed
at `2026-09-04T12:15:02Z`:

```text
$ npm audit --package-lock-only --json
exit: 0
vulnerabilities: {}
info: 0
low: 0
moderate: 0
high: 0
critical: 0
total: 0

$ npm audit --package-lock-only --audit-level=moderate
exit: 0
found 0 vulnerabilities

$ npm audit --package-lock-only --audit-level=high
exit: 0
found 0 vulnerabilities
```

Current-candidate npm-audit acceptance is therefore terminal for the exact
`4b664972...` lock.

`audit-level` changes the exit threshold and does not filter lower-severity
report rows. Batch acceptance therefore depends on the default total-zero JSON
result, not a HIGH-only exit. The earlier network failures did not change the
replay-proven dependency partition or substitute for the successful retry.

## Permanent conjunctive postcondition

The exact authorization literal and data maps are at
`tests/test_frontend_dependency_guards.py:214`. The shared executor at
`tests/test_frontend_dependency_guards.py:1623`:

1. requires exactly the literal targets `browserslist` and `qs`;
2. enumerates each tracked npm surface and rejects duplicate raw JSON members;
3. rejects direct, aliased, override, or bundled ownership for either target;
4. delegates all other source semantics to installed npm's
   `npm-package-arg`/`semver` adapter and rejects opaque sources;
5. requires dependency manifests and root lock records to match exactly and
   admits only lockfile v3;
6. validates every non-root lock record through the existing canonical
   registry-provenance adapter;
7. loads each complete virtual graph through the hermetic repository npm
   wrapper, with ambient graph-shaping configuration removed;
8. independently discovers every raw canonical/nested target occurrence;
9. rejects links, prereleases, malformed versions, identity/path conflicts,
   foreign provenance, and invalid 64-byte SHA-512 SRI metadata;
10. compares each occurrence with every affected range for its target;
11. permits per-target executable absence only after the complete shared
    admission pass.

The permanent guard does not freeze base/candidate hashes, occurrence counts,
or `4.28.8` / `6.16.0` as the only future-safe versions. Passing SRI syntax is
not a cryptographic recomputation of fetched package bytes. Opaque or future npm
semantics stop for rescope instead of creating another carrier parser.

## Provider projection

At `2026-09-04T10:44:52Z`, the complete authenticated open Dependabot census
contained only alert `#273` for Browserslist / `GHSA-73wf-gq98-2v4g`, state
`open`, development scope, `frontend/package-lock.json`, with no fixed or
dismissed timestamp. No authenticated alert currently projects `qs`; this is a
provider-projection gap, not evidence of `qs` closure or non-applicability.

Repository remediation is `P_browserslist AND P_qs`. Provider closure is a
separate post-merge observation. No alert is dismissed.

## Verification, rollback, and stop conditions

Focused verification commands include:

```text
python -m pytest -q tests/test_frontend_dependency_guards.py
python scripts/ci/check_docs_phase1_gates.py --files docs/security/FRONTEND_BROWSERSLIST_REMEDIATION_CLASS.md docs/security/DEPENDABOT_ALERT_INVENTORY.md
npm query '#browserslist' --package-lock-only --json
npm query '#qs' --package-lock-only --json
npm ls browserslist qs --all --package-lock-only --json
npm explain browserslist
npm explain qs
```

The complete focused file collects 229 tests after the batch expansion.

Before merge, rollback means abandoning the branch/PR. After merge, never return
either identity to an affected version; use a separate secure roll-forward.

Stop on a third vulnerable identity or authored action, empty `A`, incomplete or
incomparable GAD inventory, replay mismatch, overlapping independent deltas,
combined non-union, manifest/root/unrelated package movement, missing provenance
or integrity, affected head occurrence, nonzero default/MODERATE audit, new npm
grammar branch, second evidence owner, suppression/waiver/dismissal, stale
base/head, or unresolved review/CI evidence.

This document does not claim production exploitability, whole-repository
security, provider review, provider scan, PASS, no findings, approval, merge
readiness, deployment, or release authority.

<!-- markdownlint-enable MD013 MD031 MD032 -->
