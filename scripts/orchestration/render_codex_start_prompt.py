#!/usr/bin/env python3
"""Render Codex copy-paste startup prompts from repo bootstrap truth."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
DEFAULT_PR_REVIEW_CHECKLIST = (
    "agent-coordinator",
    "architecture-specialist",
    "security-auditor",
    "qa-engineer-agent",
    "bug-hunter",
    "dev-operator",
)
PYTHON_ENV_GUIDANCE = (
    "For local Python gates in the worktree, set `VENV_PYTHON` to an absolute "
    "interpreter path printed by the starter/bootstrap scripts or to another "
    "explicit repo Python, then run Make targets or `$VENV_PYTHON -m pytest ...`; "
    "do not use bare `python3 -m pytest`, relative `.venv/bin/python`, or "
    "`$PWD/.venv/bin/python` in isolated worktrees, because those paths can "
    "miss FastAPI and other locked deps."
)
EXPERIMENT_RUNNER_ENV_GUIDANCE = (
    "For Experiment Runner evidence, use repo Python as "
    "`$VENV_PYTHON scripts/orchestration/experiment_runner.py ...`; if a "
    "non-trivial lane cannot load or write the runner artifact because the "
    "environment misses FastAPI/runtime deps, artifact load/write failures are "
    "infra blockers, not `Not applicable`."
)
ROLE_DISPATCH_GUIDANCE = (
    "Role-agent dispatch is a required post-bootstrap step: copy the packet's "
    "`role_agent_dispatch_contract.dispatch_manifest_command` verbatim, replace "
    "`<packet>` with the actual packet path, use repo Python per RUNBOOK, then "
    "run each `dispatch_sequence` role in order. Do not reconstruct a generic "
    "bridge command, because implementation packets may carry runtime owner "
    "flags. Do not treat task_bootstrap.py packet creation as role-agent execution."
)
POST_OPEN_REVIEW_GUIDANCE = (
    "After the PR opens, run the role-only post-open pass in order: "
    "`qa-engineer-agent -> bug-hunter -> security-auditor`. Fix or disposition "
    "every finding, run the scoped local gates, and confirm current-head checks. "
    "When all material fixes are complete, freeze the exact material with "
    "`pr_review_closeout.py freeze`, then run the repo-native exact-head "
    "`pulseplate-pr-review` as the executable local self-review and disposition "
    "every actual finding. Any material fix invalidates the freeze and returns "
    "to fixes, local/current-head gates, freeze, and self-review. Seal with "
    "`pr_review_closeout.py seal --repo <owner/name> --pr-number <N> "
    "--self-review-report <report.json>` without "
    "review/security provider flags. This authors the exact static provider "
    "no-claim pair (`review_claim=none`, `scan_claim=none`, "
    "`no_findings_claim=false`) and performs no provider invocation, retry, "
    "poll, wait, substitute, operator override, or TTL. Provider absence is not "
    "a PASS, review, scan, approval, or no-findings result. Current-head CI, "
    "the trusted security-check bundle, dispositions, mapping, ancestry, bot "
    "actionables, unresolved threads, and the review wait window remain hard."
)


class PromptError(ValueError):
    """Raised when prompt inputs are invalid."""


def _repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _load_packet(packet_path: Path) -> dict[str, Any]:
    if not packet_path.is_file():
        raise PromptError(f"task packet not found: {_repo_relative(packet_path)}")
    try:
        payload = json.loads(packet_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PromptError(f"task packet is not valid JSON: {_repo_relative(packet_path)}") from exc
    if not isinstance(payload, dict):
        raise PromptError("task packet JSON must be an object")
    return payload


def _as_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def _unique(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _prompt_text(value: object, fallback: str = "") -> str:
    """Render user/packet data as a single prompt data field."""

    text = str(value) if value not in (None, "") else fallback
    return text.replace("\\", "\\\\").replace("\r", "\\r").replace("\n", "\\n").replace("\t", "\\t")


def _shell_quote(value: object, fallback: str = "") -> str:
    """Render user/packet data safely for copy-paste shell commands."""

    return shlex.quote(str(value if value not in (None, "") else fallback))


def _is_packet_placeholder(value: str) -> bool:
    return value.startswith("<") and value.endswith(">") and value[1:-1] == "packet"


def _render_dispatch_command(
    role_dispatch_contract: dict[str, Any],
    *,
    packet_path: str,
) -> str:
    """Render the packet-provided dispatch command with local interpreter guidance."""

    raw_command = str(role_dispatch_contract.get("dispatch_manifest_command", "")).strip()
    if not raw_command:
        raw_command = (
            "python3 scripts/orchestration/role_dispatch_bridge.py " "--packet <packet> --pretty"
        )
    try:
        tokens = shlex.split(raw_command)
    except ValueError:
        tokens = [
            "python3",
            "scripts/orchestration/role_dispatch_bridge.py",
            "--packet",
            "<packet>",
            "--pretty",
        ]

    rendered_tokens: list[str] = []
    for index, token in enumerate(tokens):
        if index == 0 and token in {"python", "python3"}:
            rendered_tokens.append("$VENV_PYTHON")
        elif _is_packet_placeholder(token):
            rendered_tokens.append(_shell_quote(packet_path))
        else:
            rendered_tokens.append(_shell_quote(token))
    return " ".join(rendered_tokens)


def _prompt_list(items: list[str], fallback: str) -> str:
    return ", ".join(_prompt_text(item) for item in items) if items else fallback


def _packet_role_bindings(bridge: dict[str, Any], key: str) -> list[object]:
    value = bridge.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise PromptError(f"native_subagent_bridge.{key} must be a list when present")
    return value


def _packet_role_order(packet: dict[str, Any]) -> list[str]:
    bridge = packet.get("native_subagent_bridge")
    secondary_bindings: list[object] = []
    advisory_bindings: list[object] = []
    if isinstance(bridge, dict):
        secondary_bindings = _packet_role_bindings(bridge, "secondary")
        advisory_bindings = _packet_role_bindings(bridge, "advisory")

        from scripts.orchestration import qoder_dispatch_bridge

        parsed_roles: list[str] = qoder_dispatch_bridge._parse_json_packet_roles(packet)
        if parsed_roles:
            if not qoder_dispatch_bridge._json_payload_requested_order_preserves_mandatory_tail(
                packet
            ):
                parsed_roles = qoder_dispatch_bridge._enforce_mandatory_post_open_order(
                    parsed_roles
                )
            return parsed_roles
    role_order: list[str] = []
    if isinstance(bridge, dict):
        primary = bridge.get("primary")
        if isinstance(primary, dict):
            role_order.extend(_as_string_list([primary.get("repo_agent_slug")]))
        reviewer = bridge.get("reviewer")
        if isinstance(reviewer, dict):
            role_order.extend(_as_string_list([reviewer.get("repo_agent_slug")]))
        for secondary in secondary_bindings:
            if isinstance(secondary, dict):
                role_order.extend(_as_string_list([secondary.get("repo_agent_slug")]))
        for advisory in advisory_bindings:
            if isinstance(advisory, dict):
                role_order.extend(_as_string_list([advisory.get("repo_agent_slug")]))
    if not role_order:
        role_order = [
            *_as_string_list([packet.get("primary_agent")]),
            *_as_string_list([packet.get("reviewer")]),
            *_as_string_list(packet.get("secondary_agents")),
        ]
    return _unique(["agent-coordinator", *role_order])


def _advisory_binding_is_executable(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    slug = str(value.get("repo_agent_slug", "")).strip()
    if not slug:
        return False
    dispatch_contract = value.get("dispatch_contract")
    if not isinstance(dispatch_contract, dict):
        return False
    return not (
        dispatch_contract.get("advisory_only")
        or dispatch_contract.get("spawn_with_native_subagent") is False
    )


def _packet_advisory_roles(packet: dict[str, Any], *, executable: bool) -> list[str]:
    bridge = packet.get("native_subagent_bridge")
    advisory_roles: list[str] = []
    if isinstance(bridge, dict):
        for advisory in _packet_role_bindings(bridge, "advisory"):
            if isinstance(advisory, dict):
                is_executable = _advisory_binding_is_executable(advisory)
                if executable == is_executable:
                    advisory_roles.extend(_as_string_list([advisory.get("repo_agent_slug")]))
    return _unique(advisory_roles)


def _common_prompt_lines(*, mode_note: str) -> list[str]:
    return [
        "Paste into Codex now:",
        "",
        "STOP: do not edit or write code/docs until the coordinator-first step below is complete.",
        "Start with agent-coordinator as the mandatory first role.",
        mode_note,
        "",
    ]


def render_packet_prompt(
    packet: dict[str, Any],
    *,
    packet_path: str,
    branch: str = "",
    worktree: str = "",
) -> str:
    """Render the post-task-bootstrap prompt block."""

    goal = str(packet.get("goal") or "<goal unavailable>")
    task_class = str(packet.get("task_class") or "<task_class unavailable>")
    pr_phase = str(packet.get("pr_phase") or "none")
    candidate_paths = _as_string_list(packet.get("candidate_paths"))
    role_order = _packet_role_order(packet)
    executable_advisory_roles = _packet_advisory_roles(packet, executable=True)
    closure_only_advisory_roles = _packet_advisory_roles(packet, executable=False)
    recommended_skills = _as_string_list(packet.get("recommended_skills"))
    role_dispatch_contract = packet.get("role_agent_dispatch_contract")
    if not isinstance(role_dispatch_contract, dict):
        role_dispatch_contract = {}
    packet_creation_executes_roles = str(
        role_dispatch_contract.get("packet_creation_executes_roles", False)
    ).lower()
    role_agent_dispatch_required = str(
        role_dispatch_contract.get("role_agent_dispatch_required", True)
    ).lower()
    dispatch_command = _render_dispatch_command(
        role_dispatch_contract,
        packet_path=packet_path,
    )

    lines = _common_prompt_lines(
        mode_note=(
            "Authoritative bootstrap already ran; follow the generated task packet before "
            "implementation."
        )
    )
    lines.extend(
        [
            f"Task packet: {_prompt_text(packet_path)}",
            f"Goal: {_prompt_text(goal)}",
            f"Task class: {_prompt_text(task_class)}",
            f"PR phase: {_prompt_text(pr_phase)}",
            f"Branch: {_prompt_text(branch, '<branch unavailable>')}",
            f"Worktree: {_prompt_text(worktree, '<worktree unavailable>')}",
            f"Path scope: {_prompt_list(candidate_paths, '<no explicit paths>')}",
            f"Role order: {_prompt_list(role_order, 'agent-coordinator')}",
            f"Default PR review checklist: {_prompt_list(list(DEFAULT_PR_REVIEW_CHECKLIST), 'agent-coordinator')}",
            f"Executable required custom-role passes: {_prompt_list(executable_advisory_roles, '<none>')}",
            f"Closure-only/no-spawn custom roles still require disposition input: {_prompt_list(closure_only_advisory_roles, '<none>')}",
            f"Passive skills from packet: {_prompt_list(recommended_skills, '<none>')}",
            "",
            "Open the PR non-draft by default so GitHub, CodeRabbit, Cubic, Sourcery, and current-head checks can run; draft requires an explicit operator exception.",
            "Skills are passive/discovery-only; they do not replace agent-coordinator, task_bootstrap.py, review governance, or merge-readiness gates.",
            "Host/Codex preflight is not authoritative lane provenance. Repo custom orchestration remains: check_preflight.py -> task_bootstrap.py -> agent-coordinator.",
            "Experiment Runner joins after coordinator bootstrap as oracle-only evidence; it must not replace agent-coordinator or become the lane-start authority.",
            f"Packet role dispatch contract: packet_creation_executes_roles={packet_creation_executes_roles}; role_agent_dispatch_required={role_agent_dispatch_required}.",
            f"Next role-agent dispatch command: {dispatch_command}",
            ROLE_DISPATCH_GUIDANCE,
            POST_OPEN_REVIEW_GUIDANCE,
            "Experiment Runner evidence: for every non-trivial PR, create oracle-only evidence by default and record `## Experiment Runner Evidence` as `Artifact: artifacts/orchestration/experiments/results/<id>.json`; use `Not applicable: <reason>` only when the runner result is genuinely unused or inapplicable.",
            "Lane start provenance: record `## Lane Start Provenance` with `Packet: artifacts/orchestration/task_packets/<id>.json` or a narrow documented cleanup/emergency `Exception: <reason>`; `Starter: scripts/orchestration/start_pr_lane.sh` is supplemental and cannot be used alone.",
            "Premortem closure rule: every premortem finding must be fixed in code/docs/tests or formally dispositioned as NOT-A-BUG/DEFERRED with evidence/backlog. No finding may be ignored as advisory.",
            PYTHON_ENV_GUIDANCE,
            EXPERIMENT_RUNNER_ENV_GUIDANCE,
            "Then run only the scoped validation bundle required by the lane before any readiness claim.",
        ]
    )
    return "\n".join(lines)


def render_recipe_prompt(
    *,
    goal: str,
    task_class: str,
    pr_phase: str,
    branch: str = "",
    worktree: str = "",
    paths: list[str],
    requested_agents: list[str],
    preflight_ran: bool = True,
) -> str:
    """Render the pre-task-bootstrap helper prompt block."""

    agents = _unique(["agent-coordinator", *requested_agents])
    if preflight_ran:
        mode_note = (
            "This local helper only ran analyze preflight; it did not run authoritative "
            "task_bootstrap.py and did not create a task packet."
        )
    else:
        mode_note = (
            "Dry run only: this command did not run preflight, did not run authoritative "
            "task_bootstrap.py, and did not create a task packet."
        )
    lines = _common_prompt_lines(mode_note=mode_note)
    lines.extend(
        [
            f"Goal: {_prompt_text(goal, '<set --goal>')}",
            f"Task class: {_prompt_text(task_class, '<set --task-class>')}",
            f"PR phase: {_prompt_text(pr_phase)}",
            f"Branch: {_prompt_text(branch, '<branch unavailable>')}",
            f"Worktree: {_prompt_text(worktree, '<worktree unavailable>')}",
            f"Path scope: {_prompt_list(paths, '<no explicit paths>')}",
            f"Requested role order seed: {_prompt_list(agents, 'agent-coordinator')}",
            f"Default PR review checklist: {_prompt_list(list(DEFAULT_PR_REVIEW_CHECKLIST), 'agent-coordinator')}",
            "",
            "Next required repo command: run task_bootstrap.py with the printed arguments, then follow the generated packet.",
            "Open the PR non-draft by default so bot review and current-head checks run; draft requires an explicit operator exception.",
            "Skills are passive/discovery-only; they do not replace agent-coordinator, task_bootstrap.py, review governance, or merge-readiness gates.",
            "Host/Codex preflight is not authoritative lane provenance. Repo custom orchestration remains: check_preflight.py -> task_bootstrap.py -> agent-coordinator.",
            "After task_bootstrap.py returns a packet, copy `role_agent_dispatch_contract.dispatch_manifest_command` verbatim, substitute the actual packet path and repo Python, then execute the manifest `dispatch_sequence` in order.",
            ROLE_DISPATCH_GUIDANCE,
            POST_OPEN_REVIEW_GUIDANCE,
            "After coordinator bootstrap, create oracle-only Experiment Runner evidence by default for non-trivial PRs; the runner joins the lane and must not replace agent-coordinator.",
            "Record `## Experiment Runner Evidence` as `Artifact: artifacts/orchestration/experiments/results/<id>.json`; use `Not applicable: <reason>` only when the runner result is genuinely unused or inapplicable.",
            "Record `## Lane Start Provenance` with `Packet: artifacts/orchestration/task_packets/<id>.json` or a narrow documented cleanup/emergency `Exception: <reason>`; `Starter: scripts/orchestration/start_pr_lane.sh` is supplemental and cannot be used alone.",
            "Premortem closure rule: every premortem finding must be fixed in code/docs/tests or formally dispositioned as NOT-A-BUG/DEFERRED with evidence/backlog. No finding may be ignored as advisory.",
            PYTHON_ENV_GUIDANCE,
            EXPERIMENT_RUNNER_ENV_GUIDANCE,
        ]
    )
    return "\n".join(lines)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render Codex startup prompts for PulsePlate repo bridge scripts."
    )
    subparsers = parser.add_subparsers(dest="mode", required=True)

    packet_parser = subparsers.add_parser("packet")
    packet_parser.add_argument("--packet", required=True)
    packet_parser.add_argument("--branch", default="")
    packet_parser.add_argument("--worktree", default="")

    recipe_parser = subparsers.add_parser("recipe")
    recipe_parser.add_argument("--goal", default="")
    recipe_parser.add_argument("--task-class", default="")
    recipe_parser.add_argument("--pr-phase", default="none")
    recipe_parser.add_argument("--branch", default="")
    recipe_parser.add_argument("--worktree", default="")
    recipe_parser.add_argument("--path", action="append", default=[])
    recipe_parser.add_argument("--requested-agent", action="append", default=[])
    recipe_parser.add_argument("--preflight-ran", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if args.mode == "packet":
            packet_path = Path(args.packet)
            if not packet_path.is_absolute():
                packet_path = REPO_ROOT / packet_path
            packet = _load_packet(packet_path)
            print(
                render_packet_prompt(
                    packet,
                    packet_path=_repo_relative(packet_path),
                    branch=args.branch,
                    worktree=args.worktree,
                )
            )
            return 0
        print(
            render_recipe_prompt(
                goal=args.goal,
                task_class=args.task_class,
                pr_phase=args.pr_phase,
                branch=args.branch,
                worktree=args.worktree,
                paths=args.path,
                requested_agents=args.requested_agent,
                preflight_ran=args.preflight_ran,
            )
        )
        return 0
    except PromptError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
