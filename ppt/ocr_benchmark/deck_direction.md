# Direction and Execution Plan for the New Audit AI Deck

## 1. Purpose

Redesign the deck around a simple management story:

1. What problem are we solving?
2. What is the proposed solution?
3. What audit value can it create?
4. Why is AI the preferred extraction approach?
5. How will the solution be governed and integrated with downstream testing?

The deck should focus on the current priority: **reliably extracting important information from medical receipts and converting it into structured data**. Downstream audit tests are potential uses of that data, not the current core scope.

---

## 2. Core Message

> The application uses Azure Document Intelligence and Azure OpenAI to convert unstructured medical receipts into structured, reusable audit data. This can reduce manual work, expand receipt-screening coverage, and enable additional audit testing on approved platforms.

The benchmark supports the selection of the extraction approach. It does not prove production readiness or validate every future audit test.

---

## 3. Audience

The primary audience is Internal Audit management and business auditors.

The deck should:

- Start from the auditors' problem, not the technology.
- Explain the practical value in audit terms.
- Use simple language when discussing OCR, rules, and AI.
- Clearly distinguish current extraction capability from future downstream testing.
- Address accuracy, privacy, PII masking, governance, and platform boundaries.

---

## 4. Recommended Storyline and Slide Structure

### Slide 1: Problem and Proposed Solution

**Purpose:** Immediately explain what is being solved and how.

**Problem:**

- Important information is locked inside unstructured medical receipts.
- Business auditors manually read sampled receipts and compare receipt information with claims-system information.
- Manual extraction limits the number of receipts that can be reviewed.

**Solution:**

- Use Azure Document Intelligence to read receipt content.
- Use Azure OpenAI to identify and structure the audit-relevant fields.
- Export the extracted data for later audit testing and analysis.

**Key message:**

> Build a reliable receipt-data extraction layer so auditors can use receipt information at greater scale.

---

### Slide 2: Business Value to Internal Audit

**Purpose:** Explain why the audit team should care.

Organize the value into four areas:

1. **Broader coverage**
   - Move from limited sample-based receipt review toward population-scale screening of available and supported receipts.

2. **Improved efficiency**
   - Reduce manual reading, field identification, and transcription.
   - Allow auditors to focus more time on exceptions and judgement.

3. **Automation of manual testing**
   - Structured receipt fields can later be compared automatically with claims-system and policy data.

4. **Additional insight**
   - Structured receipt data can support duplicate screening, practitioner checks, pattern analysis, and other future tests.

Do not claim full audit assurance or that AI replaces auditors.

---

### Slide 3: Current Limitations and Bottlenecks

**Purpose:** Explain why the current process does not scale.

Cover:

- Business auditors currently review a limited sample, such as approximately 25 receipts.
- Receipt formats vary across clinics, hospitals, practitioners, languages, and layouts.
- Auditors must manually identify values such as practitioner, patient, treatment date, diagnosis, treatment items, and amount.
- Manual work is repetitive and time-consuming.
- Valuable receipt information remains unstructured and difficult to reuse.
- Small samples limit cross-claim and population-level analysis.

Avoid criticizing the business auditors. Present the bottleneck as a data-access and scalability problem.

---

### Slide 4: How the AI Application Improves the Audit Process

**Purpose:** Explain the benefits in more detail.

Use a before-and-after comparison:

| Current approach | AI-enabled approach |
|---|---|
| Limited manual sample | Potential population-scale receipt processing |
| Manual reading and transcription | Automated field extraction |
| Receipt reviewed separately for each procedure | Structured data reused across tests |
| Auditor effort spent on normal and exceptional cases | Greater focus on exceptions |
| Limited cross-claim analysis | Potential additional analytics and insights |

Show the future flow:

**Medical receipts -> OCR -> AI extraction -> structured receipt dataset -> downstream audit testing -> auditor review**

Clarify that the current project focuses on the extraction layer.

---

### Slide 5: Three Approaches Tested and Benchmark Results

**Purpose:** Show the evidence supporting the recommended approach.

Present the three approaches:

1. PaddleOCR plus rules.
2. Azure Document Intelligence plus rules.
3. Azure Document Intelligence plus Azure OpenAI.

If the figures remain unchanged, show:

- Azure Document Intelligence plus Azure OpenAI: **49/51 fields, 96.1%**.
- Azure Document Intelligence plus rules: **36/51 fields, 70.6%**.
- PaddleOCR plus rules: **26/51 fields, 51.0%**.

Required qualification:

> The results were produced using the project's own small synthetic/development dataset. They demonstrate directional performance only and do not establish production accuracy.

State that an independent and representative validation set is still required.

---

### Slide 6: Concrete Limitations Observed

**Purpose:** Make the comparison real through receipt examples.

Use two or three examples from the benchmark, such as:

- OCR or rules selecting the receipt issue date instead of the treatment date.
- Rules selecting a referring doctor instead of the treating practitioner.
- Different layouts or labels causing a rule to miss the correct amount.
- OCR reading the text correctly but failing to determine the business meaning of the text.
- AI correctly using context, but still requiring validation for missing, ambiguous, or unsupported values.

For each example, show:

**Receipt evidence -> output from each approach -> why the difference matters**

Do not repeat the full benchmark statistics on this slide.

---

### Slide 7: Pros, Cons, and Scalability Trade-offs

**Purpose:** Explain why the AI approach is preferred without presenting any option as perfect.

| Approach | Advantages | Limitations |
|---|---|---|
| PaddleOCR plus rules | Low software dependency; transparent rules | Lower accuracy in the benchmark; more preprocessing; rules depend heavily on layout and wording |
| Azure Document Intelligence plus rules | Stronger document reading; deterministic and explainable | Rules must be created and maintained as formats and labels change |
| Azure Document Intelligence plus Azure OpenAI | Highest development-set accuracy; stronger contextual interpretation; less dependence on format-specific rules | Requires prompt and schema governance, independent validation, monitoring, PII controls, and Azure cost management |

Scalability message:

> Rules-only approaches can require repeated maintenance for new receipt formats. Contextual AI may adapt better to format variation, but it still requires controlled prompts, schemas, testing, and monitoring.

---

### Slide 8: Future Audit Tests Enabled by Structured Receipt Data

**Purpose:** Show why reliable extraction matters without moving the project scope too far ahead.

Separate future uses into two categories.

#### Potential tests of control or deterministic tests

- Required receipt information is present.
- Receipt amount matches the claimed amount.
- Treatment date matches the claims-system date.
- Service date falls within the relevant policy period.
- Claim amount follows the approval-authority matrix.

#### Potential red-flag tests

- Possible duplicate receipt.
- Practitioner cannot be matched or is ambiguous.
- Diagnosis and treatment appear inconsistent.
- Unusual claim, clinic, practitioner, or receipt patterns.

Required boundary:

> These downstream tests require separate business rules, internal data, validation, and auditor review. An AI-generated red flag is not an audit finding.

---

### Slide 9: Governance, PII Masking, and Platform Design

**Purpose:** Explain how receipt processing and downstream testing will be controlled.

#### PII and data handling

- Identify which receipt fields contain PII or sensitive medical information.
- Mask or redact PII before data is sent to components that do not require the information.
- Use approved Azure services, access controls, retention rules, and logging.
- Preserve enough linkage to reconnect approved extracted results with the correct audit record.

#### Platform separation

Some processing can occur within the Azure application:

- OCR and document reading.
- Contextual field extraction.
- PII masking or redaction.
- Basic validation and structured export.

Some downstream tests may need to run on another approved internal platform because they require additional internal data:

- Claims-system records.
- Policy coverage and benefit information.
- Approval-authority tables.
- Historical claims.
- Customer, provider, clinic, or agent data.

Show this architecture:

**Receipt -> Azure Document Intelligence -> PII masking boundary -> Azure OpenAI extraction -> approved structured output -> internal analytics platform -> audit tests -> auditor review**

Key message:

> Run each activity on the platform best suited to its data, risk, and control requirements.

---

### Slide 10: Recommendation and Next Step

**Purpose:** End with one clear recommendation instead of repeating earlier caveats.

Recommended position:

> Continue with Azure Document Intelligence plus Azure OpenAI as the preferred extraction approach, subject to independent validation and governance approval. First establish reliable, traceable receipt extraction. Then use the approved structured output to develop additional audit tests on the appropriate internal platforms.

Next steps:

1. Finalize the required receipt fields and structured-output schema.
2. Confirm the PII-masking and data-flow design.
3. Build an independent and representative validation dataset.
4. Measure accuracy by field, including missing and ambiguous values.
5. Define acceptance criteria for critical fields.
6. Confirm which downstream tests will run in Azure and which will run on other approved internal platforms.

---

## 5. Required Positioning

### Say this

- The current priority is reliable receipt-information extraction.
- The application creates structured, reusable audit data.
- AI achieved the highest accuracy on the project's own development dataset.
- AI reduces dependence on format-specific extraction rules.
- Downstream tests may run on different approved platforms based on their data requirements.
- Independent validation is required before wider use.

### Avoid this

- AI provides complete audit coverage.
- AI replaces auditors.
- The 96.1% result proves production readiness.
- AI eliminates maintenance.
- OCR is unnecessary.
- Receipt data is always correct.
- The application already performs every proposed audit test.
- Every red flag is an audit finding.

---

## 6. Design Instructions

- Keep the main deck to approximately 10 slides.
- Use one main message per slide.
- Use short bullets, process flows, comparisons, and receipt examples.
- Do not repeat governance, human oversight, or pilot caveats across multiple slides.
- Put the key limitation beside the relevant claim.
- Use the benchmark statistics once.
- Clearly label current capability, future testing opportunity, and required validation.
- Keep detailed methodology, validation criteria, and additional test examples in the appendix if needed.

---

## 7. Success Criteria

The new deck should allow the audience to answer:

1. What receipt-data problem is the project solving?
2. What is the proposed solution?
3. What value can reliable extraction bring to Internal Audit?
4. Why does the current manual process limit coverage and efficiency?
5. Why did the AI approach perform better than the alternatives in the development benchmark?
6. What are the practical limitations and trade-offs of each approach?
7. What future control tests and red-flag tests could use the extracted data?
8. How will PII be protected?
9. Why will some downstream tests run on a separate internal platform?
10. What decision and next step are being requested?
