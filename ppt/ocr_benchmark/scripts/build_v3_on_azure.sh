#!/usr/bin/env bash
# One command to build the Version 3 deck on Azure ML compute, verify it and push it to GitHub.
#
#   bash ppt/ocr_benchmark/scripts/build_v3_on_azure.sh        (from anywhere inside the repository)
#
# 1. pulls the latest code;
# 2. installs python-pptx into the benchmark environment if it is missing;
# 3. generates current/OCR_Benchmark_V3.pptx and the receipt crops in assets_v2/;
# 4. checks the deck against the benchmark results and writes previews/deck_text.md;
# 5. renders a PDF and slide images if LibreOffice is available (optional; they can also be
#    rendered from the pushed deck);
# 6. commits and pushes the deck, crops and previews.
# No OCR and no Azure API calls.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
git pull --ff-only

# shellcheck disable=SC1090
source ~/venvs/paddle322/bin/activate
python3 -c "import pptx" 2>/dev/null || pip install -q python-pptx==1.0.2

python3 ppt/ocr_benchmark/scripts/generate_ppt_v3.py --force
python3 ppt/ocr_benchmark/scripts/check_deck_v3.py

cd ppt/ocr_benchmark
if command -v soffice >/dev/null && command -v pdftoppm >/dev/null; then
  soffice --headless --convert-to pdf --outdir previews current/OCR_Benchmark_V3.pptx >/dev/null
  mv previews/OCR_Benchmark_V3.pdf previews/OCR_Benchmark_V3_preview.pdf
  rm -f previews/slide-*.png
  pdftoppm -png -r 80 previews/OCR_Benchmark_V3_preview.pdf previews/slide
else
  echo "LibreOffice/pdftoppm not available here: skipping the PDF preview (it can be rendered from the pushed deck)."
fi

git add current/OCR_Benchmark_V3.pptx assets_v2 previews
git commit -m "OCR benchmark deck V3: generated on Azure ML" || echo "Nothing new to commit."
git push
echo "Done: deck, receipt crops and previews pushed."
