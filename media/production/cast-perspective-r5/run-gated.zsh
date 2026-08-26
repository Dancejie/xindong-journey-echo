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
  print -u2 -- "--execute is permanently disabled because this R5 plan is archived."
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

print -u2 -- "Paid execution blocked permanently: the 198-job R5 plan is archived. Use the reviewed 480p gender-rotation plan and its CNY 200 manual budget gate instead."
exit 4
