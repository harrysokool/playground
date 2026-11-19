"use strict";

// From this folder, run npm ci and then npm run build.
// The build reads committed benchmark CSVs and makes no service calls.

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { parse } = require("csv-parse/sync");
const PptxGenJS = require("pptxgenjs");
const { autoFontSize } = require("./pptxgenjs_helpers/text");
const {
  warnIfSlideHasOverlaps,
  warnIfSlideElementsOutOfBounds,
} = require("./pptxgenjs_helpers/layout");

const results = process.env.BENCHMARK_RESULTS_DIR ||
  path.resolve(__dirname, "../../../python/receipt_ocr_benchmark/results/v2");
const output = process.argv[2] || path.join(__dirname, "Medical_Receipt_Audit.pptx");

const fields = {
  doctor_name: "Practitioner name",
  registration_number: "Registration number",
  patient_name: "Patient name",
  receipt_number: "Receipt number",
  service_date: "Service date",
  total_amount: "Total amount",
};
const fieldKeys = Object.keys(fields);
const rules = "scores_multilingual";
const ai = "scores_aoai_improved";
const run = {
  paddle: [rules, "paddle_light_multilingual", "PaddleOCR + rules"],
  azure: [rules, "azure_di_multilingual", "Azure DI + rules"],
  contextual: [ai, "aoai_v2_rows", "Azure DI + OpenAI"],
};

function readScores(folder, file) {
  return parse(fs.readFileSync(path.join(results, folder, file)), {
    columns: true,
    skip_empty_lines: true,
  });
}

function score([folder, approach, label]) {
  const details = readScores(folder, "detail.csv").filter(row => row.approach === approach);
  const summary = readScores(folder, "summary.csv").find(row => row.approach === approach);
  assert.ok(summary, `Missing summary for ${approach}`);
  const receipts = new Set(details.map(row => row.receipt));
  assert.equal(details.length, receipts.size * fieldKeys.length);
  assert.equal(new Set(details.map(row => `${row.receipt}/${row.field}`)).size, details.length);
  assert.ok(details.every(row => fieldKeys.includes(row.field)));
  assert.ok(details.every(row => ["Correct", "Wrong", "N/A", "N/A (invented)"].includes(row.result)));
  const applicable = details.filter(row => row.result === "Correct" || row.result === "Wrong");
  const byField = Object.fromEntries(fieldKeys.map(field => {
    const rows = applicable.filter(row => row.field === field);
    const correct = rows.filter(row => row.result === "Correct").length;
    assert.equal((100 * correct / rows.length).toFixed(1), Number(summary[field + "_accuracy_pct"]).toFixed(1));
    return [field, { correct, total: rows.length }];
  }));
  const correct = applicable.filter(row => row.result === "Correct").length;
  assert.equal(correct, Number(summary.correct));
  assert.equal(applicable.length, Number(summary.applicable));
  const pct = Number((100 * correct / applicable.length).toFixed(1));
  assert.equal(pct, Number(summary.accuracy_pct));
  return { label, details, receipts: receipts.size, correct, total: applicable.length, pct, byField };
}

const scores = Object.values(run).map(score);
const reference = scores[0].details.map(({ receipt, field, ground_truth }) => [receipt, field, ground_truth]).sort();
for (const method of scores.slice(1)) {
  assert.deepEqual(method.details.map(({ receipt, field, ground_truth }) => [receipt, field, ground_truth]).sort(), reference);
}
const best = scores[2];
const dentalAmount = scores[1].details.find(row => row.receipt === "receipt5" && row.field === "total_amount");
assert.equal(dentalAmount.result, "Wrong");
const illustrativeClaim = Number(dentalAmount.predicted);
const receiptTotal = Number(dentalAmount.ground_truth);
assert.ok(Number.isFinite(illustrativeClaim) && Number.isFinite(receiptTotal));
const hkd = new Intl.NumberFormat("en-HK", { maximumFractionDigits: 2 });
const formatAmount = amount => `HK$${hkd.format(amount)}`;
const notApplicable = best.receipts * fieldKeys.length - best.total;
const perField = fieldKeys.map(field => {
  const results = scores.map(method => {
    const { correct, total } = method.byField[field];
    return `${correct}/${total}`;
  });
  return `${fields[field]}: ${results.join(" | ")}`;
});

const pptx = new PptxGenJS();
pptx.layout = "LAYOUT_WIDE";
pptx.title = "AI-enabled medical receipt testing";
pptx.subject = "Internal Audit pilot proposal and receipt extraction benchmark";
pptx.author = "Codex";
pptx.lang = "en-GB";
const font = "Arial";
pptx.theme = { headFontFace: font, bodyFontFace: font, lang: "en-GB" };

const W = 40 / 3;
const L = 0.68;
const R = W - L;
const C = {
  bg: "F7F6F3", white: "FFFFFF", ink: "182638", muted: "4C5D69", line: "DADFD9",
  navy: "142638", navyLight: "243B51", navyTint: "E7EEF5",
  teal: "006D64", tealTint: "E0F1EC", mint: "A9E4D1",
  violet: "6045A1", violetTint: "EEE8F8",
  orange: "88431C", orangeTint: "F9E9DD",
};

function text(slide, value, x, y, w, h, size, options = {}) {
  const { color = C.ink, bold = false, align = "left", minSize = size - 1, ...extra } = options;
  const { fontSize } = autoFontSize(value, font, {
    x, y, w, h, fontSize: size, minFontSize: minSize, maxFontSize: size,
    mode: "shrink", bold, margin: 0,
  });
  slide.addText(value, {
    x, y, w, h, fontFace: font, fontSize, bold, color, align,
    valign: "mid", margin: 0, ...extra,
  });
}

function rect(slide, x, y, w, h, fill, border = fill) {
  slide.addShape(pptx.ShapeType.rect, {
    x, y, w, h, fill: { color: fill }, line: { color: border, width: 0.6 },
  });
}

function rule(slide, x1, x2, y, color = C.line) {
  slide.addShape(pptx.ShapeType.line, {
    x: x1, y, w: x2 - x1, h: 0, line: { color, width: 0.8 },
  });
}

function arrow(slide, x, y, w, color = C.muted) {
  slide.addShape(pptx.ShapeType.line, {
    x, y, w, h: 0, line: { color, width: 1.3, endArrowType: "triangle" },
  });
}

function label(slide, value, x, y, w, color = C.teal) {
  text(slide, value, x, y, w, 0.22, 11, { bold: true, color, charSpacing: 0.9 });
}

function page(slide, section, title, description) {
  slide.background = { color: C.bg };
  label(slide, section, L, 0.43, 11);
  text(slide, title, L, 0.77, R - L, 0.60, 32, { bold: true });
  text(slide, description, L, 1.46, R - L, 0.39, 16, { color: C.muted });
  rule(slide, L, R, 6.98);
  text(slide, "Internal Audit pilot proposal", L, 7.07, 5.2, 0.19, 10, { color: C.muted });
  text(slide, String(pptx.slides.length).padStart(2, "0"), R - 0.5, 7.07, 0.5, 0.19, 10,
    { color: C.muted, align: "right" });
}

function note(slide, ...paragraphs) {
  slide.addNotes(paragraphs.join("\n\n"));
}

// Card fills intentionally sit behind and fully contain their editable text.
function card(slide, x, y, w, h, heading, body, fill, accent, options = {}) {
  const { headingSize = 17, bodySize = 14, pad = 0.19, headingH = 0.35, bodyY = 0.68 } = options;
  rect(slide, x, y, w, h, fill);
  text(slide, heading, x + pad, y + 0.16, w - 2 * pad, headingH, headingSize, { bold: true, color: accent });
  text(slide, body, x + pad, y + bodyY, w - 2 * pad, h - bodyY - 0.14, bodySize, { valign: "top" });
}

function strip(slide, copy, y, fill = C.tealTint, color = C.teal) {
  rect(slide, L, y, R - L, 0.54, fill);
  text(slide, copy, L + 0.16, y + 0.12, R - L - 0.32, 0.30, 14.5, { bold: true, color });
}

// 1. Open on the audit decision.
{
  const s = pptx.addSlide();
  s.background = { color: C.navy };
  label(s, "INTERNAL AUDIT  /  PILOT PROPOSAL", L, 0.67, 7.1, C.mint);
  text(s, "AI-enabled medical\nreceipt testing", L, 1.30, 7.55, 2.12, 47,
    { color: C.white, bold: true });
  text(s, "Turn receipt images into structured evidence so auditors can screen more claims and focus on exceptions.",
    L, 3.64, 7.05, 1.13, 23, { color: "D8E6EC", valign: "top" });
  const milestones = [
    ["Receipt data", "Read and extract source fields"],
    ["Audit testing", "Compare against claims and policy"],
    ["Auditor review", "Corroborate and resolve exceptions"],
  ];
  const x = 8.45;
  const w = 4.19;
  milestones.forEach(([heading, body], i) => {
    const y = 1.29 + i * 1.36;
    // The dark backing intentionally contains both text boxes.
    rect(s, x, y, w, 1.09, C.navyLight, "3E5970");
    text(s, heading, x + 0.23, y + 0.15, w - 0.46, 0.37, 19, { bold: true, color: i === 2 ? C.mint : C.white });
    text(s, body, x + 0.23, y + 0.62, w - 0.46, 0.24, 13.5, { color: "D8E6EC" });
    if (i < milestones.length - 1) {
      s.addShape(pptx.ShapeType.line, {
        x: x + w / 2, y: y + 1.12, w: 0, h: 0.17,
        line: { color: C.mint, width: 1.1, endArrowType: "triangle" },
      });
    }
  });
  rule(s, L, R, 6.24, "496177");
  label(s, "DECISION REQUESTED", L, 6.51, 2.28, C.mint);
  text(s, "Approve a controlled pilot and independent validation.", 3.10, 6.42, 9.51, 0.40, 19,
    { bold: true, color: C.white });
  note(s, "Audience: business auditors and Internal Audit management. Present this as a pilot proposal.",
    "Sources: new_deck_direction_execution_plan.md and OCR_Benchmark_V14.pptx. The nine-receipt extraction proof of concept supports the proposed pilot. Population screening, operational savings and downstream audit outcomes are proposed benefits to measure.");
}

// 2. Show what auditors do today.
{
  const s = pptx.addSlide();
  page(s, "CURRENT PROCESS", "Manual testing limits receipt coverage",
    "Auditors inspect source documents, reconcile details to claims and investigate differences.");
  rect(s, L, 2.15, 3.62, 3.77, C.navy);
  text(s, "≈25", L + 0.24, 2.49, 3.14, 1.22, 67, { bold: true, color: C.mint });
  text(s, "receipts in an example manual sample", L + 0.26, 4.02, 3.08, 0.85, 22,
    { bold: true, color: C.white, valign: "top" });
  text(s, "Confirm the baseline for the pilot.", L + 0.26, 5.26, 3.08, 0.35, 13, { color: "D8E6EC" });
  const rows = [
    ["Read and transcribe", "Find names, service dates, amounts and other details in receipt images or PDFs."],
    ["Reconcile to the claim", "Check whether the receipt agrees with claim-system records and supporting documents."],
    ["Investigate exceptions", "Review mismatches and apply policy, approval and evidence criteria."],
  ];
  rows.forEach(([heading, body], i) => {
    const y = 2.17 + i * 1.27;
    label(s, heading.toUpperCase(), 4.68, y + 0.02, 7.75);
    text(s, body, 4.68, y + 0.37, 7.86, 0.50, 17);
    rule(s, 4.68, R, y + 1.07);
  });
  strip(s, "Structured receipt data can make cross-claim checks, such as duplicate screening, practical.", 6.18);
  note(s, "The approximate sample of 25 comes from the execution plan. Confirm actual counts and time spent with the audit team before estimating benefit.",
    "Source: manual_sample_test.png. The checklist also covers authenticity cues, insurer identity, coverage and medical necessity where applicable, payment recalculation, authority checks and fraud, waste and abuse indicators.");
}

// 3. Define coverage and visible outcomes.
{
  const s = pptx.addSlide();
  page(s, "PROPOSED OPERATING MODEL", "Screen the available population and route exceptions",
    "Track every in-scope receipt through extraction, testing and any review it requires.");
  const steps = [
    ["Inventory", "Count available and supported receipts.", C.navyTint, C.navy],
    ["Extract", "Capture fields and link to the source.", C.tealTint, C.teal],
    ["Run tests", "Apply approved comparisons and checks.", C.violetTint, C.violet],
    ["Triage", "Prioritise failures and material flags.", C.orangeTint, C.orange],
    ["Resolve", "Auditor reviews and records disposition.", C.navyTint, C.navy],
  ];
  steps.forEach(([heading, body, fill, accent], i) => {
    const x = L + i * 2.47;
    card(s, x, 2.22, 2.11, 1.64, heading, body, fill, accent);
    if (i < steps.length - 1) arrow(s, x + 2.16, 3.00, 0.24);
  });
  card(s, L, 4.22, 5.84, 1.58, "Completed",
    "Keep test results and evidence links. Sample completed cases for quality checks.", C.white, C.teal,
    { bodySize: 16 });
  card(s, 6.80, 4.22, 5.84, 1.58, "Needs review, failed or unsupported",
    "Route exceptions or log coverage gaps. Record who resolved each case.", C.white, C.orange,
    { bodySize: 16 });
  strip(s, "Coverage = receipts that completed approved screening ÷ all in-scope receipts.", 6.17);
  note(s, "The denominator includes available in-scope receipts that were unsupported, failed or did not complete the relevant screening. Report each status and why items failed or were excluded.",
    "This is population-scale screening capability. Audit assurance still depends on data quality, test design, coverage and human review. Retain existing audit procedures while validating the approach.");
}

// 4. Show how independent inputs inform a reproducible test.
{
  const s = pptx.addSlide();
  page(s, "AUDIT EVIDENCE", "Receipt data gives auditors another source to compare",
    "Each source answers a different question about the same claim.");
  const inputs = [
    ["Claim-system record", "What did the claimant submit?"],
    ["Receipt and extracted fields", "What does the source document show?"],
    ["Practitioner reference data", "Can the identified practitioner be matched?"],
    ["Policy and approval criteria", "Which requirement or threshold applies?"],
  ];
  inputs.forEach(([heading, body], i) => {
    const y = 2.22 + i * 0.82;
    text(s, heading, L + 0.02, y, 5.75, 0.30, 17, { bold: true });
    text(s, body, L + 0.02, y + 0.35, 5.75, 0.26, 14.5, { color: C.muted });
    rule(s, L + 0.02, 6.30, y + 0.73);
  });
  // The light panel intentionally contains the illustrative reconciliation and its labels.
  rect(s, 6.66, 2.18, 5.99, 3.78, C.white, C.line);
  label(s, "ILLUSTRATIVE AMOUNT CHECK", 6.92, 2.44, 5.43);
  const amounts = [
    ["Claimed amount (illustrative)", formatAmount(illustrativeClaim)],
    ["Receipt total after discount", formatAmount(receiptTotal)],
    ["Difference", formatAmount(illustrativeClaim - receiptTotal)],
  ];
  amounts.forEach(([name, amount], i) => {
    const y = 2.89 + i * 0.69;
    text(s, name, 6.92, y, 3.47, 0.33, 15.5, { bold: i === 2 });
    text(s, amount, 10.54, y, 1.83, 0.33, 17, { bold: true, align: "right", color: i === 2 ? C.orange : C.ink });
    if (i < 2) rule(s, 6.92, 12.39, y + 0.49);
  });
  text(s, "Review the source, discount and applicable policy before deciding how to resolve the difference.",
    6.92, 5.01, 5.43, 0.61, 14.5, { color: C.muted });
  strip(s, "Preserve the receipt reference, extracted value, claim record and test result for review.", 6.20);
  note(s, "The dental receipt benchmark example shows a HK$1,750 subtotal and a HK$1,575 final total after discount. The HK$1,750 claim is hypothetical. Source: OCR_Benchmark_V14.pptx slide 6 and results/v2/scores_multilingual/detail.csv.",
    "A receipt supplies corroborating evidence. Authenticity, eligibility and payment correctness require further evidence and approved procedures.");
}

// 5. Show data boundaries and roles.
{
  const s = pptx.addSlide();
  page(s, "TECHNOLOGY AND DATA BOUNDARY", "OCR reads the receipt. Contextual AI selects the fields.",
    "A single extraction can supply receipt fields for multiple audit tests.");
  rect(s, L, 2.15, 6.39, 2.66, C.tealTint);
  label(s, "AZURE  /  APPROVED RECEIPT DATA ONLY", L + 0.19, 2.37, 5.98);
  card(s, L + 0.19, 2.84, 2.79, 1.62, "Document Intelligence", "Reads text and layout from the receipt.", C.white, C.teal,
    { headingSize: 15.5, bodySize: 15 });
  arrow(s, 3.74, 3.57, 0.23, C.teal);
  card(s, 4.05, 2.84, 2.80, 1.62, "Azure OpenAI", "Extracts defined fields and flags uncertainty.", C.white, C.violet,
    { headingSize: 16, bodySize: 15 });
  arrow(s, 7.17, 3.56, 0.46, C.teal);
  rect(s, 7.75, 2.15, 4.90, 2.66, C.navyTint);
  label(s, "AUTHORIZED AUDIT ENVIRONMENT", 7.95, 2.37, 4.50, C.navy);
  text(s, "Deterministic analytics and auditor review", 7.95, 2.83, 4.45, 0.64, 19,
    { bold: true });
  text(s, "Join structured fields to claims, policy, history and approved reference data.",
    7.95, 3.64, 4.41, 0.65, 15.5);
  text(s, "Transfer of approved structured output requires agreement and approval.",
    L, 4.94, R - L, 0.36, 14, { color: C.muted, bold: true });
  card(s, L, 5.47, R - L, 1.17, "Why context matters",
    "On a physiotherapy receipt, the rules picked the referring doctor and issue date. Azure OpenAI identified the treating practitioner and service date.",
    C.white, C.violet, { bodyY: 0.60, headingH: 0.31, bodySize: 15 });
  note(s, "Both extraction methods used the same Azure DI text for this example. Source: OCR_Benchmark_V14.pptx slide 6 and the saved multilingual and Azure OpenAI scores for receipt 6.",
    "Keep claims, policy and historical data in the authorized audit environment. Agree field minimization, transfer, access, retention and deletion before the pilot. Contextual extraction can reduce dependence on layout-specific rules. It still requires evaluation, change control and review.");
}

// 6. Use the technical benchmark once.
{
  const s = pptx.addSlide();
  page(s, "EXTRACTION PROOF OF CONCEPT", "Contextual extraction recovered more receipt fields",
    `The three approaches processed the same ${best.receipts} receipts. The benchmark scored ${best.total} applicable fields.`);
  // Native PowerPoint chart and embedded data. The adjacent copy does not overlap the plot.
  s.addChart(pptx.ChartType.bar, [{
    name: "Correct applicable fields",
    labels: scores.map(method => `${method.label}\n${method.correct}/${method.total} fields`),
    values: scores.map(method => method.pct / 100),
  }], {
    x: L, y: 2.20, w: 7.40, h: 3.69, barDir: "col", barGrouping: "clustered",
    chartColors: ["7F94A5", "467B83", C.teal], showLegend: false,
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.0%",
    dataLabelColor: C.ink, dataLabelFontFace: font, dataLabelFontSize: 14,
    catAxisLabelFontFace: font, catAxisLabelFontSize: 12, catAxisLabelColor: C.ink,
    valAxisLabelFontFace: font, valAxisLabelFontSize: 10, valAxisLabelColor: C.muted,
    valAxisMinVal: 0, valAxisMaxVal: 1.08, valAxisMajorUnit: 0.25, valAxisLabelFormatCode: "0%",
    valGridLine: { color: C.line, width: 0.6 }, catGridLine: { style: "none" },
    gapWidthPct: 75,
  });
  rect(s, 8.34, 2.22, 4.31, 3.63, C.orangeTint);
  label(s, "DEVELOPMENT-SET RESULTS", 8.56, 2.47, 3.91, C.orange);
  text(s, "The team had already reviewed these receipts when adapting the rules and refining the AI instructions.",
    8.56, 2.88, 3.82, 1.02, 17, { bold: true, valign: "top" });
  text(s, "Validate on independent receipts. Measure accuracy by field and classify errors by severity.",
    8.56, 4.17, 3.82, 1.08, 16, { valign: "top" });
  text(s, `${notApplicable} registration numbers were inapplicable. The comparison covers field extraction only.`,
    L, 6.07, R - L, 0.31, 13, { color: C.muted });
  note(s, "Source: python/receipt_ocr_benchmark/results/v2/scores_multilingual/{summary,detail}.csv and scores_aoai_improved/{summary,detail}.csv, plus docs/MULTILINGUAL_BASELINE.md. The chart uses the multilingual rule baseline and refined row-text Azure OpenAI run. V2 Final Analysis reports an earlier English-only experiment and original prompt.",
    "In a separate experiment, hand-tuned rules scored 45/51 (PaddleOCR) and 44/51 (Azure DI) on the same development receipts. This illustrates the effect of the rules baseline. The four genuinely unseen receipts in the historical check yielded 11/15 for both Azure OpenAI prompts, too few for a representative assessment.",
    "Per-field counts in chart order:\n" + perField.join("\n"));
}

// 7. Bring audit mechanics into the examples.
{
  const s = pptx.addSlide();
  page(s, "POTENTIAL DOWNSTREAM TESTS", "Structured fields support several repeatable audit tests",
    "These tests are candidates for the pilot. Each requires approved logic, data and evidence.");
  const table = [
    ["Receipt-to-claim reconciliation", "Compare patient, service date and final amount to the claim.", "Deterministic comparison"],
    ["Possible duplicate receipt", "Compare receipt number, provider, date and amount across claims.", "Deterministic indicators"],
    ["Practitioner matching", "Match extracted name or registration number to an approved registry.", "Reference lookup and review"],
    ["Fees and authority limits", "Apply approved thresholds to comparable fees or approval amounts.", "Deterministic threshold"],
    ["Diagnosis or treatment review", "Prioritise unusual combinations using approved criteria.", "Contextual triage and review"],
  ];
  const columns = [L + 0.16, 4.26, 9.50];
  const widths = [3.38, 5.02, 2.95];
  rect(s, L, 2.16, R - L, 0.49, C.navy);
  ["Audit test", "Evidence and logic", "Preferred mechanism"].forEach((head, i) =>
    text(s, head, columns[i], 2.25, widths[i], 0.26, 14, { bold: true, color: C.white }));
  table.forEach((row, i) => {
    const y = 2.68 + i * 0.64;
    rect(s, L, y, R - L, 0.60, i % 2 ? C.navyTint : C.white);
    row.forEach((value, j) => text(s, value, columns[j], y + 0.08, widths[j], 0.44, 14,
      { bold: j === 0, color: j === 2 ? C.teal : C.ink }));
  });
  strip(s, "A registry match can identify a named practitioner. Review the receipt to establish their role.", 6.18);
  note(s, "Examples from manual_sample_test.png and the new deck direction plan. V14 and the benchmark README describe exact doctor-registry matching as a proposal, which was not benchmarked. The lookup may surface referring doctors, signatories or ambiguous matches.",
    "The six-field benchmark excludes diagnosis, treatment and line-item extraction. The separate diagnosis experiment assessed comment presence on development receipts. It provides no accuracy estimate for diagnosis or treatment interpretation.");
}

// 8. Explain how findings are made.
{
  const s = pptx.addSlide();
  page(s, "AUDIT INTERPRETATION", "Tests of control and risk flags serve different purposes",
    "Both depend on defined criteria and traceable evidence.");
  const panels = [
    {
      x: L, color: C.teal, fill: C.tealTint, title: "Test of control",
      copy: "Evaluate whether a defined control operated as required.",
      example: "Verify the approval amount and approver against the applicable authority matrix.",
      evidence: "Retain the approval record, matrix version, test result and any exception disposition.",
    },
    {
      x: 6.80, color: C.orange, fill: C.orangeTint, title: "Red-flag screening",
      copy: "Prioritise a transaction for audit follow-up.",
      example: "Flag two claims with the same receipt number, provider, amount and service date.",
      evidence: "Review both documents and claim histories to determine whether the apparent duplicate is valid.",
    },
  ];
  for (const p of panels) {
    rect(s, p.x, 2.20, 5.85, 3.64, p.fill);
    text(s, p.title, p.x + 0.23, 2.39, 5.38, 0.39, 23, { bold: true, color: p.color });
    text(s, p.copy, p.x + 0.23, 2.97, 5.38, 0.46, 16, { bold: true });
    label(s, "EXAMPLE", p.x + 0.23, 3.65, 5.37, p.color);
    text(s, p.example, p.x + 0.23, 3.94, 5.38, 0.61, 16);
    rule(s, p.x + 0.23, p.x + 5.61, 4.71);
    text(s, p.evidence, p.x + 0.23, 4.95, 5.38, 0.60, 15, { color: C.muted });
  }
  strip(s, "Red flags require auditor review and corroboration before they can support a finding.", 6.18);
  note(s, "Source: new_deck_direction_execution_plan.md, section 10, and manual_sample_test.png. Test-of-control conclusions depend on the control design, population, evidence sufficiency and audit methodology.",
    "Use AI only where contextual interpretation adds value under approved criteria. Auditors determine the outcome and document their rationale. A matched rule or risk indicator alone does not establish fraud, authenticity or coverage.");
}

// 9. Make governance visible as part of the workflow.
{
  const s = pptx.addSlide();
  page(s, "GOVERNANCE", "Build privacy, traceability and review into the pilot",
    "Agree the owners and controls for each step before processing approved receipts.");
  const controls = [
    [L, 2.20, "Approve data and access", "Minimise receipt data sent to Azure. Approve access, transfer, retention and deletion.", C.tealTint, C.teal],
    [6.80, 2.20, "Version and validate changes", "Record the model deployment, prompt and schema. Retest material changes before release.", C.violetTint, C.violet],
    [L, 4.00, "Preserve the evidence trail", "Link outputs to the receipt, processing status, run version, test result and review outcome.", C.navyTint, C.navy],
    [6.80, 4.00, "Route and resolve exceptions", "Assign failed, uncertain and material cases to auditors. Record decisions and overrides.", C.orangeTint, C.orange],
  ];
  for (const [x, y, heading, body, fill, accent] of controls) {
    card(s, x, y, 5.85, 1.51, heading, body, fill, accent, { bodySize: 16 });
  }
  strip(s, "Revalidate when the model, prompt, policy, data source or receipt population changes.", 6.17);
  note(s, "Agree responsibilities across Internal Audit, the technology owner, and internal privacy, information security and data governance teams. Confirm applicable Hong Kong privacy and internal requirements with the responsible teams.",
    "Where permitted, retain source references, extracted fields and timestamps, model and prompt versions, practitioner matching evidence, test outcome and auditor disposition. Monitor failures, exceptions, overrides, cost and processing time.");
}

// 10. Define evidence required to judge the pilot.
{
  const s = pptx.addSlide();
  page(s, "PILOT SCORECARD", "Measure extraction quality and the impact on audit work",
    "Use a representative holdout and agreed acceptance criteria before any wider use.");
  const sections = [
    ["Extraction quality", "Score by field and by severity. Track wrong, missing and unsupported values, especially amounts and service dates.", C.tealTint, C.teal],
    ["Coverage and reliability", "Report screened, failed, unsupported and needs-review rates against the full in-scope population.", C.navyTint, C.navy],
    ["Audit test performance", "Measure false positives by test, auditor overrides and missed exceptions in a reviewed sample.", C.violetTint, C.violet],
    ["Capacity and effort", "Measure time per receipt and batch, cost per 1,000 receipts and net auditor hours saved against the manual baseline.", C.orangeTint, C.orange],
  ];
  sections.forEach(([heading, body, fill, accent], i) => {
    const x = i % 2 === 0 ? L : 6.80;
    const y = i < 2 ? 2.19 : 4.00;
    card(s, x, y, 5.85, 1.57, heading, body, fill, accent, { bodySize: 16 });
  });
  strip(s, "Include varied layouts, languages, image quality and receipt types in the holdout.", 6.17);
  note(s, "Use separately labelled receipts kept out of model, prompt and rules development. Benchmark critical fields independently and use approved per-field and per-test thresholds.",
    "Define what counts as screened and reconcile status counts to the pilot inventory. Estimate net time savings after manual exception handling and quality checks. No thresholds, costs or savings have been assumed.");
}

// 11. Close on a staged decision.
{
  const s = pptx.addSlide();
  page(s, "RECOMMENDATION", "Approve a controlled pilot of receipt screening",
    "Use Azure Document Intelligence and Azure OpenAI for extraction, with audit testing in the authorized environment.");
  const stages = [
    ["Define scope", "Confirm owners, approved receipt sources, transfer method and the manual baseline.", C.tealTint, C.teal],
    ["Run in parallel", "Start with amount and service-date reconciliation. Have auditors verify exceptions and sample completed cases.", C.navyTint, C.navy],
    ["Decide whether to expand", "Compare results with agreed thresholds. Expand coverage and fields in phases if the evidence supports it.", C.violetTint, C.violet],
  ];
  stages.forEach(([heading, body, fill, accent], i) => {
    const x = L + i * 4.09;
    card(s, x, 2.36, 3.81, 2.57, heading, body, fill, accent,
      { headingSize: 20, headingH: 0.69, bodyY: 1.03, bodySize: 17, pad: 0.23 });
    if (i < stages.length - 1) arrow(s, x + 3.86, 3.67, 0.17);
  });
  text(s, "Return to Internal Audit with holdout results, the agreed data boundary and the pilot scorecard.",
    L, 5.24, R - L, 0.58, 20, { bold: true });
  strip(s, "Auditors retain responsibility for exception disposition and the audit conclusion.", 6.18);
  note(s, "Suggested scope is intentionally narrow: start with amount and service date because the benchmark tested both fields and the manual audit checklist identifies both. Establish pilot thresholds and the representative evaluation set before the run.",
    "Expand to additional fields and downstream tests only after accuracy, coverage, false positives, operational cost, time and governance meet the agreed pilot criteria. The proposal does not authorize production use.");
}

async function main() {
  for (const slide of pptx.slides) {
    warnIfSlideHasOverlaps(slide, pptx);
    warnIfSlideElementsOutOfBounds(slide, pptx);
  }
  await pptx.writeFile({ fileName: output, compression: true });
  console.log(`Wrote ${output} (${pptx.slides.length} slides)`);
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
