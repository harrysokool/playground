# Riley — Master Story (LOCKED FINAL — Revision 6)
_Single source of truth for the written application and the supporting deck. Revision history: rounds 1–3 completed 2026-09-21 (de-risked the back-office population figure, removed an unprovable "no existing tool" claim, softened cross-market scalability wording, added a budget range). Revision 4 (2026-09-23): bolder vision, illustrative impact scenario, explicit platform-vs-Riley differentiation, central multiplier story, award-theme and Double Employee Value links, governance model, and factual corrections to the McKinsey citation, budget and approval-model wording. Revision 5 (2026-09-23): approved sequential timeline and phase gates; auditability added to the design; independent quality sample reviews; FTE framing removed from outward-facing content; scenario wording made explicitly hypothetical; fragmentation premise labelled as an observed problem. Final wording (2026-09-23): approval required before anything is sent to anyone (not only external sends); explicit headcount wording removed from outward-facing content. Revision 6 (2026-09-23, approved by Harry): aligned with application Revision 6 and deck v2 — annual figure (~50,000 hours/year) moved into the outward-facing scenario; future-platform argument added; first pilot workflow selected in Phase 0 rather than defaulting to complaints. **Locked final by Harry — no further story changes unless he explicitly asks.**_

**Evidence labels used throughout:** **[FACT]** confirmed information · **[BENCHMARK]** external, cited source · **[SCENARIO]** illustrative, not a forecast · **[VISION]** long-term ambition · **[HYPOTHESIS]** to be tested in the pilot · **[ASSUMPTION]** applicant's working assumption.

**Locked decisions:** Market = Hong Kong · Submission = individual · Complaints workflow = illustrative example and one possible pilot candidate only, never the definition of Riley; the first live workflow is selected in Phase 0.

---

## 0. Anchor lines

**Vision [VISION]:**
> Every AIA employee has a virtual coworker in Microsoft Teams. They describe the business outcome they need; Riley coordinates AIA's systems, data, AI capabilities and approved external information to complete much of the work — and the employee reviews and approves before anything is finalized.

**Differentiator (the line judges should remember):**
> Riley is not the AI model. Riley is the AIA-specific coworker layer that connects AIA data, systems, AI capabilities, business processes, governance and employee feedback through one employee experience.

Short form: *The platform is the engine. Riley is the AIA coworker built on top of it.* Copilot Studio or another enterprise agent platform can potentially be the underlying engine; the platform is not the core innovation.

**Long-term vision, in full [VISION].** Today, work at AIA is executed by employees moving between systems, documents, colleagues and a growing set of separate AI tools. In the long run, every employee — not only a pilot team, not only the back office — has access to Riley on demand. Most AI capability AIA builds or adopts is reachable through one conversation. Employees spend less of their week gathering, switching and assembling, and more of it on customers, judgment and decisions. Human accountability does not change: the employee owns the outcome, and Riley works within the employee's permissions and AIA's governance.

---

## 1. Category selection (form field 6)

**Employee Value** (primary) **+ Operations Value** (secondary).

---

## 2. Problem statement (form field 7)

**Primary problem — organizational AI fragmentation.** Different teams across AIA are building their own AI tools and solutions for their own needs. **[HYPOTHESIS — an observed organizational problem, based on Harry's direct observation as an AIA employee. No names, counts or specific internal tools are cited, and none may be invented. Outward wording must present this as an observation ("from what I observe…"), not as a measured fact, unless real internal examples are added later.]** For employees, each new tool is one more thing to discover, learn and fit into their work. Completing an end-to-end piece of work means knowing which tool applies, learning it, and manually combining its output with information from other systems and colleagues. That coordination burden falls on the employee however good each individual tool becomes — and it grows with every new tool, unless something sits above them. Another point-solution tool cannot fix this; it only adds to the list.

**Supporting context [BENCHMARK].** McKinsey Global Institute, *The social economy* (2012): interaction workers (high-skill knowledge workers) spend nearly 20% of the workweek looking for internal information or tracking down colleagues who can help with specific tasks. Used only as evidence that information-seeking is a large, real category of work. It is **not** described as time "lost", it does **not** cover "coordinating across systems", and it predates today's AI tools — so it is not evidence of AI fragmentation itself.

**Scale.** Outward-facing wording: "a large back-office population across many functions." Harry's internal working estimate (on the order of a couple thousand employees) is retained as internal context only and is not asserted in the submission. **[ASSUMPTION]**

---

## 3. Illustrative example — not the definition of Riley

> "Review the latest customer complaints, identify the most common issues, compare them with the previous quarter, research relevant external information, prepare a management summary and draft a presentation."

Always framed as "for example" / "one candidate first pilot". It is the main illustration, but the pilot plan does not depend on it: the first live workflow is chosen in Phase 0 (Section 10). The same pattern — research, analysis, reporting, coordination, drafting — applies across back-office functions. Riley is a broad employee capability, not complaints automation.

---

## 4. How Riley works (form field 8, core mechanics)

1. Employee describes the outcome they want, in natural language, in Microsoft Teams.
2. Riley works out what the task needs, drawing only on what the employee is authorized to use: internal AIA data and documents; approved internal systems; AI tools and solutions built by other AIA teams; approved external information sources.
3. Riley plans the work, carries out the steps (research, analysis, drafting), and assembles a finished piece of work.
4. **Approval model:** during the pilot, Riley may plan and execute intermediate steps itself, but the employee reviews, corrects and approves the output **before anything is finalized, sent to anyone, or entered into a business system**. The employee remains accountable for the result. (This is *review before final action* — never described as "human in the loop at every step".)
5. **Traceable work:** Riley keeps an appropriate record of each piece of work — the request, the systems or capabilities used, the output, the employee's approval, and the final action where relevant (Section 12).
6. **Feedback loop — core, not incidental:** corrections, approvals and feedback, captured under governance (Section 12), improve how Riley handles AIA-specific work: understanding requests, choosing the right tools, following business processes and avoiding repeated mistakes.

---

## 5. Differentiation — "Isn't this just Copilot?"

**Position:** Riley does not compete with Copilot or any enterprise agent platform. Riley can be built on Microsoft Copilot Studio, another enterprise agent platform, or future technology. The platform choice is a build decision, not the innovation. Agent technology will keep improving across the industry; Riley benefits from that rather than depending on out-building it.

| The platform provides (engine) | Riley adds (the AIA layer) |
|---|---|
| AI models, agent-building tools, generic connectors | Connections to **AIA data** and **AIA systems** |
| A general-purpose assistant | Access to **AI capabilities built by different AIA teams**, in one place |
| Generic task handling | **AIA business workflows** and how work is actually done here |
| Platform-level security features | **AIA permissions, governance and auditability** applied to every request |
| General model improvements | **Learning from AIA employees' own feedback** |

A generic platform does not arrive knowing AIA. Riley is the AIA-specific coworker layer that brings these together through one employee experience.

**If the platform gets better.** Even if Copilot or another enterprise platform later provides stronger native agent routing and orchestration, AIA still needs to define which AIA data, systems and internal AI capabilities are connected, how employee permissions and AIA workflows apply, how actions are approved and recorded, and how feedback and learning are governed. That AIA-specific layer is Riley. A more capable underlying platform makes Riley more capable, not irrelevant. Riley does not need its own AI model and does not compete with Copilot.

**Three legs of the Creativity argument:**
1. **One coworker, not many tools** — employees learn one way of working, not each team's tool.
2. **A multiplier on AIA's AI investment** — Section 6.
3. **Learns AIA** — the governed feedback loop.

**Removed claim (2026-09-21, unchanged):** "no existing AIA tool unifies internal AI capabilities this way today" — cannot be proven across AIA. Positive framing only: Riley proposes a common employee-facing layer designed to bring these capabilities together.

---

## 6. The AI investment multiplier — central to the idea

**Without Riley:** every new AI solution AIA builds or adopts becomes another separate tool. Each one needs its own discovery, training and adoption effort, and employees must combine them by hand. More AI investment → more fragmentation.

**With Riley:** a new AI capability is connected to Riley and becomes available, through the same conversation, to every employee authorized to use it — increasing what Riley can do without forcing employees to learn another separate tool. More AI investment → a more capable coworker.

**What this does not claim:** connections are not free or automatic. Each one requires technical integration and governance review. The point is that this work is done once per capability, while the employee experience stays unified — one coworker — as the capability underneath grows. **[HYPOTHESIS]**

**How it is tested:** Phase 2 connects at least one AI tool built by a different AIA team and extends Riley to a second workflow. It is the core test of the idea, not an optional extension.

---

## 7. Enduring value (award theme: "Innovation for Enduring Value")

Riley is designed to create compounding value, not a one-time productivity gain — its usefulness can grow as more capabilities, workflows and employee feedback are added over time:
1. **The common layer becomes more useful with every capability connected to it.**
2. **Employee feedback keeps improving** how Riley supports AIA-specific work.
3. **The same layer expands into more workflows and teams over time**, without a new tool each time.
4. **Existing and future AI investments become easier for employees to use**, instead of harder.

Use the theme phrase where it naturally fits (Scalability, closing lines), not everywhere.

---

## 8. Double Employee Value

Riley gives employees more capacity for higher-value work by reducing manual research, information gathering, coordination, system switching and repetitive execution. That capacity moves to customer relationships, judgment, problem-solving and innovation. The framing is **released employee capacity for higher-value work.** No claims are made about specific corporate KPI improvements.

---

## 9. Impact (form field 12)

**Part A — Illustrative scale scenario [SCENARIO — not a forecast or a measured result]:**

**Outward-facing message (use this wording):**

> If Riley eventually served **1,000 employees** and saved each employee an average of **1 hour per week**, it would release approximately **1,000 hours of employee capacity every week**, or around **50,000 hours per year** assuming 50 working weeks — capacity for higher-value work.

- *Framing (internal guidance, not outward wording):* describe impact only as released employee capacity for higher-value work. Headcount-reduction or FTE language must not appear in the application, deck or pitch.
- *Headline:* the weekly 1,000-hour figure is the primary headline; the annual figure (~50,000 hours, 50 working weeks) is part of the same illustrative scenario, used to make scale easier to grasp.
- *1,000 employees* is an illustrative scenario size — **not** a confirmed pilot population and **not** a verified AIA employee count.
- *Reasonableness check (may be used outwardly):* 1 hour is 2.5% of a 40-hour week, and about one-eighth of the ~8 hours/week (nearly 20% of 40 hours) McKinsey estimates knowledge workers spend looking for internal information or tracking down colleagues.
- *Upside [HYPOTHESIS]:* per-employee savings could grow as more capabilities are connected (Section 6).

**Back-pocket for Q&A only — not the main outward message:**
- *Sensitivity:* at 30 minutes/week → ~500 hours/week; at 2 hours/week → ~2,000 hours/week.

**INTERNAL CONTEXT ONLY — do not use in the form, deck or pitch:** at ~2,000 working hours per full-time employee per year, ~50,000 hours ≈ the annual working time of ~25 full-time employees. Excluded outwardly because Riley is not a headcount-reduction idea.

**Part B — Pilot measurement plan (how the scenario is validated):**

| Metric | What it measures | Why it matters |
|---|---|---|
| Active employee effort per completed task | Time the employee actually spends working the task, before vs. after Riley | Direct test of the hours-saved assumption in Part A |
| End-to-end completion time | Elapsed time from request to finished, approved output | Speed of the outcome, not just effort |
| Manual steps / systems touched | Tools and systems previously used manually vs. now handled by Riley | Direct evidence against the fragmentation problem |
| Rework rate | Share of Riley's outputs needing significant correction before approval | Quality, and how fast Riley improves via feedback |
| Quality | Accuracy/completeness vs. a human-only baseline — rated by the requesting employee **and** confirmed through periodic independent sample reviews by an appropriate business reviewer or subject-matter expert | Makes the quality result credible, not self-assessed |
| Adoption | Share of eligible pilot employees using Riley weekly/monthly; repeat use | Evidence employees trust it and choose it |

Phase 3 replaces the Part A scenario with a projection built from measured data.

**Part C — Link to financial metrics [HYPOTHESIS]:** faster, better-supported back-office work plausibly supports operational efficiency, service quality and speed, which can indirectly feed VONB/ANP economics. To be validated with AIA's TDA methodology, not asserted as a number.

---

## 10. Pilot plan & timeline (form field 9)

Phases run in sequence; each phase proceeds only if the previous one shows results.

| Phase | Timing | Milestone / deliverable |
|---|---|---|
| Phase 0 — Validate & select | Month 1 | Select the first live pilot team and workflow, weighing business value, implementation readiness, data sensitivity and governance complexity (customer complaints is one candidate; a lower-sensitivity internal workflow may be chosen if it can prove Riley faster and more safely); baseline effort, completion time and manual steps; confirm data access, security, privacy, audit-record and governance requirements (including feedback governance, Section 12); nominate the independent quality reviewer |
| Phase 1 — MVP pilot | Months 2–4 | Deploy Riley for the workflow selected in Phase 0, with one team; employee approval before final action; measure Part B against the baseline, including independent quality sample reviews. **Go/no-go gate:** proceed only if employee effort is reduced, quality is maintained or improved, and usage is sustained |
| Phase 2 — Prove the multiplier | Months 5–7 | Connect at least one AI tool built by a different AIA team; extend to a second workflow or team. **Go/no-go gate:** the new capability is usable through Riley without a new tool for employees, with effort, quality and usage holding up across both workflows |
| Phase 3 — Scale toward the vision | Months 8–12 | Extend to more back-office teams and connected capabilities; replace the Part A scenario with a measured projection |

---

## 11. Budget logic (form field 11)

**Phase 1 (MVP, ~3 months, one workflow, one team): approximately US$20,000–60,000 incremental cost. [ASSUMPTION — applicant's planning estimate; not AIA-costed and not benchmarked.]** To be replaced with a scoped figure from IT and Finance in Phase 0.
- Assumes Riley is built on an enterprise agent platform AIA already has or adopts, not new agent infrastructure.
- Excludes the time of existing staff (sponsor, pilot users, reviewers). **[ASSUMPTION]**
- Main cost driver: implementation effort to connect the first workflow's systems, plus security, privacy and compliance review.
- Platform licensing depends on the platform chosen and what AIA already licenses. **[FACT — Microsoft public list pricing, checked 2026-09-23]:** Copilot Studio is US$200/month per 25,000-Copilot-Credit capacity pack (pay-as-you-go also available); Microsoft 365 Copilot (enterprise) is US$30/user/month paid yearly, on an annual commitment, and requires a qualifying Microsoft 365 licence. Licensing is not expected to be the main cost driver.

**Removed in Revision 4:** the unsourced "$100,000–$500,000 enterprise AI pilot" and "~$60,000 minimal PoC" benchmarks, and the "$900–$2,700 over 3 months" licensing calculation (incorrect — Microsoft 365 Copilot requires an annual commitment).

**Phases 2–3:** cost scales with each additional capability, workflow and team connected, plus training and change management. To be scoped from Phase 1 results. The award's seed funding would be directed to Phase 1.

---

## 12. Governance — designed for an insurer

Conceptual and practical. No specific memory or training architecture is committed to.

1. **Employee's own access only.** Riley acts with the access the requesting employee is already authorized to use and never bypasses existing permissions.
2. **Data stays under AIA controls.** Sensitive and customer data remain subject to AIA's existing data, privacy and information-security controls. External information comes only from approved sources.
3. **Approval before final action.** During the pilot, Riley may plan and execute intermediate steps itself, but the employee reviews and approves the output before anything is finalized, sent to anyone, or entered into a business system. The employee remains accountable.
4. **Traceable and reviewable (intentional design element, added Revision 5).** Riley keeps an appropriate record of the work it performs: the employee's request, the systems or capabilities used, the output produced, the employee's approval, and the final action where relevant. Record content, retention and access follow AIA's existing policies and are confirmed in Phase 0. No specific logging architecture is committed to.
5. **Governed learning.** What feedback is captured, who can see it, and how improvements are reviewed before they change Riley's behaviour are agreed with risk and IT in Phase 0. The learning mechanism itself is a build decision.
6. **Independent quality checks.** During the pilot, periodic sample reviews by an appropriate business reviewer or subject-matter expert supplement the requesting employee's own review (Section 9, Part B).

---

## 13. Scalability (form field 14)

- **Three directions of scale:** more employees, more workflows, more connected capabilities.
- **Near-term:** a large back-office population across many functions is in scope before any cross-market expansion.
- **Mechanism:** the multiplier (Section 6, tested in Phase 2) — each connected capability becomes available to every authorized employee without rebuilding Riley.
- **Cross-market:** the core Riley experience and orchestration model can be reused across markets, while each market adds its own system integrations, data controls, governance and process configuration. Not a near-free replication.
- **Enduring value:** Section 7.

---

## 14. Feasibility (form field 15)

- Delivered in Microsoft Teams, which employees already use, lowering adoption friction. Trust still has to be earned through reliable results; this is not a claim that there is no adoption curve.
- Built on existing or emerging enterprise AI/agent technology, not a from-scratch engine. Platform left open.
- Starts narrow — one team, one workflow — with each phase gated on measured results.
- Governance designed in from the start (Section 12): employee-level permissions, AIA data controls, approval before final action, traceable work records, governed learning and independent quality checks. **Corrected in Revision 4:** earlier wording "human-in-the-loop at every step" was inaccurate. The actual model is **review and approval before final action**.

---

## Assumptions & sourcing ledger

| # | Item | Type |
|---|---|---|
| 1 | AIA teams are independently building their own AI tools | HYPOTHESIS — observed organizational problem (Harry's direct observation; no names, counts or tools cited) |
| 2 | "A large back-office population across many functions"; internal estimate ~a couple thousand, not stated outwardly | ASSUMPTION |
| 3 | Nearly 20% of the workweek looking for internal information or tracking down colleagues (interaction workers) — McKinsey Global Institute, *The social economy*, 2012 | BENCHMARK |
| 4 | If Riley eventually served 1,000 employees and saved each 1 hour/week → ~1,000 hours/week of released capacity, ~50,000 hours/year over 50 working weeks (1,000 is illustrative, not a pilot size or AIA headcount) | SCENARIO (outward-facing; weekly figure is the headline) |
| 4a | 30-min / 2-hr sensitivity | SCENARIO (Q&A back-pocket only) |
| 4b | ~25 full-time-employee equivalent (2,000 hrs/FTE/year) | INTERNAL CONTEXT ONLY — never outward-facing |
| 5 | Savings may grow as more capabilities connect | HYPOTHESIS |
| 6 | Phase 1 incremental cost ~US$20,000–60,000, excluding existing staff time | ASSUMPTION |
| 7 | Copilot Studio US$200/month per 25,000-credit pack; Microsoft 365 Copilot US$30/user/month, annual commitment | FACT (Microsoft public pricing, checked 2026-09-23) |
| 8 | Link from workflow outcomes to VONB/ANP | HYPOTHESIS |
| 9 | Each capability can be connected once and reused by all authorized employees | HYPOTHESIS (tested in Phase 2) |
| 10 | Cross-market = reusable core + real per-market integration work | ASSUMPTION |
| 11 | No underlying platform, memory or training architecture is committed to | Design decision |
| 12 | Riley becomes available to every AIA employee | VISION |
| 13 | Riley keeps a record of request, capabilities used, output, approval and final action | Design decision (Revision 5); no logging architecture committed |
| 14 | Periodic independent quality sample reviews during the pilot | Design decision (Revision 5) |
| 15 | Sequential timeline (Month 1 / 2–4 / 5–7 / 8–12) and go/no-go gates | Design decision (approved by Harry, Revision 5) |
| 16 | First live pilot workflow chosen in Phase 0 on value, readiness, data sensitivity and governance complexity | Design decision (Revision 6) |
| 17 | A more capable platform makes Riley more capable, not irrelevant | HYPOTHESIS / positioning (Revision 6) |

**Status: LOCKED FINAL Revision 6 (2026-09-23).** Consistent with `application_form_draft.md` Revision 6 and `innovative_idea_award_draft_v2.pptx`. No further story changes unless Harry explicitly asks.
