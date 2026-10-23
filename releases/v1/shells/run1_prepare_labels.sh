#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd -- "$repo_root"
export CDR_ENTRYPOINT="releases/v1/shells/run1_prepare_labels.sh"
export MKL_THREADING_LAYER="${MKL_THREADING_LAYER:-GNU}"
export VLLM_WORKER_MULTIPROC_METHOD="${VLLM_WORKER_MULTIPROC_METHOD:-spawn}"
source "$repo_root/shells/common/select_label_model.sh"
select_label_model "$@"
label_python="${PYTHON:-}"
if [[ -z "$label_python" ]]; then
  if [[ "$LABEL_BACKEND" == vllm && -x "${CDR_VENV:-$repo_root/.venv}/bin/python" ]]; then
    label_python="${CDR_VENV:-$repo_root/.venv}/bin/python"
  else
    label_python=python
  fi
fi
if [[ "$LABEL_MODEL" == all_vllm_models ]]; then
  # Each model gets a fresh session/process group; never load two models together.
  command -v setsid >/dev/null || { echo 'all_vllm_models requires setsid.' >&2; exit 2; }
  forwarded=()
  source_prefix=v1_run1_labels
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --model|--backend) shift 2 ;;
      --model=*|--backend=*) shift ;;
      --source-id) source_prefix="$2"; shift 2 ;;
      --source-id=*) source_prefix="${1#*=}"; shift ;;
      *) forwarded+=("$1"); shift ;;
    esac
  done
  model_pid=''
  cleanup_model() {
    if [[ -n "$model_pid" ]]; then
      # The parent has exited normally; remove any orphaned GPU workers too.
      kill -KILL -- "-$model_pid" 2>/dev/null || true
      wait "$model_pid" 2>/dev/null || true
      model_pid=''
    fi
  }
  trap cleanup_model EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM
  failed_models=0
  for model_index in "${!VLLM_MODELS[@]}"; do
    model="${VLLM_MODELS[model_index]}"
    model_slug="${model//\//_}"
    printf 'Running vLLM model %d/%d: %s\n' "$((model_index + 1))" "${#VLLM_MODELS[@]}" "$model" >&2
    setsid "$label_python" "$repo_root/releases/v1/scripts/prepare_labels.py" \
      --root "$repo_root" --catalog-version v1 --sample-source v1_run1_samples \
      "${forwarded[@]}" --source-id "${source_prefix}_${model_slug}" --backend vllm --model "$model" &
    model_pid=$!
    model_status=0
    wait "$model_pid" || model_status=$?
    cleanup_model
    if [[ "$model_status" -ne 0 ]]; then
      printf 'Model failed (exit %d): %s\n' "$model_status" "$model" >&2
      failed_models=$((failed_models + 1))
    fi
  done
  printf 'All vLLM models finished; failed models: %d\n' "$failed_models" >&2
  [[ "$failed_models" -eq 0 ]]
  exit
fi
exec "$label_python" "$repo_root/releases/v1/scripts/prepare_labels.py" \
  --root "$repo_root" --catalog-version v1 \
  --sample-source v1_run1_samples --source-id v1_run1_labels "${LABEL_MODEL_ARGS[@]}" "$@"
