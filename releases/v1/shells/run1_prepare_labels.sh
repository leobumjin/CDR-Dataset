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
exec "$label_python" "$repo_root/releases/v1/scripts/prepare_labels.py" \
  --root "$repo_root" --catalog-version v1 \
  --sample-source v1_run1_samples --source-id v1_run1_labels "${LABEL_MODEL_ARGS[@]}" "$@"
