#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd -- "$repo_root"
export CDR_ENTRYPOINT="releases/v1/shells/run1_prepare_samples.sh"
exec "${PYTHON:-python}" "$repo_root/releases/v1/scripts/prepare_samples.py" \
  --root "$repo_root" --catalog-version v1 --source-id v1_run1_samples "$@"
