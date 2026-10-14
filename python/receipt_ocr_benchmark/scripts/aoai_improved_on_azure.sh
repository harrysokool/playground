#!/usr/bin/env bash
# Evaluate the improved Azure DI + AOAI pipeline on Azure ML compute, in one command.
#
#   bash python/receipt_ocr_benchmark/scripts/aoai_improved_on_azure.sh     (from anywhere in the repository)
#
# Needs the usual managed-identity settings (AZURE_CLIENT_ID, AZURE_DI_ENDPOINT, AZURE_OPENAI_ENDPOINT,
# AZURE_OPENAI_DEPLOYMENT). No Azure DI calls: every run reuses the DI responses the original AOAI run
# saved, so only the extraction step changes. Azure OpenAI calls: 9 + 9 + 9 (Version 2) + 6 (Version 1)
# = 33, about 1-2k tokens each.
#
# Never overwrites the original results (results/v2/di_aoai, results/v2/scores_improved): it stops if
# an output folder already exists.
#
# Runs:
#   v2_rows        the improved pipeline (prompt v2, row layout, validation)      -> the result to report
#   v2_plain       prompt v2 + validation on the original plain text              -> how much the layout helps
#   v2_rows_image  the improved pipeline + the receipt photo (experiment)          -> can the photo fix OCR misreads
#   Version 1      the improved pipeline on the 6 Version 1 receipts; receipts 1, 2, 3 and 5 were never used
#                  to design the changes (4 and 6 are Version 2 receipts 9 and 10)
# Then scores everything with the current scorer, checks the scorer change left every original score
# unchanged, and commits and pushes the new results.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)/python/receipt_ocr_benchmark"
git pull --ff-only
# shellcheck disable=SC1090
source ~/venvs/paddle322/bin/activate

OUT=results/v2
V1=results/v1_heldout
for d in $OUT/di_aoai_v2_rows $OUT/di_aoai_v2_plain $OUT/di_aoai_v2_rows_image $OUT/scores_aoai_improved $V1; do
  [ -e "$d" ] && { echo "Stopping: $d already exists (results are never overwritten)."; exit 1; }
done

# 1. Tests (the PaddleOCR smoke test is skipped: no OCR is run here)
python -m pytest -q --deselect tests/test_paddle_engine.py::test_paddle_engine_processes_receipt

# 2. Version 2: the three runs, all reusing the saved DI responses
IN=data/receipts_v2/benchmark_inputs
DI=$OUT/di_aoai/di_response
python -m receipt_bench.di_aoai --input $IN --reuse-di $DI --output $OUT/di_aoai_v2_rows
python -m receipt_bench.di_aoai --input $IN --reuse-di $DI --output $OUT/di_aoai_v2_plain --text plain
if python -c "import PIL" 2>/dev/null; then
  python -m receipt_bench.di_aoai --input $IN --reuse-di $DI --output $OUT/di_aoai_v2_rows_image --attach-image
else
  echo "Pillow is not installed: skipping the photo experiment."
fi

# 3. Score with the current scorer. First the original seven results again, to show the scorer change
#    altered none of them; then the original AOAI next to the new runs and the improved rules.
GT=data/receipts_v2/benchmark_ground_truth.xlsx
CHECK=$(mktemp -d)
python -m receipt_bench.score --ground-truth $GT \
  --approach paddle_light_general=$OUT/extracted_general_light --approach paddle_light_improved=$OUT/extracted_improved_light \
  --approach paddle_heavy_general=$OUT/extracted_general_heavy --approach paddle_heavy_improved=$OUT/extracted_improved_heavy \
  --approach azure_di_general=$OUT/extracted_general_azure_di --approach azure_di_improved=$OUT/extracted_improved_azure_di \
  --approach azure_di_aoai=$OUT/di_aoai --output-dir "$CHECK" >/dev/null
if diff <(cut -d, -f1-4 $OUT/scores_improved/summary.csv) <(cut -d, -f1-4 "$CHECK/summary.csv"); then
  echo "Scorer check: all seven original scores are unchanged."
else
  echo "Scorer check: the scorer change altered an original score (see the diff above)."
fi
APPROACHES=(--approach paddle_light_improved=$OUT/extracted_improved_light
            --approach azure_di_improved=$OUT/extracted_improved_azure_di
            --approach aoai_original=$OUT/di_aoai --approach aoai_v2_rows=$OUT/di_aoai_v2_rows
            --approach aoai_v2_plain=$OUT/di_aoai_v2_plain)
[ -d $OUT/di_aoai_v2_rows_image ] && APPROACHES+=(--approach aoai_v2_rows_image=$OUT/di_aoai_v2_rows_image)
python -m receipt_bench.score --ground-truth $GT "${APPROACHES[@]}" --output-dir $OUT/scores_aoai_improved >/dev/null
head -25 $OUT/scores_aoai_improved/report.md
cp "$CHECK/summary.csv" $OUT/scores_aoai_improved/scorer_check_summary.csv

# 4. Version 1 receipts (held out): the original AOAI results and saved DI responses from the v1 tag.
#    The photos are extracted to a temporary folder, not into the repository.
TAG=$(mktemp -d)
git archive ocr-benchmark-v1:python/receipt_ocr_benchmark data/raw results/di_aoai | tar -x -C "$TAG"
mkdir -p $V1
cp -r "$TAG/results/di_aoai" $V1/di_aoai_original
python -m receipt_bench.di_aoai --input "$TAG/data/raw" --reuse-di "$TAG/results/di_aoai/di_response" --output $V1/di_aoai_v2_rows
python -m receipt_bench.score --ground-truth data/ground_truth/ground_truth_template.xlsx \
  --approach aoai_original=$V1/di_aoai_original --approach aoai_v2_rows=$V1/di_aoai_v2_rows \
  --output-dir $V1/scores >/dev/null
head -14 $V1/scores/report.md
rm -rf "$TAG" "$CHECK"

# 5. Commit and push the new results only
git add $OUT/di_aoai_v2_rows $OUT/di_aoai_v2_plain $OUT/scores_aoai_improved $V1
[ -d $OUT/di_aoai_v2_rows_image ] && git add $OUT/di_aoai_v2_rows_image
git commit -m "DI + AOAI improved pipeline: results on Version 2 and held-out Version 1 receipts"
git push
echo "Done: results pushed."
