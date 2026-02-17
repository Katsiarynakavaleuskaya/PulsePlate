#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Install PulsePlate Codex skills from this repo into a Codex skills directory.

Usage:
  scripts/install_codex_skills.sh [--copy] [--unlink] [--list] [--dest <skills_dir>]

Options:
  --copy            Install by copying directories (default is symlink mode).
  --unlink          Remove installed skills from destination.
  --list            Print source skills and destination install status.
  --dest <path>     Destination skills directory (default: $CODEX_HOME/skills or ~/.codex/skills).
  -h, --help        Show this help.

Examples:
  scripts/install_codex_skills.sh
  scripts/install_codex_skills.sh --copy
  scripts/install_codex_skills.sh --list
  scripts/install_codex_skills.sh --unlink
  scripts/install_codex_skills.sh --dest /tmp/codex-skills
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SKILLS_SRC_ROOT="${REPO_ROOT}/tools/codex_skills"

CODEX_HOME_DEFAULT="${CODEX_HOME:-${HOME}/.codex}"
DEST_ROOT="${CODEX_HOME_DEFAULT}/skills"
MODE="link"
ACTION="install"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --copy)
      MODE="copy"
      shift
      ;;
    --unlink)
      ACTION="unlink"
      shift
      ;;
    --list)
      ACTION="list"
      shift
      ;;
    --dest)
      if [[ $# -lt 2 ]]; then
        echo "Error: --dest requires a path argument." >&2
        exit 1
      fi
      DEST_ROOT="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Error: unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ ! -d "${SKILLS_SRC_ROOT}" ]]; then
  echo "Error: source skills directory not found: ${SKILLS_SRC_ROOT}" >&2
  exit 1
fi

mapfile -t SKILL_DIRS < <(find "${SKILLS_SRC_ROOT}" -mindepth 1 -maxdepth 1 -type d | sort)
if [[ "${#SKILL_DIRS[@]}" -eq 0 ]]; then
  echo "Error: no skill directories found under ${SKILLS_SRC_ROOT}" >&2
  exit 1
fi

list_skills() {
  echo "Source: ${SKILLS_SRC_ROOT}"
  echo "Destination: ${DEST_ROOT}"
  echo
  printf "%-36s %s\n" "SKILL" "STATUS"
  printf "%-36s %s\n" "-----" "------"
  for src_dir in "${SKILL_DIRS[@]}"; do
    local skill_name
    local dest_dir
    local status
    skill_name="$(basename "${src_dir}")"
    dest_dir="${DEST_ROOT}/${skill_name}"
    if [[ -L "${dest_dir}" ]]; then
      status="linked -> $(readlink "${dest_dir}")"
    elif [[ -d "${dest_dir}" ]]; then
      status="copied"
    else
      status="not installed"
    fi
    printf "%-36s %s\n" "${skill_name}" "${status}"
  done
}

install_skills() {
  mkdir -p "${DEST_ROOT}"
  for src_dir in "${SKILL_DIRS[@]}"; do
    local skill_name
    local dest_dir
    skill_name="$(basename "${src_dir}")"
    dest_dir="${DEST_ROOT}/${skill_name}"

    if [[ ! -f "${src_dir}/SKILL.md" ]]; then
      echo "Skipping ${skill_name}: missing SKILL.md in source." >&2
      continue
    fi

    if [[ -L "${dest_dir}" ]]; then
      local current_target
      current_target="$(readlink "${dest_dir}")"
      if [[ "${current_target}" == "${src_dir}" ]]; then
        echo "Already linked: ${skill_name}"
        continue
      fi
      echo "Error: destination already exists as a different symlink: ${dest_dir}" >&2
      echo "Run with --unlink first or pick another --dest." >&2
      exit 1
    fi

    if [[ -e "${dest_dir}" ]]; then
      echo "Error: destination already exists: ${dest_dir}" >&2
      echo "Run with --unlink first or pick another --dest." >&2
      exit 1
    fi

    if [[ "${MODE}" == "copy" ]]; then
      cp -R "${src_dir}" "${dest_dir}"
      echo "Copied: ${skill_name}"
    else
      ln -s "${src_dir}" "${dest_dir}"
      echo "Linked: ${skill_name}"
    fi
  done
}

unlink_skills() {
  mkdir -p "${DEST_ROOT}"
  for src_dir in "${SKILL_DIRS[@]}"; do
    local skill_name
    local dest_dir
    skill_name="$(basename "${src_dir}")"
    dest_dir="${DEST_ROOT}/${skill_name}"

    if [[ -L "${dest_dir}" ]]; then
      rm "${dest_dir}"
      echo "Unlinked: ${skill_name}"
      continue
    fi

    if [[ -d "${dest_dir}" && -f "${dest_dir}/SKILL.md" ]]; then
      rm -rf "${dest_dir}"
      echo "Removed copied skill: ${skill_name}"
      continue
    fi

    echo "Not installed: ${skill_name}"
  done
}

case "${ACTION}" in
  list)
    list_skills
    ;;
  unlink)
    unlink_skills
    ;;
  install)
    install_skills
    ;;
  *)
    echo "Internal error: unknown action ${ACTION}" >&2
    exit 1
    ;;
esac
