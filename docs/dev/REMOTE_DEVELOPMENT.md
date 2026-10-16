# Remote development on a private Linux VM — RDEV-01

<!-- markdownlint-disable MD013 -->

The existing MacBook retains Xcode, one selected Simulator, Apple builds,
indexing/debugging/signing, its local iOS checkout and installed application UIs.
One ordinary Linux VPS runs Docker Engine/Compose, the selected devcontainer,
backend/web development and Linux checks explicitly sent over SSH. The PRIMARY
Codex desktop/chat, configured Mac Computer Use/browser/apps/plugins and their
permissions remain LOCAL; an optional remote Codex CLI is a separately scoped
worker, not required for each check. OpenDesign stays a
local installed app; only identified Linux-capable commands may later count as
offloaded. Ollama remains future-only. Do not replace the primary local chat with
a remote project or assume SSH transfers Mac tools. VS Code is optional.
**Remote acceptance remains pending**. The owner purchased the VM and host-level
SSH/Docker setup and manual runtime-container bootstrap have been observed.
Published PR [#2491](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2491)
has observed candidate validation and private-preview components below. The
post-open recipe/test corrections in this revision still require fresh validation;
full persistence, recovery and measured local Apple benefit remain separate.

Root [AGENTS.md](../../AGENTS.md) owns policy and validation budgets. Follow
[agent onboarding](AGENT_COMPATIBILITY_ONBOARDING.md) and the governing
coordinator/packet/role sequence. Host and container execution are explicit;
this runbook introduces no command router or product authority.

## Current truth and commercial decision

Accepted reference: `RDEV01.acceptance.v1` plus the explicit owner revision
`RDEV01.owner-decision.d1823604.20261015.v1`: Linux offload with local Apple work.
All ten original criteria remain required; that revision adds measured local
Xcode/Simulator benefit. Latest execution reference:
`RDEV01.owner-execution.56e898f1.20261016.v1`: primary LOCAL control, exact current
material over SSH, persistent remote results and no silent local-heavy fallback. The owner permits starting on red main with separately
owned #2477 still open; this is a start exception, not a validation waiver.

Owner port revision `RDEV01.owner-ports.20261016.v1` selects LOCAL backend
**18001** and web **15173**, forwarding to unchanged container ports 8001/5173.
Existing SurrealDB/Surrealist services retain local 8000/8001 and their data.
The original iOS Debug/Simulator integration obligation remains pending until a
separately admitted compatible solution; no iOS or Release configuration changes
follow from this port decision. Owner maintenance requirement
`RDEV01.owner-reboot-recovery.20261016.v1` adds verified off-VPS result preservation
before every long run and explicit recovery after a host reboot.
Combined continuation reference: `RDEV01.owner-ports-reboot.20261016.v1`.

Purchased by the owner: Contabo Core VPS 12, **USA CENTRAL**, 12 shared vCPU,
48 GB RAM, 400 GB SSD, Ubuntu 24.04 LTS amd64, **one full month**, with Automated
Backup. Final checkout observed on 2026-10-16: **EUR 37.50 monthly and due today,
EUR 0 setup and EUR 0 VAT**. The owner paid and the instance became available.
The earlier EUR 30.80 quote excluded backup. Checkout observation is separate
from the final invoice, card settlement and capacity acceptance.

**USD 60 is the hard total for all NEW infrastructure per full month**, including
mandatory fees/taxes, USD conversion and an explicit independent-copy allowance;
existing DigitalOcean bills are outside this new-infrastructure ceiling. Retain
the final invoice, card conversion, renewal/cancellation/refund terms and the
independent-copy reserve before claiming commercial reconciliation. Further
purchases require a separate human decision; do not change region, tariff, term
or budget silently. Provider backup is enabled, but the observed US-central
service warning says backups may be delayed and restores temporarily unavailable.
No first successful backup, restore or independent recovery has been verified.

Re-query main and [#2477](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2477)
before integration. Read-only foreign head
`4df6d45c8662d55bd4996e68fb125fe741582bc3` is the admitted runtime-only preview,
with tree `8fab68ff10a4e634d11e04258875c123294e9230`; the RDEV candidate remains
based on `ea40bc78a433c4e0ab4333b4fbffa41b79349659`. Runtime uses psycopg[c]
and cryptography 50.0.2; the candidate uses psycopg[binary] and cryptography 50.0.0.
Runtime Python bootstrap cannot prove candidate dependency parity. Foreign Docker/Make/dependency
ownership remains unchanged. Bind remote observations to the coordinator-admitted
ACTUAL runtime SHA, including an unmerged #2477 revision only when explicitly
admitted for that development observation. Its merge is not a prerequisite to
this parallel lane. Do not adopt the foreign branch into the RDEV PR or borrow its
gates. When #2477 merges, synchronize normally, reread affected instructions and
repeat only impacted proof under the current-head policy.

The dated 2026-10-16 post-open readback still found #2477 OPEN, now at
`ca46de5a9ed3889859dc58bed6c8352f378dbb60`. The earlier `4df6d45c...`
identity remains the historical runtime preview, not a current foundation
merge or permission to adopt its locks, code or successful checks. CD remains a
separately owned lane; RDEV-01's own CI and review gates remain required.

References: [Contabo configurator](https://contabo.com/en-us/vps/cloud-vps-core-12),
[official devcontainer CLI](https://code.visualstudio.com/docs/devcontainers/devcontainer-cli),
[Docker Ubuntu installation](https://docs.docker.com/engine/install/ubuntu/),
[Docker port behavior](https://docs.docker.com/engine/network/packet-filtering-firewalls/),
[Codex authentication](https://learn.chatgpt.com/docs/auth).

### Observed host and runtime checkpoint — 2026-10-16

The SSH host key was compared with the authenticated provider console before
strict key login. Two separate `dev` key logins/reconnects succeeded. SSH password
and keyboard-interactive authentication are disabled; root key recovery remains.
UFW admits incoming SSH 22 only. The local alias `pulseplate-rdev01` selects the
dedicated identity and known-hosts file without agent forwarding. These host
observations do not establish application exposure or full remote acceptance.

Native SDK images were built from the admitted runtime source. The selected
container binds `/home/dev/work/PulsePlate` at `/workspaces/PulsePlate`, runs as
vscode UID/GID 1001, has no published ports or Docker socket, and showed zero
restarts and no OOM. Python is 3.13.5; installed container Node is 24.22.0 rather
than `.nvmrc` 24.18.1. The existing frontend wrapper permits this with a warning;
exact CI Node parity is not claimed.

Preserve the failure history: an initial preflight stopped before CLI execution
because task artifacts used a non-ignored path. Moving only those artifacts into
`artifacts/orchestration/` restored clean status. Actual CLI attempt one failed
because modern Compose/Bake requested filesystem access to the optional
acquisition secret `/dev/null`. The admitted recovery selected an empty regular
mode-0600 file **inside the existing build context**, through the existing
`PULSEPLATE_NATIVE_SDK_NETRC_FILE` selector. The approved proxy was reachable
without authentication; no Mac credential was copied. Do not disable Bake
filesystem checks or add broad entitlements to bypass this error.

Actual CLI attempt two built the images and started the container, then its
TTY lifecycle helpers stopped through background job control. The exact owned
launcher was terminated; CLI, host and launcher returned **143**, and native
process inspection confirmed no remaining owned helpers. This is an interrupted
CLI lifecycle, never a successful `up`. The existing exact `safe.directory`
setting was read back without replaying the postStart command. Manual recovery
retained the container and changed only the roots of three verified empty named
volumes to UID/GID 1001; vscode write access then passed. Initial manual bootstrap
returned 2 because pre-commit could not create its cache under a root-owned
parent. Creating only the absent `/home/vscode/.cache/pre-commit` child as
1001:1001, mode0700, allowed one canonical bootstrap recovery to return 0.
Tracked source remained clean. Separate `make verify-env` and native tooling
smoke each returned guest 0/host 0. These are exact runtime-preview results;
the separate own-candidate environment proof is recorded below. Full acceptance
remains pending, and the two CLI attempts are spent; no third attempt is implied.
BuildKit clipped one compiler stage at its native 2 MiB limit; complete compiler
stdout is unavailable even though the retained CLI stream shows image completion.

### Published candidate checkpoint and post-open corrections — 2026-10-16

Published material C0 is `85e56e8ed2e73e7e9c74ae73746079448dcb681a`, parent
`ea40bc78a433c4e0ab4333b4fbffa41b79349659`, tree
`a42837f1a95f52eaf49a34747e95ea152f40e11b`, in PR #2491. Its native candidate
environment used its own canonical venv with Python 3.13.5, psycopg-binary 3.3.4
and cryptography 50.0.0. Own `make venv`, pip check, `make verify-env`, scoped
preflight and agent consistency passed separately from the foreign runtime.
Node 24.18.1/npm 11.16.0 ran the retained focused two-file/10-test bundle,
typecheck and build successfully; existing build warnings were retained.

The final C0 source projection passed all-files pre-commit with actual guest 0,
host 0 and original-index restoration 0. Native commit hooks passed, and committed
`make validate-changed` actually selected the docs path-leakage test. The exact-C0
zero-network Apple Oracle accepted two metadata guards in one attempt, with no
mutated paths and `promotion_ready=false`; this supplies no application,
TypeScript, operational, provider-review or security-scan result. The ordinary
named-origin push and its native hooks returned 0; GitHub confirmed C0.

Off-VPS retention covered 419 files/14 directories/four verified native bundles,
then 102 current-gate files, 23 commit/ferry entries and 27 publication files with
complete selected membership, bytes, modes and SHA checks. Retained Mac work and
returned owned results were verified, including the native C0 ferry. Earlier
private browser/API health 200 and synthetic validation 422 were observed through
local 18001/15173; owned apps/tunnel were stopped. These are bounded components,
not a VM-loss restore, public-refusal result, Simulator integration or comparable
Apple performance measurement.

The single post-open QA → bug-hunter → security role pass completed and identified
six bounded recipe/test/status defects. The following corrections are written
procedures until their targeted native rehearsal succeeds. C0 evidence remains
historical for its exact source; it does not validate this changed material.
Fresh affected VPS checks/current-head CI, final-material self-review,
provider-neutral seal, mapping, strict readiness and the review wait remain
pending. Existing automatic provider quota output creates no retry requirement.
The 14:14 UTC factual cloud checkpoint was read back in all five existing IDs
with history/metadata and the native table preserved; this changed revision still
needs its own continuity update, and RD01-10 remains not achieved.

## Exact material transfer from one authoritative source

For each run declare ONE authoritative task checkout, normally the selected Mac
checkout, and freeze selected source during capture/transfer/testing. Record
branch, intended base and HEAD, plus index **I**, working tree **W**, selected new
files/deletions/types/modes. Equal HEAD is not equal material. No simultaneous
remote author or overwrite of an active receiver; later local edits require a new
snapshot. Retain Mac originals/Apple checkout, unique data and original index.

This is a manual native Git/SSH/rsync procedure, not an automatic transport helper.
Use a dedicated Bash shell with `set -euo pipefail`; replace reviewed placeholders
before execution. Capture/receiver directories must be new, owned and private.
These future instructions are not observed transfer or test evidence.

### Capture committed history and separate I/W patches on the Mac

```bash
set -euo pipefail
RDEV_SOURCE="$PWD"
RDEV_CAPTURE=<new-private-owned-capture-directory>
RDEV_BRANCH="$(git branch --show-current)"
RDEV_HEAD="$(git rev-parse HEAD)"
RDEV_BASE=<coordinator-admitted-base-sha>
umask 077
mkdir "$RDEV_CAPTURE"   # Collision stops; never reuse an old capture.
RDEV_SELECTED=(CONTRIBUTING.md docs/dev/CODEX_SKILLS.md docs/dev/REMOTE_DEVELOPMENT.md docs/roadmap/BACKLOG_LEDGER.md frontend/AGENTS.md frontend/vite.config.ts frontend/src/config/__tests__/remoteDevelopmentProxy.test.ts)
git bundle create "$RDEV_CAPTURE/source.bundle" "$RDEV_BRANCH"
git bundle verify "$RDEV_CAPTURE/source.bundle"
git diff --cached --binary --full-index --no-renames --no-ext-diff --no-textconv HEAD -- "${RDEV_SELECTED[@]}" > "$RDEV_CAPTURE/index.patch"
git diff --binary --full-index --no-renames --no-ext-diff --no-textconv -- "${RDEV_SELECTED[@]}" > "$RDEV_CAPTURE/working.patch"
git diff --cached --name-status -z --no-renames HEAD -- "${RDEV_SELECTED[@]}" > "$RDEV_CAPTURE/index-paths.z"
git diff --name-status -z --no-renames -- "${RDEV_SELECTED[@]}" > "$RDEV_CAPTURE/working-paths.z"
git ls-files --stage -z -- "${RDEV_SELECTED[@]}" > "$RDEV_CAPTURE/index-modes.z"
git ls-files --others --exclude-standard -z -- "${RDEV_SELECTED[@]}" > "$RDEV_CAPTURE/newfiles.z"
shasum -a 256 "$RDEV_CAPTURE/source.bundle" "$RDEV_CAPTURE/index.patch" "$RDEV_CAPTURE/working.patch" "$RDEV_CAPTURE/newfiles.z"
```

Record branch/base/HEAD and complete selected I/W/new/deleted inventories in
private task notes. Ipatch is HEAD->I; Wpatch is I->W. Staged additions belong to
Ipatch already. A staged deletion plus untracked same-path re-add is two states:
I absent, W present. Do not collapse patches into HEAD->W and claim original
staging was reproduced. No synthetic commit is required.

Review the scoped `newfiles.z` and every selected new file: canonical relative
path contained beneath source/receiver, regular leaf, expected real parents,
mode/size/bytes/SHA256, no traversal/surprise symlink/gitlink. Keep lists NUL-safe
(`-z`, rsync `--from0`), not whitespace pipelines. Unsupported types, source drift
or EOL/filter normalization preventing exact bytes stop transfer for scope review.
No home, `.git` administration, `.env`, credentials/auth, private keys/browser
profiles, `.venv` or dependency caches. No follow-link copy, `--delete` or two-way
sync. This bounded cooperative freeze does not promise hostile same-user exclusion.

### Receive and verify in the selected Linux container

Transfer only the reviewed capture through strict verified SSH. Use the existing
`artifacts/orchestration/` ignored namespace for transfer and run data. Before
creating those directories in a fresh clone, verify its actual ignore rules:

```bash
ssh pulseplate-rdev01 'git -C /home/dev/work/PulsePlate check-ignore -- artifacts/orchestration/rdev01-transfers artifacts/orchestration/rdev01-runs'
```

An untracked artifact stops setup; do not assume the Mac's local exclusions exist
on the VM. After creating a fresh collision-refusing private destination beneath
the owned transfer root:

```bash
rsync -rtp "$RDEV_CAPTURE/" pulseplate-rdev01:/home/dev/work/PulsePlate/artifacts/orchestration/rdev01-transfers/<fresh-snapshot>/
# In the selected container PRIMARY clone (not on the Mac):
set -euo pipefail
RDEV_SNAPSHOT_ID="REPLACE-FRESH-SNAPSHOT-ID"
RDEV_SOURCE_BRANCH="REPLACE-RECORDED-BRANCH"
RDEV_HEAD="REPLACE-RECORDED-FULL-HEAD-SHA"
RDEV_BASE="REPLACE-RECORDED-FULL-BASE-SHA"
[[ "$RDEV_SNAPSHOT_ID" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]]
RDEV_IMPORT_REF="refs/rdev01/imports/$RDEV_SNAPSHOT_ID"
RDEV_BUNDLE="/workspaces/PulsePlate/artifacts/orchestration/rdev01-transfers/$RDEV_SNAPSHOT_ID/source.bundle"
git check-ref-format "$RDEV_IMPORT_REF"
git check-ref-format --branch "$RDEV_SOURCE_BRANCH"
git bundle verify "$RDEV_BUNDLE"
if git show-ref --verify --quiet "$RDEV_IMPORT_REF"; then
  printf '%s\n' 'Import ref already exists; preserve it and stop.' >&2
  exit 1
else
  RDEV_REF_STATUS=$?
  test "$RDEV_REF_STATUS" -eq 1   # Only native confirmed absence permits fetch.
fi
git fetch --no-tags --no-write-fetch-head "$RDEV_BUNDLE" "refs/heads/$RDEV_SOURCE_BRANCH:$RDEV_IMPORT_REF"
test "$(git rev-parse --verify "$RDEV_IMPORT_REF^{commit}")" = "$RDEV_HEAD"
git cat-file -e "$RDEV_BASE^{commit}"
git worktree add --detach /workspaces/PulsePlate/worktrees/REPLACE-OWNED-RECEIVER "$RDEV_IMPORT_REF"
```

Reserve this fresh snapshot ID/import ref for one cooperative transfer owner;
no other task may create or update that same ref during absence/fetch/comparison.
Different captures use different refs, so another capture's fetch cannot replace
this receipt. The executable equality check precedes worktree creation. Shared
FETCH_HEAD is neither written nor used as evidence by this fetch. The selected
VPS Git help and self-only dry-run accepted `--no-write-fetch-head`; that option
support is not actual transfer/interleaving proof. No all-refs fetch, force update,
source checkout mutation or hostile-concurrency/atomicity guarantee follows.
Create an owned CLEAN receiver at exact source HEAD; never overlay a foreign dirty checkout.
After native bundle verification/fetch of the selected branch, use the existing
visible common Git directory for a detached nested worktree. Record that intended
base and HEAD are available and match, without foreign #2477 source/base adoption.
The source branch name is recorded provenance. The receiver is deliberately a
DETACHED worktree: match its HEAD/base and actual I/W material, not the output
of `git branch --show-current` to the source branch name. An empty receiver branch
name is expected here, not missing material. All normal Git mutations/hooks
occur in the selected container.

```bash
# INSIDE the clean exact-HEAD receiver in the selected container:
# Replace REPLACE-SNAPSHOT with the verified received snapshot directory.
set -euo pipefail
RDEV_INDEX_PATCH="/workspaces/PulsePlate/artifacts/orchestration/rdev01-transfers/REPLACE-SNAPSHOT/index.patch"
RDEV_WORKING_PATCH="/workspaces/PulsePlate/artifacts/orchestration/rdev01-transfers/REPLACE-SNAPSHOT/working.patch"
RDEV_INDEX_SHA256="REPLACE-RECORDED-INDEX-PATCH-SHA256"
RDEV_WORKING_SHA256="REPLACE-RECORDED-WORKING-PATCH-SHA256"
git rev-parse HEAD
git status --short
# Validate BOTH frozen inputs before the first mutating apply.
for RDEV_PATCH in "$RDEV_INDEX_PATCH" "$RDEV_WORKING_PATCH"; do
  test ! -L "$RDEV_PATCH"
  test -f "$RDEV_PATCH"
  test -r "$RDEV_PATCH"
done
printf '%s  %s\n' "$RDEV_INDEX_SHA256" "$RDEV_INDEX_PATCH" | sha256sum -c -
printf '%s  %s\n' "$RDEV_WORKING_SHA256" "$RDEV_WORKING_PATCH" | sha256sum -c -
if test -s "$RDEV_INDEX_PATCH"; then
  git apply --check --index "$RDEV_INDEX_PATCH"
  git apply --index "$RDEV_INDEX_PATCH"
fi
if test -s "$RDEV_WORKING_PATCH"; then
  git apply --check "$RDEV_WORKING_PATCH"
  git apply "$RDEV_WORKING_PATCH"
fi
```

W apply deliberately has NO `--index`. An empty patch is an explicitly verified
empty transition: omit only its check/apply pair after both files' type,
readability and captured hash checks. Missing input is never empty input, and a
failed nonempty check/apply stops. Keep the source/receiver freeze and reviewed
real parent paths throughout; these checks do not exclude a hostile same-UID
writer. No unsafe-path apply. Once the receiver exists, copy selected regular
new files from frozen Mac:

```bash
rsync -rtp --from0 --files-from="$RDEV_CAPTURE/newfiles.z" "$RDEV_SOURCE/" pulseplate-rdev01:/home/dev/work/PulsePlate/worktrees/<owned-receiver>/
```

At BOTH ends compare bundle/patch/list hashes, recorded source branch provenance,
receiver HEAD/base and expected I and W
membership/content/modes, selected new-file hashes and deleted-path absence.
Native `git ls-files --stage` and index blob inspection describe I; file SHA256/
stat describe W. Mac uses `shasum -a 256`, Linux `sha256sum`. Check existence/type
before hashing: missing is not a match. Verify source still matches capture;
partial transfer, mode drift, stale deleted files or divergent receiver stop tests.
Keep full private inventories out of public evidence. Hashes bind selected bytes,
not authenticity or execution. Runtime/image/SDK identity is separate from
candidate base/HEAD/I/W; foreign provisioning cannot substitute candidate recipes.
Preserve received I/W during the run and retain originals/unique evidence through
return-to-Mac verification. Independent VM-loss/B2 recovery remains future-only.

## VM host setup after purchase approval

The following steps apply only to the new, identified development VM. Record its
provider identity and exact Ubuntu/kernel, architecture, disk and Docker versions.
Use the provider console to obtain the SSH host-key fingerprint independently;
an unverified `ssh-keyscan` does not authenticate the host. Keep recovery access
until a second key-authenticated login and reconnect as `dev` both work.

Generate a dedicated key on the Mac, keeping its private half there:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/pulseplate_rdev01 -C pulseplate-rdev01
```

On the VM, through the authenticated initial administrative session:

```bash
sudo adduser dev
sudo usermod -aG sudo dev
sudo install -d -o dev -g dev -m 0700 /home/dev/.ssh
sudo install -d -o dev -g dev -m 0750 /home/dev/work
sudo apt-get update
sudo apt-get install -y ca-certificates curl git tmux
```

Install only the dedicated public key in `dev`'s mode-0600 `authorized_keys`.
Authenticate the host record on the Mac against the provider-console fingerprint,
then configure a local `Host pulseplate-rdev01` entry selecting `User dev`, the
actual VM address, dedicated `IdentityFile`, `IdentitiesOnly yes`,
`StrictHostKeyChecking yes`, `ForwardAgent no` and a dedicated known-hosts file.
Do not log private keys or blindly accept a changed fingerprint.

Follow [Docker's official Ubuntu repository instructions](https://docs.docker.com/engine/install/ubuntu/#install-using-the-apt-repository)
for Engine and the `docker compose` plugin. Observed host versions: Ubuntu
24.04.5, Engine 29.9.1, Compose 5.6.0, Buildx 0.38.0, host Node 24.18.1/npm
11.16.0 and Dev Containers CLI 0.89.0. Compose 5 retains the v2 command model;
see [Docker's version history](https://docs.docker.com/compose/intro/history/).
On a fresh Ubuntu 24.04 amd64 VM, after
confirming no conflicting existing installation or data:

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<'EOF'
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: noble
Components: stable
Architectures: amd64
Signed-By: /etc/apt/keyrings/docker.asc
EOF
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Record exact installed versions; a floating repository install is not a version
receipt. If existing Docker/data or a different OS is found, stop this fresh-host
recipe and reconcile it. After host installation, allow the trusted operator
account to manage Docker:

```bash
sudo usermod -aG docker dev
# Log out and back in as dev before checking group membership.
docker version
docker compose version
uname -m
df -h /home/dev/work
free -h
```

Docker group access is root-equivalent host authority. A separate user organizes
work; it does not isolate that user from the host. Keep daemon management on the
VM host, with no Docker socket/home mount in the devcontainer. Permit intended
SSH ingress only; do not open 8000/8001/5173 publicly or use production/staging Compose.
After a second verified `dev` login/reconnect, validate `sshd -t` and actual loaded
SSH settings before approved restrictions on initial root/password login. Preserve
provider recovery access. Do not apply staging/production SSH or firewall changes.

## Explicit SSH and feature-enabled container startup

Initial source acquisition on the identified VM host as `dev` creates an
independent primary clone. Private repository access needs its own owner-approved
least-privilege credential; automatic Mac agent forwarding/credential copies are
outside this workflow. Keep the separate local Apple checkout and Mac originals.

```bash
# Initial acquisition before a container exists; subsequent project Git mutations
# and hooks use the selected container below.
git clone https://github.com/Katsiarynakavaleuskaya/PulsePlate.git /home/dev/work/PulsePlate
cd /home/dev/work/PulsePlate
git rev-parse HEAD
git status --short
```

Keep the PRIMARY configured Codex desktop/chat on the Mac, retaining existing
Computer Use/browser/apps/plugins and permissions. Observe a permitted benign
local action when proving capability. Developer Mode is not blanket permission;
this workflow changes no Accessibility/Screen Recording/app/browser setting.
Remote projects describe remote files/shell, not Mac tools, and local UI/session
RAM does not move to the VPS.

The local controller sends ordinary explicit SSH commands to the identified
Linux host, then selected-container exec for repository commands. Remote Codex
CLI is OPTIONAL for separately scoped delegated work, with its OWN install/
skills/owner login on the actual executing host/container. Do not copy Mac auth,
private keys/home, provider credentials or signing material. No required remote
project/app-server, second agent, editor or dynamic command router is introduced.

```bash
# LOCAL controller: HOST identity only, not container proof.
ssh pulseplate-rdev01 hostname
# LOCAL controller: explicit selected remote container command.
ssh pulseplate-rdev01 '/home/dev/.local/bin/devcontainer exec --workspace-folder /home/dev/work/PulsePlate --container-id <observed-container-id> make verify-env'
```

Ordinary noninteractive SSH must first show the intended Node version and the
recorded absolute CLI path/version; an interactive terminal's PATH is insufficient.
The examples use the admitted `/home/dev/.local` user prefix. Missing remote
Node/CLI or a different installation path stops setup; do not try local tools or
implicit network bootstrap.

Each job binds candidate receiver/cwd and I/W/HEAD view, not just this primary
workspace. SSH/transfer/runtime/material failure stops the Linux-heavy step with
its raw diagnostic. It MUST NOT silently run on Mac; local-heavy execution needs
a separate explicit owner decision. This runbook is not that decision. Required
native Apple checks remain on macOS.

Use the official CLI, not editor-only startup or raw Compose. On Linux host,
provision the exact `.nvmrc` Node baseline (currently 24.18.1), Python and required
native toolchain through official sources. Official package metadata checked on
2026-10-15 identifies stable `@devcontainers/cli` **0.89.0**, requiring Node >=20
([official package metadata](https://registry.npmjs.org/@devcontainers%2fcli/0.89.0));
record the actual installed version and help. No implicit floating npx bootstrap.

```bash
npm install --global --prefix "$HOME/.local" @devcontainers/cli@0.89.0
export PATH="$HOME/.local/bin:$PATH"
devcontainer --version
devcontainer up --help
docker compose version
```

Before `up`, confirm installed help supports **`--no-lockfile`**. If absent, stop
setup for scope admission; do not author an unadmitted `.devcontainer-lock.json`.
The approved proxy setting belongs to the Linux CLI host process; `localEnv`
means this host, not an unrelated Mac shell. Keep the index credential-free and
use only #2477's existing approved acquisition-secret interface for native SDK/
wheelhouse construction. Do not log/render the full Compose environment or copy
Mac `.netrc`. No fake SDK, tooling-only target or public-index/raw-pip fallback.

**Before the first CLI `up`, acquire the canonical Docker source artifacts.**
The #2477 `dc-up` Make target depends on `docker-source-artifacts`; direct CLI
startup bypasses that Make prerequisite. Use its existing stdlib fetcher through
Make, with an explicitly resolved absolute HOST Python, to populate ignored
`build/docker-sources` and retain the native manifest/source-hash checks. This is
only pre-container acquisition alongside initial clone/host tools; application
bootstrap/tests and normal project Git mutations/hooks still run in the selected
container. Do not opt into separate Alertmanager qualification, source compilation
or additional build modes. A failed acquisition stops before `up`.

```bash
set -euo pipefail
export PULSEPLATE_PYTHON_INDEX_URL=https://packages.pulseplate.app/root/pulseplate/+simple/
unset PULSEPLATE_PYTHON_TRUSTED_HOST
# Linux host, admitted primary clone; stdlib acquisition only, no host app bootstrap.
RDEV_HOST_PYTHON="$(readlink -f "$(command -v python3)")"
test -x "$RDEV_HOST_PYTHON"
make DEV_PYTHON="$RDEV_HOST_PYTHON" ensure-python-proxy docker-source-artifacts
# Modern Bake needs the optional empty acquisition input inside this context.
test "$(pwd -P)" = /home/dev/work/PulsePlate
git check-ignore -- artifacts/orchestration/rdev01-build-inputs
umask 077
for RDEV_PARENT in artifacts artifacts/orchestration; do
  test ! -L "$RDEV_PARENT"
  if test ! -e "$RDEV_PARENT"; then mkdir "$RDEV_PARENT"; fi
  test -d "$RDEV_PARENT" && test -O "$RDEV_PARENT"
done
RDEV_INPUT_DIR="$(mktemp -d "$PWD/artifacts/orchestration/rdev01-build-inputs.XXXXXX")"
RDEV_EMPTY_NETRC="$RDEV_INPUT_DIR/empty.netrc"
test ! -e "$RDEV_EMPTY_NETRC" && test ! -L "$RDEV_EMPTY_NETRC"
(set -C; : > "$RDEV_EMPTY_NETRC")
test -f "$RDEV_EMPTY_NETRC" && test ! -L "$RDEV_EMPTY_NETRC" && test -O "$RDEV_EMPTY_NETRC"
test "$(stat -c '%a' "$RDEV_EMPTY_NETRC")" = 600
test "$(stat -c '%s' "$RDEV_EMPTY_NETRC")" = 0
printf '%s  %s\n' e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 "$RDEV_EMPTY_NETRC" | sha256sum -c -
export PULSEPLATE_NATIVE_SDK_NETRC_FILE="$RDEV_EMPTY_NETRC"
devcontainer up --workspace-folder /home/dev/work/PulsePlate --config /home/dev/work/PulsePlate/.devcontainer/devcontainer.json --no-lockfile
# Record returned containerId; use that actual identity in subsequent commands.
devcontainer exec --workspace-folder /home/dev/work/PulsePlate --container-id <observed-container-id> bash
```

`up` processes the existing Node feature; raw `make dc-up` does not. CLI/Compose
source guidance is feasibility only: actual generated composition must retain
`native_sdk: service:native-sdk-artifacts`, Linux amd64, build-secret references,
zero replicas for the artifact service and the existing venv mount. CLI source
supports feature additional contexts with Compose >=2.17
([upstream Compose adapter](https://github.com/devcontainers/cli/blob/main/src/spec-node/dockerCompose.ts)); the installed version,
resolved native Compose composition and genuine build/bootstrap still need remote proof.
Preserve failures and route foreign foundation defects to their owner.

Inside that SAME selected container (user `vscode`, workspace `/workspaces/PulsePlate`):

```bash
id -un
hostname
pwd
git rev-parse HEAD
python3 --version
node --version
npm --version
bash scripts/devcontainer/smoke.sh
make devcontainer-bootstrap
make verify-env
```

The #2477 recipe consumes admitted offline wheelhouse/native SDK into a real
venv; source inspection is not a successful remote run. Record exact versions,
resolved feature/image and host/container identity. Never borrow another
container's smoke/CI proof. Keep Docker management on the host; no socket/home
mount enters this container.

From the LOCAL Codex controller, send remote repository-validation/Git-mutation
commands explicitly through SSH and selected-container exec:

```bash
ssh pulseplate-rdev01 '/home/dev/.local/bin/devcontainer exec --workspace-folder /home/dev/work/PulsePlate --container-id <observed-container-id> make verify-env'
```

Record local-controller identity separately from remote host/container
user/cwd/material/shell PID/parent and a harmless ignored artifact. Never capture
full argv/environ. SSH echo/host execution alone is not selected-container proof;
bind actual command, frozen material and returned terminal result to the same run. See [runtime skills](CODEX_SKILLS.md#remote-vm-and-devcontainer-runtime).

## Linked worktrees and hooks

The primary clone's `.git` must be visible within the workspace mount. Create
linked worktrees from the container, below its stable workspace path, using the
ordinary governed starter and a separately selected branch name. Run Git/hooks
for those worktrees inside the container. A host/Mac-created worktree can contain
an absolute `.git` pointer that the container cannot resolve; opening only that
worktree does not fix the common-directory mount. Conversely, container-created
worktrees can point to absolute `/workspaces/...` paths unavailable to host Git.
The LOCAL controller remains local; nested-worktree commands/status/Git mutations
and hooks use explicit SSH/selected-container exec. Optional remote Codex there
needs its own skills/auth. No required remote project, host path alias/Git extension
or promise of managed desktop child-worktree parity; that behavior is unverified.

Inside the selected linked worktree, check:

```bash
git rev-parse --show-toplevel
git rev-parse --git-common-dir
git status --short
git config --show-origin --get core.hooksPath
```

No configured hooksPath is an expected diagnostic no-match, not a failed gate.
Still prove real pre-commit/pre-push execution through the existing hook contract.
The resolver can fall back to the primary clone's venv. A valid Git backlink does
not establish dependency parity: compare the actual Python version, dependency
recipes, complete selected runtime/dev locks and constraints before sharing.
Current runtime4df and candidateea40 differ, so that fallback cannot supply
candidate proof. Use the candidate's own canonical environment instead:

```bash
# INSIDE the reviewed candidate worktree; its own Makefile/locks own this install.
RDEV_WORKSPACE="$(git rev-parse --show-toplevel)"
test ! -L "$RDEV_WORKSPACE/.venv"
RDEV_CANDIDATE_PYTHON="$RDEV_WORKSPACE/.venv/bin/python"
export PULSEPLATE_PYTHON_INDEX_URL=https://packages.pulseplate.app/root/pulseplate/+simple/
unset PULSEPLATE_PYTHON_TRUSTED_HOST PULSEPLATE_BOOTSTRAP_WHEELHOUSE PULSEPLATE_PSYCOPG_C_SDK
make venv VENV_PYTHON="$RDEV_CANDIDATE_PYTHON" DEV_PYTHON="$RDEV_CANDIDATE_PYTHON"
"$RDEV_CANDIDATE_PYTHON" -c 'import sys; from pathlib import Path; assert Path(sys.prefix) == Path.cwd() / ".venv"; print(sys.executable, sys.prefix, sys.version)'
"$RDEV_CANDIDATE_PYTHON" -m pip check
make verify-env VENV_PYTHON="$RDEV_CANDIDATE_PYTHON" DEV_PYTHON="$RDEV_CANDIDATE_PYTHON"
"$RDEV_CANDIDATE_PYTHON" -m pre_commit --version
```

This is the exactea40 recipe; after a foundation merge reread its canonical
SDK/bootstrap contract before changing runtime selectors. Retain own locked
package/version/implementation proof as well as sys.prefix and verify-env.
Do not overwrite an unexpected existing venv, permanently export an interpreter
override, copy a Mac/foreign venv or borrow another branch's successful checks.
Primary sharing is usable only after the comparison establishes actual parity.
Preserve common-directory and admin backlink evidence. Nested worktrees remain
ignored and absent from `git ls-files worktrees`.

## Synthetic backend and same-origin web preview

Use synthetic development data only. Do not copy a production `.env` or source
the entire example: its default `postgres` hostname has no database service in
the selected development-container composition. First select the absolute
workspace whose HEAD, separate I/W inventory, Vite config and dependency locks
match the reviewed snapshot. For current RDEV acceptance this is the received
candidate worktree; the runtime-only primary4df clone lacks the new proxy.
Use the primary path only when it itself contains the exact admitted candidate
material. Compare the identity/hash output below with the frozen receiver receipt
before starting either process; a mismatch stops preview.

After successful own bootstrap, run backend in one selected container terminal
with explicit local-only SQLite and no provider credentials:

```bash
set -euo pipefail
RDEV_WORKSPACE=/workspaces/PulsePlate/worktrees/REPLACE-RECEIVER
cd "$RDEV_WORKSPACE"
test "$(git rev-parse --show-toplevel)" = "$RDEV_WORKSPACE"
git rev-parse HEAD
git status --short
sha256sum frontend/vite.config.ts frontend/package.json frontend/package-lock.json
RDEV_CANDIDATE_PYTHON="$RDEV_WORKSPACE/.venv/bin/python"
test -x "$RDEV_CANDIDATE_PYTHON"
export PATH="$RDEV_WORKSPACE/.venv/bin:$PATH"
"$RDEV_CANDIDATE_PYTHON" -c 'import sys; from pathlib import Path; assert Path(sys.prefix) == Path.cwd() / ".venv"; print(sys.executable)'
# This fresh-clone example refuses an existing dotenv file; inspect any existing
# local configuration separately before selecting a different startup context.
test ! -e .env
mkdir -p cache
export APP_ENV=local ENVIRONMENT=local
export DATABASE_URL=sqlite:///./cache/rdev01.db
export SUBSCRIPTION_DB_ENABLED=false PRIVATE_EXPORTS_ENABLED=false
export FOOD_UPDATE_SCHEDULER_MODE=disabled
export SERVER_SALT="$(python -c 'import secrets; print(secrets.token_hex(32))')"
make dev VENV_PYTHON="$RDEV_CANDIDATE_PYTHON" DEV_PYTHON="$RDEV_CANDIDATE_PYTHON"
```

Do not print/persist the generated salt in public evidence; this is a dedicated
local synthetic environment. Keep real LLM/billing/provider credentials absent.
Observe startup/liveness errors rather than weakening production invariants.
SQLite here is local development only. In a second container terminal:

```bash
set -euo pipefail
RDEV_WORKSPACE=/workspaces/PulsePlate/worktrees/REPLACE-RECEIVER
RDEV_NODE_BIN=/REPLACE-VERIFIED-NODE-24.18.1-BIN
cd "$RDEV_WORKSPACE"
test "$(git rev-parse --show-toplevel)" = "$RDEV_WORKSPACE"
git rev-parse HEAD
git status --short
sha256sum frontend/vite.config.ts frontend/package.json frontend/package-lock.json
test -x "$RDEV_NODE_BIN/node"
export PATH="$RDEV_WORKSPACE/.venv/bin:$RDEV_NODE_BIN:$PATH"
test "$(node --version)" = v24.18.1
make frontend-install
VITE_API_BASE=/api/v1 ./scripts/frontend_npm.sh --prefix frontend run dev -- --mode remote --host 0.0.0.0 --port 5173 --strictPort
```

Only **development serve in mode remote**, explicitly excluding preview, enables
the Vite proxy. It forwards canonical `/api/v1` and descendants unchanged to
`http://127.0.0.1:8001` inside the same container. `/api/v10` and non-API paths do
not match. Default dev, build, test and `preview --mode remote` retain their
existing behavior. The target is fixed, with no rewrite, WS, auth injection or
external redirect following. The backend retains auth/error/entitlement authority.

## Explicit private SSH preview and local iOS Simulator

Before a tunnel, inspect ONLY the actual selected container's identity, Compose
labels, `NetworkSettings.Networks`, mounts and `PortBindings`, excluding Config.Env.
Use rootful Linux Docker bridge reachability: require one unambiguous owned
network/address and prove host access to its backend/web listeners. Do not select
an arbitrary first network. No Docker host-published ports, host networking or
socket mount is allowed; backend/Vite bind `0.0.0.0` INSIDE the container so the
host can reach the bridge address. CLI `forwardPorts` does not create SSH tunnels.

On the Mac, after recording that current bridge IP, verifying host identity and
checking that both selected local ports are free:

```bash
RDEV_CONTAINER_IP=<observed-selected-container-bridge-IPv4>
ssh -N -T -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -L "127.0.0.1:18001:${RDEV_CONTAINER_IP}:8001" -L "127.0.0.1:15173:${RDEV_CONTAINER_IP}:5173" pulseplate-rdev01
```

All local binds are explicit loopback. `ExitOnForwardFailure` detects bind errors,
not upstream health. Occupied local ports fail; do not attach to/stop another
owner's listener. Close OLD tunnels before container recreation, then refresh
container/network/IP identity and host reachability before opening new ones;
an old bridge IP can be reassigned. SSH host keys remain strictly verified and
agent forwarding disabled. Ambiguous addressing stops this dependent stage.

Open `http://127.0.0.1:15173` in the Mac browser and inspect a synthetic same-origin
`/api/v1` request: expected JSON 200/422/envelope and no CORS error. A served Vite
page is insufficient. Local **18001** is backend diagnostics. Local 8000/8001
remain occupied by the protected Surreal extension; do not stop it or route
PulsePlate into those listeners. Current iOS Debug `BASE_URL` in
`ios/PulsePlate/Info-Debug.plist:6` uses 8000, and `AppConfig` prefers that bundle
value before scheme environment. A web check at the new ports cannot prove
Simulator integration. Keep that obligation open for a separately admitted
Debug-only solution; Release HTTPS truth and physical-iPhone scope are unchanged.

Backend liveness `/health` and DB-aware `/ready` remain distinct. Existing
`scripts/smoke.sh` is limited diagnostic output, not complete envelope proof.

From the Mac, after verifying the actual private web forward uses local 15173,
run this bounded same-origin transport check. It uses no API credentials:

```bash
python3 - <<'PY'
import json
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

opener = build_opener(ProxyHandler({}))
for path, payload, expected in [
    ("/api/v1/health", None, 200),
    ("/api/v1/bmi/calculate", {}, 422),
]:
    request = Request(
        "http://127.0.0.1:15173" + path,
        data=None if payload is None else json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        response = opener.open(request, timeout=5)
    except HTTPError as error:
        response = error
    with response:
        assert response.status == expected, (path, response.status)
        assert response.headers.get_content_type() == "application/json"
        body = json.load(response)
    if expected == 422:
        assert isinstance(body.get("detail"), list) and body["detail"]
        assert all("loc" in item and "msg" in item and "type" in item for item in body["detail"])
    print(path, expected, "application/json")
PY
```

On the Mac inspect the selected loopback listeners with `lsof` and separately
probe the owned VM public IPv4 and IPv6 (when present) on **8000/8001/5173** with
bounded connections, for example `nc -vz -G 3 <owned-VM-address> 8001`. All public
preview ports must refuse while private intended flow works. Refusal and timeout
remain distinct; a timeout alone leaves visibility unknown. UFW state alone is
not Docker isolation proof. No public tunnel, reverse proxy, DNS or broad scan.

## Dirty checks, persistent runs and reconnect

Declare each check's real input view: W, I or committed HEAD. Dirty snapshots use
explicit focused commands covering admitted material; retain actual targets/counts,
stdout/stderr and terminal exit after inspecting the actual checkout's recipe.
`make validate-changed` currently selects committed merge-base..HEAD and can select
no tests at HEAD==main despite dirty/staged files. Exit0 is not dirty validation.
Canonical committed-branch narrow gates/current-head CI remain separate mandatory
lifecycle evidence. No synthetic commit to trigger selection, no Linux pytest
substitute for required native Apple checks.

Real native pre-commit against reproduced I proves I, not unstaged W. A consumer
requiring W through its index path uses a separately declared OWNED DISPOSABLE
W-index validation view, preserving original receiver I/W and Mac index. Bind
result to that projection, never original I; do not fake `PRE_COMMIT`/CI flags.
For example, docs leakage guard reads its real pre-commit index context or
committed HEAD otherwise; direct pytest is not automatically dirty-doc proof.

Use existing SSH/tmux and simple private ignored run files. Fresh reviewed runID
identifies exact nonsecret command/cwd/input view/material/runtime/container and
started process. Separate stdout/stderr and terminal exit belong to that run;
`mkdir` collision stops. Launch ONCE, without a dispatcher or reusable job helper.

```bash
# REMOTE host: task-owned private parent already exists.
# Use a dedicated fail-fast subshell; no failed admission reaches tmux.
(
set -euo pipefail
umask 077
RDEV_RUN_ID="REPLACE-FRESH-REVIEWED-RUN-ID"
RDEV_CONTAINER_ID="REPLACE-OBSERVED-CONTAINER-ID"
[[ "$RDEV_RUN_ID" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]]
test "$(id -un)" = dev
RDEV_HOST_UID="$(id -u)"
RDEV_RUN_ROOT=/home/dev/work/PulsePlate/artifacts/orchestration/rdev01-runs
for RDEV_PARENT in /home /home/dev /home/dev/work /home/dev/work/PulsePlate \
  /home/dev/work/PulsePlate/artifacts /home/dev/work/PulsePlate/artifacts/orchestration "$RDEV_RUN_ROOT"; do
  test ! -L "$RDEV_PARENT"
  test -d "$RDEV_PARENT"
  test -x "$RDEV_PARENT"
done
test -O "$RDEV_RUN_ROOT"
test "$(stat -c '%a' "$RDEV_RUN_ROOT")" = 700
RDEV_GUEST_UID="$(/home/dev/.local/bin/devcontainer exec --workspace-folder /home/dev/work/PulsePlate --container-id "$RDEV_CONTAINER_ID" bash -c 'set -e; test "$(id -un)" = vscode; id -u')"
test "$RDEV_GUEST_UID" = "$RDEV_HOST_UID"
RDEV_RUN_DIR="$RDEV_RUN_ROOT/$RDEV_RUN_ID"
RDEV_GUEST_RUN_DIR="/workspaces/PulsePlate/artifacts/orchestration/rdev01-runs/$RDEV_RUN_ID"
if ! mkdir "$RDEV_RUN_DIR"; then
  printf '%s\n' 'Run directory collision or creation failure; no task launched.' >&2
  exit 1
fi
test -O "$RDEV_RUN_DIR"
test "$(stat -c '%a' "$RDEV_RUN_DIR")" = 700
/home/dev/.local/bin/devcontainer exec --workspace-folder /home/dev/work/PulsePlate --container-id "$RDEV_CONTAINER_ID" bash -c '
  set -euo pipefail
  umask 077
  test "$(id -un)" = vscode
  test "$(id -u)" = "$2"
  for parent in /workspaces /workspaces/PulsePlate /workspaces/PulsePlate/artifacts \
    /workspaces/PulsePlate/artifacts/orchestration /workspaces/PulsePlate/artifacts/orchestration/rdev01-runs "$1"; do
    test ! -L "$parent"
    test -d "$parent"
    test -x "$parent"
  done
  test -O "$1"
  test "$(stat -c '%a' "$1")" = 700
  (set -C; printf "%s\n" rdev01-private-access > "$1/access-probe")
  test ! -L "$1/access-probe"
  test -f "$1/access-probe"
  test "$(stat -c '%a' "$1/access-probe")" = 600
' bash "$RDEV_GUEST_RUN_DIR" "$RDEV_HOST_UID"
test ! -L "$RDEV_RUN_DIR/access-probe"
test -f "$RDEV_RUN_DIR/access-probe"
test -O "$RDEV_RUN_DIR/access-probe"
test -r "$RDEV_RUN_DIR/access-probe"
test "$(stat -c '%a' "$RDEV_RUN_DIR/access-probe")" = 600
IFS= read -r RDEV_ACCESS_PROOF < "$RDEV_RUN_DIR/access-probe"
test "$RDEV_ACCESS_PROOF" = rdev01-private-access
tmux new -s "$RDEV_RUN_ID"
)
```

The observed installation has host dev UID 1001 and container vscode UID 1001;
that matching setup is real prior proof, not a guarantee from `adduser` or a
username. The initial admission checks actual numeric identity and both mount
paths, then retains a private exclusive guest-write/host-read marker before any
job. A UID/access/parent mismatch stops without launch or permission repair.
Any partial new directory remains evidence to inspect; never reuse it or alter
an existing run. Ownership repairs require separate bounded admission, with no
recursive chown/chmod or broader permissions. The marker is nonsecret run metadata.

In that tmux shell set the SAME run directory and record command/metadata before
launch. This illustrates the existing native transport-focused command on the
selected W receiver; replace identities/paths after verification. Other surfaces
need their own admitted focused command, not blindly this example.

```bash
set -euo pipefail
# Replace these values with the SAME verified run/container/receiver identities.
RDEV_RUN_ID="REPLACE-SAME-RUN-ID"
RDEV_CONTAINER_ID="REPLACE-OBSERVED-CONTAINER-ID"
RDEV_RUN_DIR="/home/dev/work/PulsePlate/artifacts/orchestration/rdev01-runs/$RDEV_RUN_ID"
RDEV_GUEST_RUN_DIR="/workspaces/PulsePlate/artifacts/orchestration/rdev01-runs/$RDEV_RUN_ID"
RDEV_RECEIVER="/workspaces/PulsePlate/worktrees/REPLACE-OWNED-RECEIVER"
if /home/dev/.local/bin/devcontainer exec --workspace-folder /home/dev/work/PulsePlate --container-id "$RDEV_CONTAINER_ID" bash -lc '
  set -euo pipefail
  RDEV_GUEST_RUN_DIR="$1"
  RDEV_RECEIVER="$2"
  test -d "$RDEV_GUEST_RUN_DIR"
  cd "$RDEV_RECEIVER"
  if ./scripts/frontend_npm.sh --prefix frontend run test:precommit -- src/config/__tests__/remoteDevelopmentProxy.test.ts src/api/__tests__/thin-client-guards.test.ts --no-cache --configLoader runner >"$RDEV_GUEST_RUN_DIR/stdout.log" 2>"$RDEV_GUEST_RUN_DIR/stderr.log"; then
    RDEV_GUEST_EXIT=0
  else
    RDEV_GUEST_EXIT=$?
  fi
  printf "%s\n" "$RDEV_GUEST_EXIT" >"$RDEV_GUEST_RUN_DIR/guest-exit-code"
  exit "$RDEV_GUEST_EXIT"
' bash "$RDEV_GUEST_RUN_DIR" "$RDEV_RECEIVER" >"$RDEV_RUN_DIR/launcher-stdout.log" 2>"$RDEV_RUN_DIR/launcher-stderr.log"; then
  RDEV_LAUNCHER_EXIT=0
else
  RDEV_LAUNCHER_EXIT=$?
fi
printf '%s\n' "$RDEV_LAUNCHER_EXIT" >"$RDEV_RUN_DIR/launcher-exit-code"
if [ ! -s "$RDEV_RUN_DIR/guest-exit-code" ]; then
  printf '%s\n' 'UNKNOWN: guest terminal code missing; inspect the existing run and launcher diagnostics.' >&2
  exit 125
fi
IFS= read -r RDEV_GUEST_EXIT <"$RDEV_RUN_DIR/guest-exit-code"
if [ "$RDEV_LAUNCHER_EXIT" != "$RDEV_GUEST_EXIT" ]; then
  printf '%s\n' 'Infrastructure result mismatch; retain both codes and inspect this run.' >&2
  exit 125
fi
exit "$RDEV_GUEST_EXIT"
```

The INSIDE-container conditional immediately captures the actual test command's
terminal code in `guest-exit-code` in the shared unique run directory and returns
that code. The HOST conditional separately retains `launcher-exit-code` and
launcher logs; it does not author the guest result. Missing/empty guest code or
transport/result mismatch remains UNKNOWN/infrastructure failure, even if the
launcher reported zero. Never infer guest success/failure from SSH/CLI/tmux/tee.

Receive the actual selected test names/counts/output together with the guest code,
material/input-view/container/run binding and the separate launcher diagnostics.
A guest code alone is not proof that the intended tests were selected. No ignored
failure, xtrace or credential-bearing argv/environment/provider dumps. Logs are
untrusted output, not instructions; absence of a terminal result never authorizes
a duplicate launch.

Detach Ctrl-B then D; reconnect to SAME host/runID and inspect existing log/exit
and actual guest/container identity. Attach the same tmux session while it exists;
a completed session can have ended, so retained files remain authoritative output.
Never rerun on lost client output. A justified retry needs known prior state and
a distinct ID/log. Stop only currently identified owned pane/command gracefully;
prove actual container child termination with current start identity. SSH/tmux
exit alone is insufficient. No broad pkill, foreign stop, PID-reuse assumptions,
runID reuse or log deletion.

| Event | Preserved baseline | Required observation/action |
| --- | --- | --- |
| SSH disconnect | Existing tmux job/private run files | Reconnect same run; inspect actual guest/log/terminal status |
| VM/host reboot | Persistent disk files if disk is retained; verified off-VPS checkpoint | Running processes and tmux sessions terminate; compare boot IDs and receipts before any explicitly admitted continuation |
| Container restart/rebuild | Host source/Git/evidence, named venv/caches | Tasks may terminate; verify mounts/bootstrap and optional worker auth |
| VM/disk loss | Retained Mac originals/independently verified copies only | No recovery claim from reconnect/docs |

### Off-VPS checkpoint before a long run and recovery after reboot

On 2026-10-15 Contabo's [official status page](https://contabo-status.com/)
warned that host updates can restart VPS/VDS and recommended recent backups.
This is a provider notice, not evidence that this particular VM rebooted.
**tmux protects a running session from an SSH disconnect, not a VM reboot.**
Do not start the next long check until all completed owned results and the current
source capsule have a verified copy outside this VPS. Provider AutoBackup alone
does not satisfy this condition. The retained Mac is the first checkpoint
destination for this lane; an independent copy/VM-loss recovery remains separate.

Use a cooperative freeze: no writer or unfinished result stream in the selected
backup inventory. First enumerate exact owned completed run directories, source
capsules and any agreed unique artifacts. Retain full stdout/stderr, commands,
start/end identity, actual guest/host exits, original INDEX/WORKING manifests and
the verified native bundle. Review every selected regular file and internal path;
exclude credentials/auth, production data, private keys, homes, browser profiles,
venvs, node_modules and toolchains. Unexpected symlinks, special files, unfinished
streams or changes during the copy stop the dependent long run.

Transfer through strict SSH into a fresh private Mac directory. This native
example requires a reviewed NUL-delimited list of exact relative owned paths;
do not substitute a whole home directory, broad wildcard or two-way sync:

```bash
# MAC: source freeze and reviewed completed-run inventory already established.
set -euo pipefail
umask 077
RDEV_BACKUP="$HOME/.codex/artifacts/rdev01/REPLACE-FRESH-OFF-VPS-CHECKPOINT"
RDEV_BACKUP_LIST=/REPLACE-REVIEWED-NUL-PATH-LIST
test ! -e "$RDEV_BACKUP" && test ! -L "$RDEV_BACKUP"
mkdir "$RDEV_BACKUP"
rsync -rtp --from0 --files-from="$RDEV_BACKUP_LIST" \
  pulseplate-rdev01:/home/dev/work/PulsePlate/artifacts/orchestration/ "$RDEV_BACKUP/"
```

At both ends compare the complete selected inventory, bytes, modes and SHA-256
for every file, not just archive size or rsync exit0. Verify the copied bundle
natively on the Mac and check all seven original I/W source states still match
the frozen source. Preserve the before/after inventories, both-end equality and
copy exit in a separate private receipt. A partial/failed/unverified copy leaves
the long run pending; never rerun it on the Mac as a fallback. Keep originals.

Before launching a new admitted run, store current host boot identity and exact
container/image/material/command in its existing unique run directory:

```bash
# REMOTE HOST: same already-created, owned run directory.
cat /proc/sys/kernel/random/boot_id > "$RDEV_RUN_DIR/host-boot-id.before"
date -u +%FT%TZ > "$RDEV_RUN_DIR/host-observed-utc"
```

Retain immediate per-phase guest exits and separate launcher exits as the phase
completes. Copy completed checkpoints off VPS before another long phase. Files
outside the container layer survive an ordinary reboot only if the persistent
disk remains intact; that is different from process survival or VM-loss recovery.

After reconnect, read the current boot ID before attaching or launching anything.
If it changed, consider the old tmux/process identity dead. Reinspect Docker
state, mounts, actual container UID, source I/W, own dependency environment and
network address. Do not trust an old bridge IP, PID, open-tunnel endpoint or
"running" marker. This lane has no automatic restart service or retry dispatcher.
If the container is stopped, its restart requires a separately admitted bounded
action; no third CLI up or build is implied by this recovery procedure.

Classify each old phase independently. A matching terminal receipt plus unchanged
material/runtime/input identities preserves that completed result within its
actual scope. A missing receipt remains **UNKNOWN / REBOOT_INTERRUPTED** even if
the preceding log looked successful; never manufacture exit0 or a timeout code.
Partial outputs are diagnostic only. Resume only under explicit coordinator
admission, in a new unique run ID linked to the old one, starting at the first
unfinished phase. Reuse completed phases only after their identity/receipt
verification; do not replay side effects or incomplete installations blindly.
Boot drift during a new run invalidates an unqualified success claim. Preserve
all interrupted evidence and complete the off-VPS checkpoint before the next
long launch. No forced reboot test or destructive cleanup is authorized here.

PRIMARY local Codex state stays on Mac. Optional remote host/container skills/auth
have distinct persistence; container home is not implicitly mounted. Preserve
unique outputs before later admitted recreation. No prune/down-v/volume deletion,
broad local cleanup or application removal is authorized.

Return to retained hash-checked Mac work through reviewed source transfer, without
silently executing Linux-heavy tasks locally. Preserve I/W, unique files/run
records, Apple dependencies/signing and foreign worktrees. Stops/deletions require
their exact admitted action; this writer revision executes none.

## Bounded resource observation and validation

Initially allow one heavy command at a time. Record a bounded scenario's UTC
start/end, exact SHA/container identity, Codex/backend/web process placement and
focused test command/input view. On the VM host capture selected `vmstat 1 10`, `free -h`
and `df -h /home/dev/work` observations; retain CPU steal as well as busy time.
Use selected-container `docker stats --no-stream` and only its OOM/restart/state
fields before/after. Record cgroup memory limits/events when available. An
unavailable counter is unknown, not zero. Keep 25–30% disk free as the operating
target; a shared-vCPU specification does not prove representative capacity.

On the Mac retain Xcode/one Simulator, Apple checkout/dependencies and installed
application UIs. Compare before/after with the same source SHA, Xcode/SDK,
selected Apple command and equivalent indexing/cache state: Activity Monitor
Memory Pressure/UI responsiveness, `vm_stat` compressor and `sysctl vm.swapusage`
trends, wall-clock build/test time and disk headroom. Cumulative swap counters,
a cold-versus-warm build or SSH success do not prove improvement. Record which
local Docker/backend/web/Linux-agent duplicates are absent and their observed
remote replacements. Linux RAM does not increase the Mac's local 16 GiB.

Stopping proven owned duplicates follows actual offload/integrity acceptance and
an exact scoped action; no local stop, application removal or cache cleanup is
currently authorized. Stopping Docker does not reclaim its disk image. Retain
unique volumes/files, originals, signing material and foreign worktrees. No full
local `make verify` is authorized by moving development to a VM.

Compound acceptance is ONE observed scenario: permitted benign LOCAL Mac
Computer Use action/tool/result, exact-current-material remote container focused
check, true returned terminal result/counts, and corresponding heavy Mac-process
absence during that bounded interval. Observe local tool availability without
permission changes; retain local Codex/UI/Apple processes honestly. SSH echo, idle
RAM or documentation CI proves neither this conjunction nor universal absence.

The own PR required bundle remains scoped preflight, agent consistency, focused
checks, `make validate-changed`, all-files pre-commit and current-head CI. For the
transport change run the meaningful native Vite tests, thin-client guards and
frontend build/typecheck. Actual-diff premortem and the admitted zero-network
Experiment Runner remain required before PR open; a new VM does not itself
admit strict Runner isolation. Follow ordinary post-open roles, exact-material
self-review, provider-neutral seal/mapping and strict readiness. Purchase,
operational acceptance and exact-head merge stay separate decisions.

## Acceptance evidence

Review reference is the original `RDEV01.acceptance.v1` plus the explicit owner
revision `RDEV01.owner-decision.d1823604.20261015.v1` and latest execution
`RDEV01.owner-execution.56e898f1.20261016.v1`; the table preserves every
original obligation with the revised execution placement and additive Apple proof.
Each row needs its own exact command, raw bounded result, exit code, SHA and
observation identity. Missing evidence remains unknown. Native localhost tests
prove the bounded proxy transport only; they do not achieve remote criteria.

| ID | Accepted outcome | Evidence required | Current outcome |
| --- | --- | --- | --- |
| RD01-01 | One reproducible runbook, exact versions, start/stop | LOCAL Codex/CU plus explicit SSH/CLI rehearsal and local Apple boundaries | not achieved; post-open recipe corrections are written, targeted native rehearsal remains pending; no third CLI up |
| RD01-02 | Code and agreed unique data on VM, SHA/integrity matched | Branch/base/HEAD plus both-end I/W/new/deleted bytes/modes and retained Apple checkout | unknown |
| RD01-03 | Manual bootstrap, verify-env and Python/Node/tooling smoke pass | Genuine container bootstrap/tooling plus dirty-focused checks/input views; committed gate separately | achieved for the bounded selected setup reviewed by QA: manual runtime bootstrap plus separate own-candidate env/tooling; no foreign-lock or full CLI-success claim |
| RD01-04 | Codex command bound to remote host/container/process/path/artifact | LOCAL Mac control plus SSH/container process/material/run/result; optional remote CLI only | unknown |
| RD01-05 | Backend 8001/web 5173 private preview, no public access | Owner port revision: LOCAL 18001/15173 to unchanged container ports; browser/API, loopback listeners, no PortBindings and public visibility. Original Simulator integration remains separately pending | unknown; earlier web 200/422/browser component observed, public timeouts/IPv6 and original Simulator integration remain unresolved |
| RD01-06 | Short tmux task and files survive reconnect | Same unique runID/log/actual exit/guest process after reconnect and owned stop proof | unknown; persisted same-run component reported, exact retained launch-close/fresh-read trace still needed; no reboot-survival inference |
| RD01-07 | Bounded Codex/backend/web/tests CPU/RAM/SSD/OOM/restart and Mac comparison | Real remote check/local heavy-process absence plus comparable Xcode/Simulator pressure/swap/build-time/UI | unknown |
| RD01-08 | Verified return to retained Mac work; rebuild behavior described | Retained originals/hash comparison and return rehearsal | achieved for bounded retained-work return reviewed by QA: original I/W, returned results, native bundle and C0 ferry; not VM-loss/destructive restore |
| RD01-09 | Own local/CI/Oracle/review/mapping gates on current material | Exact input-view/selection/terminal proof plus committed/current-head gates and separate merge approval | not achieved; C0 local/metadata-Oracle/publication components observed, three post-open roles complete; changed-material gates, terminal current-head CI and final closeout pending |
| RD01-10 | Runbook/ledger/PR body/existing Drive/Tracker/capsule agree | Same-ID updates preserving history/ACL/parents/unrelated content and raw readback | not achieved; published-C0 five-ID factual checkpoint read back, this correction and final lifecycle/continuity remain pending |

Keep [the RDEV ledger](../roadmap/BACKLOG_LEDGER.md#ledger-p1-rdev01-remote-development)
open until every original criterion is individually achieved. If the PR merges
first, use `PR_MERGED / REMOTE_ACCEPTANCE_PENDING`. Update the existing INFRA
master, operational plan, capsule and Tracker IDs; do not create replacement
documents when authorization/readback fails. Retain originals/evidence until
archive hash, extraction/recovery and owned cleanup are proven.

Carryover [#2474](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2474)
merged on 2026-10-07 as `3920d9a5c437fdb3e2bcf2694f1ce8efdfd01eb5`. That receipt
corrects repository bookkeeping only. Remaining OPS-04B operational evidence and
parent OPS-04 remain open; RDEV-01 grants no production/FinOps/restore outcome.

## Future services and portable recovery: planning only

Current [OPS-04B](../roadmap/BACKLOG_LEDGER.md#ledger-p1-ops04b-utilization-recovery-evidence)
and [INFRA/OPS-04](../roadmap/BACKLOG_LEDGER.md#ledger-p1-ops04-storage-finops)
own future capacity/recovery admission. A GitHub repository is not a recoverable
application if its database, user assets or DigitalOcean private index/devpi is
lost. Provider backup IDs/timestamps, same-datacenter snapshots and root-disk
capacities do not prove portable off-provider or attached-Volume recovery.

A later admitted lane must inventory portable devpi state/configuration/artifacts,
DB/application assets and approved secret recovery outside DigitalOcean, preserve
the private-proxy/offline SDK-wheelhouse contract and test isolated service restore
with DigitalOcean unavailable. No public PyPI fallback follows from an outage.
Any encrypted development-VPS copy is ADDITIONAL, never the sole independent copy;
keep decryption/account recovery outside both DO and development host. No plaintext
production/devpi data enters agent/Docker-administrator workspaces here.

Future WordPress needs separately admitted capacity/publication/isolation and
both database and selected `wp-content`/site-file recovery. Public plugins, agent
builds and backup plaintext cannot silently share a development Docker-root trust
boundary. Size selected used data, retained copy generations and temporary restore
space with the 25–30% free margin, not the sum of provider disk capacities. These
are existing-ledger follow-ups only: no WordPress install/public ports/DNS,
production backup/restore/transfer, new epic or purchase is implemented here.
