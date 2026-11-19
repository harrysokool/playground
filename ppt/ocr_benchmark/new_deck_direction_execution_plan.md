# Direction and Execution Plan for the New Audit AI Deck

## 1. Purpose of This Document

This document instructs an AI agent how to redesign the presentation about the medical-receipt audit application.

The new deck must not be a generic presentation about AI or a narrow comparison of OCR tools. It must explain, from an auditor's perspective, how the application changes the audit process, what measurable value it creates, why AI is needed, and how the solution can be used responsibly at scale.

The existing benchmark of three technical approaches remains useful, but it should support the business and audit argument rather than dominate the story.

---

## 2. Primary Audience

The main audience is internal audit stakeholders, especially business auditors who currently perform manual receipt testing.

Assume the audience:

- Understands the current audit process and audit risks.
- May not have deep technical knowledge of OCR, Azure Document Intelligence, or generative AI.
- Wants to know how the application improves audit quality, coverage, efficiency, and insight.
- Will be concerned about accuracy, explainability, governance, data privacy, scalability, and human oversight.
- Does not need to be convinced that AI is generally powerful. It needs to be shown why AI is suitable for this specific audit use case.

---

## 3. Core Narrative

The entire deck should support this central message:

> The application uses OCR and contextual AI to transform unstructured medical receipts into controlled, structured audit data. This enables auditors to move from limited manual sampling toward population-scale receipt screening, automate repetitive comparisons, perform additional analytics, and focus professional judgement on higher-risk exceptions.

The narrative should follow this sequence:

1. Explain the limitations of the current manual audit process.
2. Show how receipt-level data can improve the audit approach.
3. Explain how OCR and AI work together to create audit-ready data.
4. Use the benchmark to demonstrate why contextual AI is more practical than rules-only extraction.
5. Show the audit tests and insights enabled by the structured data.
6. Clarify which tests should use AI and which should use deterministic analytics.
7. Address human oversight, governance, validation, privacy, and scalability.
8. Recommend a controlled pilot and independent validation before operational use.

---

## 4. Current-State Audit Problem

The deck should begin with the audit problem, not the technology.

Currently, business auditors may sample approximately 25 receipts and manually perform checks such as:

- Comparing receipt information with customer-entered claim information.
- Identifying mismatches in dates, amounts, practitioner details, or other fields.
- Reviewing line items, diagnoses, and treatments.
- Assessing whether diagnosis or treatment information is consistent with patient attributes where the test is approved and methodologically appropriate.
- Reviewing supporting documents for unusual or potentially non-compliant information.

Key limitations of the current process:

- Coverage is limited by manual effort and audit timelines.
- Valuable information remains trapped inside unstructured receipt images or PDFs.
- Auditors spend time reading and transcribing normal receipts instead of investigating exceptions.
- Some cross-transaction or contextual tests are impractical to perform manually.
- Manual testing may be less consistent across auditors and audit cycles.

Do not criticize the existing audit team. Present the application as an enhancement that allows auditors to spend more time applying professional judgement.

---

## 5. Target Audit Value

The deck should organize the value proposition into four pillars.

### 5.1 Broader Coverage

- Move from a small manually selected sample toward population-scale receipt screening.
- Process all available and supported receipts where technically and operationally feasible.
- Preserve completed, uncertain, failed, and needs-review outcomes.
- Make processing failures visible as coverage limitations instead of silently treating them as compliant.

Use the phrase **population-scale screening** or **full-population screening capability** rather than claiming complete audit assurance.

Do not equate automated processing with conclusive testing of every transaction.

### 5.2 Improved Efficiency

- Reduce manual reading, transcription, and repetitive field comparison.
- Allow auditors to review exceptions instead of every normal receipt.
- Reuse structured receipt data across multiple audit tests.
- Reduce the effort needed to add support for varying receipt layouts compared with maintaining format-specific rule sets.

### 5.3 Additional Audit Insights

Once receipt information is structured, the audit team may perform tests that were previously too time-consuming, including:

- Receipt amount versus claimed amount.
- Receipt date versus submitted consultation date.
- Practitioner name or registration number versus registry records.
- Duplicate receipt or repeated receipt-detail indicators.
- Diagnosis-treatment inconsistencies.
- Unusual combinations of diagnosis, treatment, amount, clinic, practitioner, or patient attributes.
- Repeated claims with similar receipt characteristics.
- Transactions near approval or reimbursement thresholds.
- Missing, incomplete, or ambiguous supporting information.

Clearly separate currently implemented functionality from future or downstream audit tests.

### 5.4 Stronger Corroboration

The application introduces receipt-level source-document data as an additional comparison point.

It should not claim that receipt data is automatically more reliable or that the application proves receipt authenticity.

The correct message is:

> Audit evidence is strengthened by comparing information across customer-entered claim data, receipt-extracted data, practitioner reference data, and applicable policy or analytics rules.

Possible data sources include:

1. Customer-entered claim information.
2. Medical receipt images or PDFs.
3. Extracted receipt fields.
4. Local or approved practitioner registry data.
5. Policy requirements and approval limits.
6. Historical claims or transaction data used by approved downstream analytics platforms.

---

## 6. Technology Positioning: OCR and AI Are Complementary

The deck must not present the solution as "AI versus OCR" in a way that suggests OCR is unnecessary.

Use this distinction:

- **OCR reads:** It recognizes text, numbers, and reading order from the document.
- **Rules parse:** They locate values using predefined labels, positions, or patterns.
- **Contextual AI interprets:** It determines which text represents audit-relevant fields despite differences in layout, language, labels, abbreviations, and wording.
- **Deterministic analytics test:** SQL, Python, Power BI, or another approved analytics platform performs reproducible comparisons, thresholds, aggregations, and population-level tests.
- **Auditors conclude:** Auditors review exceptions, corroborate evidence, and make the final audit assessment.

Preferred architecture:

> Azure Document Intelligence for document reading, Azure OpenAI for contextual extraction, deterministic analytics for reproducible audit tests, and auditors for final judgement.

Avoid claims that AI only needs one good prompt. Use this wording instead:

> Contextual AI reduces dependence on merchant- or layout-specific extraction rules, making the extraction layer more adaptable. However, it still requires prompt and schema design, approved evaluation data, accuracy thresholds, regression testing, monitoring, and human-review controls.

---

## 7. How to Use the Existing Benchmark

The benchmark tested three approaches:

1. General OCR plus rules.
2. Azure Document Intelligence plus rules.
3. Azure Document Intelligence plus Azure OpenAI.

The benchmark should answer this question:

> Which approach can most practically convert varied medical receipts into structured, usable audit data?

Use the benchmark as evidence that contextual interpretation adds value beyond text recognition alone.

If the existing figures remain unchanged, show:

- Azure Document Intelligence plus Azure OpenAI: 49 of 51 fields, 96.1%.
- Azure Document Intelligence plus rules: 36 of 51 fields, 70.6%.
- PaddleOCR plus rules: 26 of 51 fields, 51.0%.

Immediately disclose the limitations:

- The proof of concept used only nine receipts.
- The rules and AI instructions were developed using those receipts.
- The findings are directional and not production acceptance evidence.
- An independent and representative holdout dataset is required.
- Accuracy should be measured by field and by error severity, not only through one overall percentage.

Do not state that AI has been proven production-ready.

---

## 8. Scalability Argument

The deck should explain that scalability includes more than processing volume.

### 8.1 Volume Scalability

Can the application process a materially larger receipt population within the audit timeline and approved Azure capacity?

### 8.2 Document Variety

Can it handle different clinics, practitioners, layouts, labels, languages, currencies, image qualities, and numbers of line items?

### 8.3 Maintenance Scalability

Rules-only extraction may require:

1. Investigating each new failure pattern.
2. Adding or modifying parsing rules.
3. Testing changes against previous formats.
4. Maintaining a growing rule library.
5. Repeating the cycle as receipt formats change.

AI can reduce this format-specific maintenance burden by using field definitions, context, extraction instructions, and structured-output schemas. Do not claim that maintenance disappears.

### 8.4 Testing Scalability

Structured receipt data should support several downstream tests without repeating manual extraction.

### 8.5 Operational Scalability

The pilot should measure:

- Successful processing rate.
- Needs-review and failure rates.
- Per-field extraction accuracy.
- False-positive rate by audit test.
- Auditor override rate.
- Average processing time per receipt.
- End-to-end processing time for a defined batch.
- Estimated cost per receipt or per 1,000 receipts.
- Percentage of the available population screened.
- Hours of manual effort saved.

Do not invent target values unless the project team has approved them.

---

## 9. Different Tests Should Run on Different Platforms

The deck should clearly state that AI is not the correct platform for every test.

| Nature of activity | Preferred mechanism | Examples |
|---|---|---|
| Document text recognition | Azure Document Intelligence | Read printed text, numbers, tables, and document order |
| Contextual field extraction | Azure OpenAI with structured output | Identify diagnosis, treatment, practitioner, date, and amount across varying layouts |
| Deterministic high-volume testing | SQL, Python, Power BI, or approved audit analytics platform | Amount mismatch, date mismatch, threshold breach, duplicate indicators |
| External reference matching | Controlled application logic and approved local reference data | Practitioner name or registration-number matching |
| Contextual risk screening | AI-supported logic with defined criteria and human review | Ambiguous descriptions or unusual diagnosis-treatment combinations |
| Final exception assessment | Auditor | Corroboration, materiality, root cause, and audit conclusion |

Key message:

> Use AI where contextual interpretation creates value. Use deterministic logic where stable, reproducible rules are more reliable, explainable, and cost-effective.

---

## 10. Test of Control Versus Red-Flag Detection

The deck must distinguish these two audit uses.

### 10.1 Test of Control

A test of control evaluates a defined control criterion and should have reproducible logic and sufficient evidence.

Potential examples:

- Required supporting documentation is attached.
- The claim was approved by the appropriate authority.
- The claim was submitted within the required period.
- The amount was within the approver's authorization limit.
- Required receipt fields are present.

The application may provide data to support a control test, but the deck must not imply that AI output alone proves control effectiveness.

### 10.2 Red-Flag Detection

Red-flag tests prioritize transactions for investigation.

Potential examples:

- Receipt information does not match customer-entered information.
- A practitioner cannot be matched or the match is ambiguous.
- A receipt may be duplicated.
- Diagnosis and treatment appear inconsistent.
- Receipt details are incomplete, unusual, or ambiguous.
- A transaction has characteristics associated with elevated risk.

Required statement:

> An AI-generated red flag is not an audit finding. It is an indicator requiring auditor review and corroboration.

---

## 11. Governance and Responsible Use

Governance should be integrated into the proposed operating model, not treated as an afterthought.

Cover at least the following areas:

### 11.1 Data Governance

- Use approved data sources and environments.
- Minimize personal data sent for model processing.
- Define access control, retention, and deletion requirements.
- Address applicable internal privacy requirements and the Hong Kong Personal Data (Privacy) Ordinance where relevant.

### 11.2 Model and Prompt Governance

- Use approved Azure services and model deployments.
- Version prompts, extraction schemas, model versions, and configuration.
- Apply change control before operational deployment.
- Perform regression testing after material changes.

### 11.3 Validation

- Build an independent, representative evaluation set.
- Include different receipt layouts, languages, image qualities, and field types.
- Define per-field quality metrics and minimum acceptance thresholds.
- Distinguish critical fields, such as amount and date, from lower-impact descriptive fields.
- Measure missing values, incorrect values, and unsupported inferences separately.

### 11.4 Human Oversight

- Route ambiguous, failed, and material exceptions to auditors.
- Do not allow the model to make the final audit conclusion.
- Document who reviewed and resolved exceptions.

### 11.5 Traceability

Where permitted, preserve:

- Source-document reference.
- Extracted field values.
- Processing status.
- Practitioner match status and rationale.
- Prompt or schema version.
- Model deployment or version.
- Time of processing.
- Downstream test result.
- Auditor review outcome.

### 11.6 Ongoing Monitoring

- Monitor error, failure, exception, and override rates.
- Review cost and processing time.
- Revalidate after model, prompt, policy, source-data, or receipt-population changes.

---

## 12. Recommended Slide Structure

Create a concise management-level deck of approximately 9 to 11 slides.

### Slide 1: Title and Executive Message

**Suggested title:** AI-Enabled Medical Receipt Testing

**Message:** Transform unstructured receipts into audit-ready data to broaden screening, improve efficiency, and enable additional insights.

### Slide 2: Current Audit Process and Limitations

Show the current manual sample-based process, including the approximate sample of 25 receipts, repetitive comparisons, limited coverage, and information trapped inside receipt images.

### Slide 3: Future-State Audit Operating Model

Show the shift from manual review of every sampled receipt to population-scale automated screening followed by auditor review of exceptions.

Suggested flow:

**Available receipt population -> automated processing -> deterministic and contextual tests -> exception prioritization -> auditor review**

### Slide 4: Data Sources and Evidence Model

Show how customer-entered claim data, receipt-extracted data, practitioner reference data, and policy or analytics rules are compared.

Emphasize corroboration across sources rather than claiming that one source is inherently reliable.

### Slide 5: OCR Reads; AI Interprets

Explain the complementary roles of Azure Document Intelligence, Azure OpenAI, deterministic analytics, and auditor judgement in simple business language.

### Slide 6: Proof-of-Concept Benchmark

Present the three tested approaches, accuracy results, key strengths, maintenance implications, and proof-of-concept limitations.

### Slide 7: Audit Value and Additional Tests

Organize benefits under broader coverage, improved efficiency, additional insights, and stronger corroboration. Include concrete examples of downstream audit tests.

### Slide 8: Right Platform for Each Test

Show that document reading, contextual extraction, deterministic analytics, external-reference matching, and auditor assessment should run on the most suitable platform.

### Slide 9: Tests of Control Versus Red Flags

Explain the distinction and state that red flags require auditor review and are not audit findings.

### Slide 10: Governance and Scalability

Combine the control framework with measurable pilot indicators, including accuracy, failure rate, false positives, processing time, cost, coverage, and auditor overrides.

### Slide 11: Recommendation and Next Steps

Recommend a controlled pilot of the hybrid architecture, followed by independent validation and phased expansion.

---

## 13. Recommended Final Position

Use a recommendation similar to the following:

> Proceed with a controlled pilot using Azure Document Intelligence for document reading and Azure OpenAI for contextual extraction. Export structured receipt data to an approved analytics environment for deterministic population-level testing, while routing ambiguous and material exceptions to auditors. Before operational use, validate the solution on an independent and representative dataset, define per-field acceptance criteria, implement model and data governance, and measure audit coverage, accuracy, false positives, processing time, cost, and manual effort saved.

---

## 14. Writing and Design Instructions for the AI Agent

### Writing Style

- Write for auditors and audit management, not software engineers.
- Lead with audit value and risk, then explain the technology needed to deliver it.
- Use concise, professional wording.
- Use concrete examples instead of broad claims such as "AI improves everything."
- Clearly distinguish implemented capability, pilot capability, downstream testing, and future opportunities.
- State limitations directly to build credibility.
- Avoid unnecessary technical implementation detail unless it supports an audit control or governance point.

### Visual Style

- Use one main message per slide.
- Prefer process diagrams, before-and-after comparisons, architecture flows, and small scorecards over paragraphs.
- Use the benchmark chart only once.
- Use consistent colors for roles, for example:
  - Source data: grey or blue.
  - OCR/document processing: teal.
  - AI interpretation: purple.
  - Deterministic analytics: dark blue.
  - Auditor review: orange.
  - Governance controls: muted green.
- Visually show that governance and human oversight apply across the workflow.
- Place important caveats close to the related claim rather than in unreadable footnotes.

---

## 15. Claims and Phrases to Avoid

Do not use the following claims without qualification:

- "AI provides full audit coverage."
- "AI replaces auditors."
- "The receipt is always more reliable than customer-entered data."
- "AI proves that a receipt is genuine."
- "AI only needs a good prompt."
- "The 96.1% result proves production readiness."
- "OCR is no longer needed."
- "Every AI red flag is an audit finding."
- "The application currently performs all downstream analytics."

Use these alternatives:

- "Supports population-scale receipt screening."
- "Allows auditors to focus on higher-risk exceptions."
- "Adds source-document data as an independent comparison point."
- "Reduces dependence on format-specific rules."
- "Provides directional proof-of-concept evidence."
- "Combines OCR, contextual AI, deterministic analytics, and auditor judgement."

---

## 16. Success Criteria for the New Deck

The redesigned deck is successful if an audit stakeholder can answer the following questions after viewing it:

1. What limitation in the current audit process does the application address?
2. How does it improve coverage and efficiency?
3. What additional tests or insights become possible?
4. Why is receipt-extracted data valuable when combined with other audit data?
5. Why is contextual AI more scalable than a rules-only extraction approach?
6. Why are OCR and AI complementary rather than mutually exclusive?
7. Which activities should use AI, deterministic analytics, or auditor judgement?
8. What is the difference between a test of control and a red flag?
9. What are the current proof-of-concept limitations?
10. What governance, validation, and human-review controls are required?
11. What should the project team do next?

If the deck mainly explains model accuracy or technical architecture but does not answer these questions, it has not achieved the required direction.
