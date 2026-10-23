#!/usr/bin/env bash
# Source this file, then call select_label_model "$@".
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/models.sh"

select_label_model() {
  LABEL_MODEL_ARGS=()
  LABEL_BACKEND=''
  LABEL_MODEL=''
  local arg next='' has_help=false
  for arg in "$@"; do
    if [[ -n "$next" ]]; then
      case "$next" in
        backend) LABEL_BACKEND="$arg" ;;
        model) LABEL_MODEL="$arg" ;;
      esac
      next=''
      continue
    fi
    case "$arg" in
      --backend) next=backend ;;
      --model) next=model ;;
      --backend=*) LABEL_BACKEND="${arg#*=}" ;;
      --model=*) LABEL_MODEL="${arg#*=}" ;;
      --help|-h) has_help=true ;;
    esac
  done
  if [[ "$has_help" == true ]]; then return; fi
  if [[ -n "$next" ]]; then
    printf 'Missing value for --%s\n' "$next" >&2
    return 2
  fi
  if [[ -n "$LABEL_BACKEND" && "$LABEL_BACKEND" != openai && "$LABEL_BACKEND" != vllm ]]; then
    echo 'Backend must be openai or vllm.' >&2
    return 2
  fi
  if [[ -n "$LABEL_MODEL" ]]; then
    if [[ -z "$LABEL_BACKEND" ]]; then
      local candidate
      for candidate in "${API_MODELS[@]}"; do
        if [[ "$candidate" == "$LABEL_MODEL" ]]; then LABEL_BACKEND=openai; fi
      done
      for candidate in "${VLLM_MODELS[@]}"; do
        if [[ "$candidate" == "$LABEL_MODEL" && -z "$LABEL_BACKEND" ]]; then LABEL_BACKEND=vllm; fi
      done
      if [[ -z "$LABEL_BACKEND" ]]; then
        echo 'For an unlisted model, also supply --backend openai|vllm.' >&2
        return 2
      fi
      LABEL_MODEL_ARGS+=(--backend "$LABEL_BACKEND")
    fi
    return
  fi
  local models=() backends=() candidate index choice
  if [[ -z "$LABEL_BACKEND" || "$LABEL_BACKEND" == openai ]]; then
    for candidate in "${API_MODELS[@]}"; do models+=("$candidate"); backends+=(openai); done
  fi
  if [[ -z "$LABEL_BACKEND" || "$LABEL_BACKEND" == vllm ]]; then
    for candidate in "${VLLM_MODELS[@]}"; do models+=("$candidate"); backends+=(vllm); done
  fi
  if [[ ${#models[@]} -eq 0 ]]; then echo 'No configured models for this backend.' >&2; return 2; fi
  choice=1
  if [[ -t 0 ]]; then
    echo 'Select a labeling model:' >&2
    for index in "${!models[@]}"; do
      printf '  %d) [%s] %s\n' "$((index + 1))" "${backends[index]}" "${models[index]}" >&2
    done
    while true; do
      read -r -p 'Model [1]: ' choice || return 2
      choice="${choice:-1}"
      if [[ "$choice" =~ ^[0-9]+$ && ${#choice} -le 5 ]] && (( 10#$choice >= 1 && 10#$choice <= ${#models[@]} )); then break; fi
      echo 'Enter one of the listed numbers.' >&2
    done
  fi
  index=$((10#$choice - 1))
  LABEL_BACKEND="${backends[index]}"
  LABEL_MODEL="${models[index]}"
  LABEL_MODEL_ARGS=(--backend "$LABEL_BACKEND" --model "$LABEL_MODEL")
  printf 'Labeling model: [%s] %s\n' "$LABEL_BACKEND" "$LABEL_MODEL" >&2
}
