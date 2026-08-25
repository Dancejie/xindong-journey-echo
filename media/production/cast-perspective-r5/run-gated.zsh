#!/bin/zsh
set -euo pipefail

SCRIPT_DIR=${0:A:h}
VALIDATOR="$SCRIPT_DIR/validate_batch_gate.py"

usage() {
  print -u2 -- "Usage:"
  print -u2 -- "  $0 --template-check"
  print -u2 -- "  $0 --validate-only --manifest FILE --approval FILE [--matrix FILE]"
  print -u2 -- "  $0 --execute --manifest FILE --approval FILE --output-dir .work-candidates/DIR [--matrix FILE]"
  print -u2 -- ""
  print -u2 -- "--execute additionally requires FUMIN_API_KEY, FUMIN_BASE_URL,"
  print -u2 -- "CONFIRM_PAID_BATCH_ID and a reviewed doNotSubmit=false approval."
}

mode=""
manifest=""
approval=""
matrix="$SCRIPT_DIR/task-matrix.json"
output_dir=""

while (( $# > 0 )); do
  case "$1" in
    --template-check|--validate-only|--execute)
      [[ -z "$mode" ]] || { print -u2 -- "Choose exactly one mode."; exit 2; }
      mode="$1"
      shift
      ;;
    --manifest)
      (( $# >= 2 )) || { usage; exit 2; }
      manifest="$2"
      shift 2
      ;;
    --approval)
      (( $# >= 2 )) || { usage; exit 2; }
      approval="$2"
      shift 2
      ;;
    --matrix)
      (( $# >= 2 )) || { usage; exit 2; }
      matrix="$2"
      shift 2
      ;;
    --output-dir)
      (( $# >= 2 )) || { usage; exit 2; }
      output_dir="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      print -u2 -- "Unknown argument: $1"
      usage
      exit 2
      ;;
  esac
done

[[ -n "$mode" ]] || { usage; exit 2; }

if [[ "$mode" == "--template-check" ]]; then
  python3 "$VALIDATOR" --template-check
  exit $?
fi

[[ -n "$manifest" && -n "$approval" ]] || { usage; exit 2; }
manifest=${manifest:A}
approval=${approval:A}
matrix=${matrix:A}

if [[ "$mode" == "--validate-only" ]]; then
  python3 "$VALIDATOR" --manifest "$manifest" --approval "$approval" --matrix "$matrix"
  exit $?
fi

[[ -n "$output_dir" ]] || { print -u2 -- "--execute requires --output-dir."; exit 2; }
output_dir=${output_dir:A}
if [[ "${output_dir:h:t}" != ".work-candidates" && "$output_dir" != */.work-candidates/* ]]; then
  print -u2 -- "Output must be a specifically named child of a .work-candidates directory."
  exit 2
fi

python3 "$VALIDATOR" \
  --manifest "$manifest" \
  --approval "$approval" \
  --matrix "$matrix" \
  --require-executable-approval

batch_id=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["planId"])' "$manifest")
if [[ "${CONFIRM_PAID_BATCH_ID:-}" != "$batch_id" ]]; then
  print -u2 -- "Paid execution blocked: set CONFIRM_PAID_BATCH_ID exactly to $batch_id after approval."
  exit 3
fi
[[ -n "${FUMIN_API_KEY:-}" ]] || { print -u2 -- "FUMIN_API_KEY is not set; no request made."; exit 3; }
[[ -n "${FUMIN_BASE_URL:-}" ]] || { print -u2 -- "FUMIN_BASE_URL is not set; no request made."; exit 3; }
if [[ -n "${FUMIN_MODEL:-}" && "$FUMIN_MODEL" != "seedance-2.0-mini" ]]; then
  print -u2 -- "FUMIN_MODEL must be exactly seedance-2.0-mini; no request made."
  exit 3
fi

client=${FUMIN_BATCH_CLIENT:-}
[[ -n "$client" ]] || { print -u2 -- "FUMIN_BATCH_CLIENT must point to the reviewed provider adapter; no request made."; exit 3; }
[[ -f "$client" ]] || { print -u2 -- "FUMIN batch client not found: $client; no request made."; exit 3; }

# Prove adapter compatibility locally before the provider model probe and paid calls.
FUMIN_MODEL="seedance-2.0-mini" python3 "$client" "$manifest" --concurrency 2 --validate-only

print -- "Paid gate passed for $batch_id. Starting exactly 178 semantic-master tasks at concurrency=2; API retry remains 0."
# A shared FUMIN_IMAGE_URL would silently replace every per-shot identity board,
# so remove it explicitly and force the reviewed local, hashed reference_image paths.
env -u FUMIN_IMAGE_URL FUMIN_MODEL="seedance-2.0-mini" \
  python3 "$client" "$manifest" \
    --output-dir "$output_dir" \
    --concurrency 2 \
    --poll-seconds 8 \
    --timeout-seconds 2400
