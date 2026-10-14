#!/usr/bin/env bash
# Evaluate the improved Azure DI + AOAI pipeline on Azure ML compute. Safe to run again: every step that
# already finished is skipped, so no Azure OpenAI call is repeated.
#
#   bash python/receipt_ocr_benchmark/scripts/aoai_improved_on_azure.sh [--no-v1] [--no-push]
#
#   --no-v1    skip the Version 1 held-out run (e.g. to commit the Version 2 results on their own)
#   --no-push  commit, but do not push
#
# Needs the usual managed-identity settings (AZURE_CLIENT_ID, AZURE_DI_ENDPOINT, AZURE_OPENAI_ENDPOINT,
# AZURE_OPENAI_DEPLOYMENT). No Azure DI calls: every run reuses the DI responses saved by the original
# AOAI runs, so only the extraction step changes. Azure OpenAI calls when nothing has run yet:
# 9 + 9 + 9 (Version 2) + 6 (Version 1).
#
# Steps (each skipped when its output is already complete):
#   1. tests; check the original results are untouched and still score exactly as recorded (else STOP)
#   2. Version 2 runs: v2_rows (the improved pipeline), v2_plain (without the row layout),
#      v2_rows_image (with the receipt photo)
#   3. Version 2 scores -> results/v2/scores_aoai_improved/; commit (and push) the Version 2 results
#   4. Version 1 held-out run (optional; skipped with a message if the Version 1 photos are not
#      available); score; commit (and push) them separately
#
# Never overwrites or deletes results. A run folder that exists but is incomplete (a receipt missing or
# failed) stops the script with instructions; move it aside yourself and run again.
set -euo pipefail
RUN_V1=1 PUSH=1
for arg in "$@"; do
  case $arg in
    --no-v1) RUN_V1=0 ;;
    --no-push) PUSH=0 ;;
    *) echo "Unknown option: $arg (use --no-v1 / --no-push)"; exit 2 ;;
  esac
done

ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT/python/receipt_ocr_benchmark"
OUT=results/v2
V1=results/v1_heldout
GT=data/receipts_v2/benchmark_ground_truth.xlsx
IMAGES='\.(png|jpe?g|tiff?|bmp|pdf)$'

stop() { echo "STOP: $*" >&2; exit 1; }

# Git lock files: never removed here. A lock left behind by a crashed git command blocks commits.
check_git_locks() {
  local locks
  locks=$(find "$ROOT/.git" -maxdepth 1 -name "*.lock" 2>/dev/null || true)
  [ -z "$locks" ] && return 0
  if pgrep -x git >/dev/null; then
    stop "git lock file(s) present while another git process is running: $locks. Wait for it to finish, then run again."
  fi
  stop "git lock file(s) present and no git process is running: $locks
Check nothing else is using this repository (another terminal, VS Code, a Jupyter git extension), then
remove only those files, e.g.: rm $locks"
}

# Number of receipt images in a folder.
n_inputs() { find "$1" -maxdepth 1 -type f | grep -Eic "$IMAGES" || true; }

# Runs the DI + AOAI pipeline into $out unless it has already completed. A complete run has one
# receipt JSON per input image, all with status "ok".
run_aoai() {
  local out=$1 input=$2 expected n ok; shift 2
  expected=$(n_inputs "$input")
  if [ -d "$out" ]; then
    n=$(( $(find "$out" -maxdepth 1 -name 'receipt*.json' | wc -l) ))
    ok=$(( $(grep -l '"status": "ok"' "$out"/receipt*.json 2>/dev/null | wc -l || true) ))
    if [ "$n" -eq "$expected" ] && [ "$ok" -eq "$expected" ]; then
      echo "Skip (already complete, $ok/$expected ok): $out"
      return 0
    fi
    stop "$out exists but is incomplete ($ok of $expected receipts ok). Results are never overwritten:
move it aside (e.g. mv $out $out.incomplete) and run this script again."
  fi
  python -m receipt_bench.di_aoai --input "$input" --output "$out" "$@"
}

commit_paths() {
  local message=$1; shift
  check_git_locks
  git add -- "$@"
  if git diff --cached --quiet -- "$@"; then
    echo "Nothing new to commit for: $*"
  else
    git commit -m "$message" -- "$@"
  fi
  if [ "$PUSH" -eq 1 ]; then
    git push
  fi
}

# --- 1. checks -----------------------------------------------------------------------------------
check_git_locks
git pull --ff-only
# shellcheck disable=SC1090
source ~/venvs/paddle322/bin/activate
python -m pytest -q --deselect tests/test_paddle_engine.py::test_paddle_engine_processes_receipt

ORIGINALS=($OUT/di_aoai $OUT/scores_improved $OUT/extracted_general_light $OUT/extracted_improved_light
           $OUT/extracted_general_heavy $OUT/extracted_improved_heavy $OUT/extracted_general_azure_di
           $OUT/extracted_improved_azure_di)
if ! git diff --quiet HEAD -- "${ORIGINALS[@]}" || [ -n "$(git ls-files --others --exclude-standard -- "${ORIGINALS[@]}")" ]; then
  git status --short -- "${ORIGINALS[@]}"
  stop "the original benchmark results differ from the committed version (above). Nothing was run."
fi
CHECK=$(mktemp -d)
trap 'rm -rf "$CHECK"' EXIT
python -m receipt_bench.score --ground-truth $GT \
  --approach paddle_light_general=$OUT/extracted_general_light --approach paddle_light_improved=$OUT/extracted_improved_light \
  --approach paddle_heavy_general=$OUT/extracted_general_heavy --approach paddle_heavy_improved=$OUT/extracted_improved_heavy \
  --approach azure_di_general=$OUT/extracted_general_azure_di --approach azure_di_improved=$OUT/extracted_improved_azure_di \
  --approach azure_di_aoai=$OUT/di_aoai --output-dir "$CHECK" >/dev/null
if ! diff <(cut -d, -f1-4 $OUT/scores_improved/summary.csv) <(cut -d, -f1-4 "$CHECK/summary.csv"); then
  stop "rescoring the original results gives different scores (diff above). Nothing more was run."
fi
echo "Scorer check: all seven original scores are unchanged."

# --- 2. Version 2 runs (reuse the saved DI responses) --------------------------------------------
IN=data/receipts_v2/benchmark_inputs
DI=$OUT/di_aoai/di_response
run_aoai $OUT/di_aoai_v2_rows "$IN" --reuse-di $DI
run_aoai $OUT/di_aoai_v2_plain "$IN" --reuse-di $DI --text plain
if [ -d $OUT/di_aoai_v2_rows_image ] || python -c "import PIL" 2>/dev/null; then
  run_aoai $OUT/di_aoai_v2_rows_image "$IN" --reuse-di $DI --attach-image
else
  echo "Pillow is not installed: skipping the photo experiment."
fi

# --- 3. Version 2 scores and commit --------------------------------------------------------------
if [ -d $OUT/scores_aoai_improved ]; then
  echo "Skip (already scored): $OUT/scores_aoai_improved"
else
  APPROACHES=(--approach paddle_light_improved=$OUT/extracted_improved_light
              --approach azure_di_improved=$OUT/extracted_improved_azure_di
              --approach aoai_original=$OUT/di_aoai --approach aoai_v2_rows=$OUT/di_aoai_v2_rows
              --approach aoai_v2_plain=$OUT/di_aoai_v2_plain)
  [ -d $OUT/di_aoai_v2_rows_image ] && APPROACHES+=(--approach aoai_v2_rows_image=$OUT/di_aoai_v2_rows_image)
  python -m receipt_bench.score --ground-truth $GT "${APPROACHES[@]}" --output-dir $OUT/scores_aoai_improved >/dev/null
  cp "$CHECK/summary.csv" $OUT/scores_aoai_improved/scorer_check_summary.csv
fi
head -12 $OUT/scores_aoai_improved/report.md
V2_PATHS=($OUT/di_aoai_v2_rows $OUT/di_aoai_v2_plain $OUT/scores_aoai_improved)
[ -d $OUT/di_aoai_v2_rows_image ] && V2_PATHS+=($OUT/di_aoai_v2_rows_image)
commit_paths "DI + AOAI improved pipeline: Version 2 results" "${V2_PATHS[@]}"

# --- 4. Version 1 held-out receipts (optional) ---------------------------------------------------
# Receipts 1, 2, 3 and 5 were never used to design the changes (4 and 6 are Version 2 receipts 9
# and 10). Their photos, saved DI responses and original AOAI results come from the v1 tag; the
# photos go to a temporary folder, never into the repository.
if [ "$RUN_V1" -eq 0 ]; then
  echo "Version 1 held-out run skipped (--no-v1)."
  exit 0
fi
TAG=$(mktemp -d)
trap 'rm -rf "$CHECK" "$TAG"' EXIT
if ! git -C "$ROOT" archive ocr-benchmark-v1:python/receipt_ocr_benchmark data/raw results/di_aoai \
     > "$TAG/v1.tar" 2>"$TAG/archive.err" || ! tar -x -f "$TAG/v1.tar" -C "$TAG"; then
  echo "Version 1 held-out run skipped: could not read the Version 1 receipts from tag ocr-benchmark-v1:"
  cat "$TAG/archive.err"
  exit 0
fi
if [ "$(n_inputs "$TAG/data/raw")" -eq 0 ] || [ ! -d "$TAG/results/di_aoai/di_response" ]; then
  echo "Version 1 held-out run skipped: the tag has no Version 1 photos or saved DI responses."
  exit 0
fi
mkdir -p $V1
[ -d $V1/di_aoai_original ] || cp -r "$TAG/results/di_aoai" $V1/di_aoai_original
run_aoai $V1/di_aoai_v2_rows "$TAG/data/raw" --reuse-di "$TAG/results/di_aoai/di_response"
if [ -d $V1/scores ]; then
  echo "Skip (already scored): $V1/scores"
else
  python -m receipt_bench.score --ground-truth data/ground_truth/ground_truth_template.xlsx \
    --approach aoai_original=$V1/di_aoai_original --approach aoai_v2_rows=$V1/di_aoai_v2_rows \
    --output-dir $V1/scores >/dev/null
fi
head -10 $V1/scores/report.md
commit_paths "DI + AOAI improved pipeline: held-out Version 1 results" $V1
echo "Done."
