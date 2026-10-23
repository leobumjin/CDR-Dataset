#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
RETRACTION_ROOT="$PROJECT_ROOT"
RETRACTION_VENV="${CDR_VENV:-$PROJECT_ROOT/.venv}"
RETRACTION_PYTHON="$RETRACTION_VENV/bin/python"
DATA_PYTHON="${DATA_PYTHON:-python3}"

RECREATE=0
DRY_RUN="${DRY_RUN:-false}"
CHECK_ONLY=false

usage() {
  cat <<'EOF'
Usage: bash tools/setup_vllm.sh [--recreate] [--dry-run] [--check]
  default: install the pinned B200 CUDA 12.8 runtime into RETRACTION_VENV
  --recreate: replace the isolated venv before installation
  --dry-run: print commands without changing the environment
  --check: validate RETRACTION_PYTHON without installing packages
EOF
}
for arg in "$@"; do
  case "${arg}" in
    --recreate) RECREATE=1 ;;
    --dry-run) DRY_RUN=true ;;
    --check) CHECK_ONLY=true ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 64 ;;
  esac
done
case "${DRY_RUN}" in true|false) ;; *) echo "DRY_RUN must be true or false" >&2; exit 64 ;; esac

run_command() {
  if [[ "${DRY_RUN}" == true ]]; then
    printf '%q ' "$@"
    printf '\n'
  else
    "$@"
  fi
}

runtime_check='
from importlib.metadata import version
expected = {"vllm": "0.11.0", "transformers": "4.57.6"}
for package, required in expected.items():
    actual = version(package)
    if actual != required:
        raise SystemExit(f"{package} version mismatch: expected {required}, found {actual}")
    print(package, actual)
import torch
if torch.version.cuda != "12.8":
    raise SystemExit(f"Expected CUDA 12.8 PyTorch runtime, found {torch.version.cuda}")
print("torch", version("torch"), "CUDA", torch.version.cuda)
'

if [[ "${CHECK_ONLY}" == true ]]; then
  if [[ "${DRY_RUN}" != true && ! -x "${RETRACTION_PYTHON}" ]]; then
    echo "Runtime missing: ${RETRACTION_PYTHON}. Run bash tools/setup_vllm.sh first." >&2
    exit 66
  fi
  run_command "${RETRACTION_PYTHON}" -c "${runtime_check}"
  exit 0
fi

if [[ -L "${RETRACTION_VENV}" || ( -e "${RETRACTION_VENV}" && ! -f "${RETRACTION_VENV}/pyvenv.cfg" ) ]]; then
  echo "Not an isolated virtual environment: ${RETRACTION_VENV}" >&2
  exit 64
fi

if [[ "${RECREATE}" -eq 1 && -e "${RETRACTION_VENV}" ]]; then
  case "${RETRACTION_VENV}" in
    ""|/|.|"${RETRACTION_ROOT}") echo "Refusing unsafe venv removal: ${RETRACTION_VENV}" >&2; exit 64 ;;
  esac
  run_command rm -rf "${RETRACTION_VENV}"
fi

needs_venv=false
if [[ "${RECREATE}" -eq 1 || ! -x "${RETRACTION_PYTHON}" ]]; then
  needs_venv=true
fi
if [[ "${needs_venv}" == true ]]; then
  if command -v uv >/dev/null 2>&1; then
    run_command uv venv "${RETRACTION_VENV}" --python 3.12 --managed-python --seed
  else
    command -v "${DATA_PYTHON}" >/dev/null 2>&1 || {
      echo "Python not found: ${DATA_PYTHON}" >&2
      exit 66
    }
    run_command "${DATA_PYTHON}" -c \
      'import sys; assert (3, 11) <= sys.version_info[:2] <= (3, 12), "Use Python 3.11/3.12 or install uv"'
    run_command "${DATA_PYTHON}" -m venv "${RETRACTION_VENV}"
  fi
fi
run_command "${RETRACTION_PYTHON}" -c \
  'import sys; assert (3, 11) <= sys.version_info[:2] <= (3, 12), "Pinned runtime requires Python 3.11/3.12"'

if command -v uv >/dev/null 2>&1; then
  run_command uv pip install --python "${RETRACTION_PYTHON}" --torch-backend=cu128 \
    -r "${PROJECT_ROOT}/requirements-vllm.txt"
else
  run_command "${RETRACTION_PYTHON}" -m pip install --upgrade pip
  run_command "${RETRACTION_PYTHON}" -m pip install \
    --extra-index-url https://download.pytorch.org/whl/cu128 \
    -r "${PROJECT_ROOT}/requirements-vllm.txt"
fi
run_command "${RETRACTION_PYTHON}" -m pip check
run_command "${RETRACTION_PYTHON}" -c "${runtime_check}"
echo "ready: ${RETRACTION_VENV}"

