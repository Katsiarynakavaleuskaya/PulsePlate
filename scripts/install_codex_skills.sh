#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Install PulsePlate and cybersecurity Codex skills from this repo into a Codex skills directory.

Usage:
  scripts/install_codex_skills.sh [--copy] [--unlink] [--list] [--dest <skills_dir>] [--no-cybersec|--only-cybersec]

Options:
  --copy            Install by copying directories (default is symlink mode).
  --unlink          Remove installed skills from destination.
  --list            Print source skills and destination install status.
  --dest <path>     Destination skills directory (default: $CODEX_HOME/skills or ~/.codex/skills).
  --no-cybersec     Install only PulsePlate skills (skip cybersecurity skills).
  --only-cybersec   Install only cybersecurity skills (skip PulsePlate skills).
  -h, --help        Show this help.

Examples:
  scripts/install_codex_skills.sh
  scripts/install_codex_skills.sh --copy
  scripts/install_codex_skills.sh --no-cybersec --list
  scripts/install_codex_skills.sh --only-cybersec
  scripts/install_codex_skills.sh --list
  scripts/install_codex_skills.sh --unlink
  scripts/install_codex_skills.sh --dest /tmp/codex-skills
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COPY_MARKER_FILE=".pulseplate_codex_skill_source"

CODEX_HOME_DEFAULT="${CODEX_HOME:-${HOME}/.codex}"
DEST_ROOT="${CODEX_HOME_DEFAULT}/skills"
MODE="link"
ACTION="install"
CYBERSEC_MODE="both"

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
    --no-cybersec)
      CYBERSEC_MODE="exclude"
      shift
      ;;
    --only-cybersec)
      CYBERSEC_MODE="only"
      shift
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

# Build SKILLS_SRC_ROOTS based on CYBERSEC_MODE
SKILLS_SRC_ROOTS=()
case "${CYBERSEC_MODE}" in
  both)
    SKILLS_SRC_ROOTS=(
      "${REPO_ROOT}/tools/codex_skills"
      "${REPO_ROOT}/tools/cybersecurity_skills/skills"
    )
    ;;
  exclude)
    SKILLS_SRC_ROOTS=("${REPO_ROOT}/tools/codex_skills")
    ;;
  only)
    SKILLS_SRC_ROOTS=("${REPO_ROOT}/tools/cybersecurity_skills/skills")
    ;;
  *)
    echo "Error: invalid CYBERSEC_MODE ${CYBERSEC_MODE}" >&2
    exit 1
    ;;
esac

SKILL_DIRS=()
for root in "${SKILLS_SRC_ROOTS[@]}"; do
  if [[ ! -d "${root}" ]]; then
    echo "Note: skipping missing source ${root} (run: git submodule update --init)" >&2
    continue
  fi
  while IFS= read -r src_dir; do
    SKILL_DIRS+=("${src_dir}")
  done < <(find "${root}" -mindepth 1 -maxdepth 1 -type d | sort)
done

if [[ "${#SKILL_DIRS[@]}" -eq 0 ]]; then
  echo "Error: no skill directories found. Check tools/codex_skills and tools/cybersecurity_skills (git submodule update --init)." >&2
  exit 1
fi

list_skills() {
  local sources_str=""
  for r in "${SKILLS_SRC_ROOTS[@]}"; do
    [[ -n "${sources_str}" ]] && sources_str="${sources_str}, "
    sources_str="${sources_str}${r#${REPO_ROOT}/}"
  done
  echo "Sources: ${sources_str}"
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
      local linked_target
      linked_target="$(readlink "${dest_dir}")"
      if [[ "${linked_target}" == "${src_dir}" ]]; then
        status="linked(managed) -> ${linked_target}"
      else
        status="linked(external) -> ${linked_target}"
      fi
    elif [[ -d "${dest_dir}" ]]; then
      if [[ -f "${dest_dir}/${COPY_MARKER_FILE}" ]]; then
        status="copied(managed)"
      else
        status="copied(external)"
      fi
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
      printf '%s\n' "${src_dir}" > "${dest_dir}/${COPY_MARKER_FILE}"
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
      local linked_target
      linked_target="$(readlink "${dest_dir}")"
      if [[ "${linked_target}" == "${src_dir}" ]]; then
        rm "${dest_dir}"
        echo "Unlinked: ${skill_name}"
      else
        echo "Skip external symlink for ${skill_name}: ${linked_target}" >&2
      fi
      continue
    fi

    if [[ -d "${dest_dir}" && -f "${dest_dir}/SKILL.md" ]]; then
      if [[ -f "${dest_dir}/${COPY_MARKER_FILE}" ]]; then
        local marker_source
        marker_source="$(cat "${dest_dir}/${COPY_MARKER_FILE}")"
        if [[ "${marker_source}" == "${src_dir}" ]]; then
          rm -rf "${dest_dir}"
          echo "Removed copied skill: ${skill_name}"
        else
          echo "Skip external copied skill for ${skill_name}: ${dest_dir}" >&2
        fi
      else
        echo "Skip unmarked copied skill for ${skill_name}: ${dest_dir}" >&2
      fi
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
