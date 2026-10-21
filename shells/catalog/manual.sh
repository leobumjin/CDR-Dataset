#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd -- "$repo_root"
exec "${PYTHON:-python}" -m src.catalog.manual --root "$repo_root" "$@"
