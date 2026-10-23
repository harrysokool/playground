#!/usr/bin/env bash
# Diagnosis comment detection with Azure OpenAI (prompt v2 + --diagnosis), on Azure ML compute.
#
#   git pull --ff-only && bash python/receipt_ocr_benchmark/scripts/aoai_diagnosis_on_azure.sh [--no-push]
#
# No Azure DI calls: the saved DI responses are reused. Azure OpenAI calls: 9 (Version 2) + 4 (Version 1
# receipts 1, 2, 3, 5; their photos and DI responses come from tag ocr-benchmark-v1 into a temporary folder).
# A run folder that already exists is skipped, so running again repeats no call. Then all approaches are
# scored against data/diagnosis/ground_truth.csv (separate from the six-field scores) and committed.
set -euo pipefail
PUSH=1
[ "${1:-}" = "--no-push" ] && PUSH=0

ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT/python/receipt_ocr_benchmark"
D=results/diagnosis
# shellcheck disable=SC1090
source ~/venvs/paddle322/bin/activate
python -m pytest -q --deselect tests/test_paddle_engine.py::test_paddle_engine_processes_receipt

run() {  # run <output dir> <input dir> <saved DI responses>
  if [ -d "$1" ]; then echo "Skip (exists): $1"; return 0; fi
  python -m receipt_bench.di_aoai --diagnosis --input "$2" --output "$1" --reuse-di "$3"
}

run $D/v2/aoai_v2_rows data/receipts_v2/benchmark_inputs results/v2/di_aoai/di_response

TAG=$(mktemp -d)
trap 'rm -rf "$TAG"' EXIT
git -C "$ROOT" archive ocr-benchmark-v1:python/receipt_ocr_benchmark data/raw results/di_aoai/di_response | tar -x -C "$TAG"
mkdir -p "$TAG/v1"
for i in 1 2 3 5; do cp "$TAG"/data/raw/receipt$i.* "$TAG/v1/"; done
run $D/v1/aoai_v2_rows "$TAG/v1" "$TAG/results/di_aoai/di_response"

python -m receipt_bench.diagnosis_cli score --ground-truth data/diagnosis/ground_truth.csv \
  --approach rules_paddle_light=v2:$D/v2/rules_paddle_light --approach rules_paddle_light=v1:$D/v1/rules_paddle_light \
  --approach rules_azure_di=v2:$D/v2/rules_azure_di --approach rules_azure_di=v1:$D/v1/rules_azure_di \
  --approach aoai_v2=v2:$D/v2/aoai_v2_rows --approach aoai_v2=v1:$D/v1/aoai_v2_rows \
  --output-dir $D/scores
head -12 $D/scores/report.md

git add $D
if git diff --cached --quiet -- $D; then echo "Nothing new to commit."; else
  git commit -m "Diagnosis comment detection: AOAI prompt v2 results" -- $D
fi
[ "$PUSH" -eq 1 ] && git push
echo "Done."
