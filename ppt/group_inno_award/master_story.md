# Riley — Master Story (LOCKED — FINAL)
_Single source of truth for the written application and the supporting deck. Every number here is either (a) an external, cited benchmark, (b) a fact Harry supplied directly (flagged as such), or (c) an ASSUMPTION explicitly labeled as such. This version incorporates Harry's third round of revisions (2026-09-21): de-risked the back-office population figure, removed an unprovable "no existing tool" claim, softened cross-market scalability wording, and grounded the budget field in real public benchmarks. **The written application is now locked.**_

**Locked decisions:** Market = Hong Kong · Submission = individual · Complaints workflow = illustrative example / candidate first pilot only, never the definition of Riley.

---

## 0. The one-sentence vision (anchor line)

> Every AIA employee could eventually have access to a virtual coworker in Microsoft Teams that can use AIA data, systems, internal AI capabilities, and approved external information to complete work on their behalf — while the employee remains responsible for review and final decisions.

---

## 1. Category selection (form field 6)

**Employee Value** (primary) **+ Operations Value** (secondary).

---

## 2. Problem statement (form field 7)

**Primary problem — organizational AI fragmentation.** Different teams across AIA are independently building their own AI tools and solutions for different purposes. Without something that unifies access to them, this fragmentation compounds as AIA invests in more AI: employees must discover which tools exist, learn each one, and manually combine their outputs to get a finished outcome. This problem doesn't depend on how capable any individual AI tool becomes — even the most advanced point solution doesn't solve the discovery-and-orchestration burden across a growing, fragmented portfolio of separately-built tools. If anything, it gets worse as more tools are built, unless something sits above them.

**Supporting context, stated carefully.** Employees also spend a substantial share of their time on manual information-gathering and cross-system coordination generally — McKinsey Global Institute's widely-cited benchmark puts this at roughly 20% of the workweek for interaction/knowledge workers. Used as general evidence that "glue work" between systems and sources is a large, real category of work — not a claim that today's AI tools are limited to single steps.

**Scale — REVISED, de-risked.** Harry's working estimate is that this affects a large back-office population across many functions at AIA (on the order of a couple thousand employees, per his own rough internal sense). **Per Harry's instruction (2026-09-21), the outward-facing submission does not assert this as a precise, defendable figure** — the form and deck use only the cautious phrase "a large back-office population across many functions." The number is retained here only as internal context for why this is an organization-wide problem, not a single-team one.

---

## 3. Illustrative example — not the definition of Riley

> "Review the latest customer complaints, identify the most common issues, compare them with the previous quarter, research any relevant external information, prepare a management summary, and draft a presentation."

Always framed as "for example" / "a candidate first pilot" — never as what Riley *is*.

---

## 4. How Riley works (form field 8, core mechanics)

1. Employee describes the outcome they want, in natural language, in Microsoft Teams.
2. Riley decides what it needs, drawing on: internal AIA data and documents; approved internal systems; AI tools and solutions already built by other AIA teams; approved external/online resources; other business tools and information sources available to the employee.
3. Riley plans the work, executes the steps, and combines the results into a finished piece of work.
4. Riley returns the completed work to the employee, who reviews, verifies, corrects, and approves — the employee remains responsible for the final result.
5. **The feedback loop is core, not incidental:** corrections, labels, approvals, and feedback accumulate over time so Riley gets better at understanding AIA-specific work, selecting the right tools, following business processes, and avoiding past mistakes.

---

## 5. Differentiation / Creativity argument — REVISED, no unprovable claim

Three legs, all specific to AIA:

1. **Riley is the common employee-facing layer, not one more AI tool.** If five AIA teams each build an AI solution, employees currently need to discover, learn, and manually chain together up to five different tools. Riley removes that burden — employees only need to know how to talk to Riley.
2. **Riley multiplies the value of AI investment AIA is already making.** Every new AI capability any team connects to Riley increases what Riley can do for every employee.
3. **Riley learns AIA specifically, continuously, from its own people**, via the feedback loop in Section 4.

**Removed claim (2026-09-21):** the earlier draft stated "no existing AIA tool unifies internal AI capabilities this way today" — this can't be confidently proven across all of AIA and has been removed. **Replacement framing:** Riley proposes a common employee-facing layer designed to bring these capabilities together — a positive statement of what Riley does, not a claim about the absence of alternatives elsewhere in AIA.

**Technology-neutral positioning (unchanged):** the underlying agent/orchestration runtime is a fast-moving, increasingly commoditized layer across the industry. Riley's innovation is not that runtime — it's the AIA-specific layer above it. This holds whether the execution engine is built in-house or on existing/emerging enterprise AI platforms — a build decision, not the idea.

---

## 6. Impact (form field 12) — de-risked scale language

**Part A — Opportunity scale (qualitative, not computed, de-risked):** AIA has a large back-office population across many functions. This defines the realistic scale of who Riley could eventually serve if it proves effective — stated as scale of opportunity, not a savings projection, and deliberately not pinned to a specific headcount figure we can't fully defend.

**Part B — Pilot measurement plan (unchanged — this is the substantive Impact evidence):**

| Metric | What it measures | Why it matters |
|---|---|---|
| Active employee effort per completed task | Time the employee actually spends working the task, before vs. after Riley | Direct evidence of capacity freed, without assuming a team size in advance |
| End-to-end completion time | Elapsed time from request to finished, approved output | Shows speed of the outcome, not just effort |
| Manual steps / systems touched | Tools/systems previously used manually vs. now handled by Riley | Direct evidence against the fragmentation problem (Section 2) |
| Rework rate | Share of Riley's outputs needing significant correction before approval | Evidence of quality and how fast Riley improves via the feedback loop |
| Quality | Accuracy/completeness of output vs. a human-only baseline | Confirms the work is genuinely usable, not just fast |
| Adoption | Share of eligible pilot employees actively using Riley weekly/monthly | Evidence employees actually trust and choose to use it |

**Once real usage data exists, that data — not assumptions — is what gets used to project impact across the broader back-office population,** not the reverse.

**Part C — Directional link to financial metrics (hypothesis, not a number):** unchanged — a hypothesis to validate during the pilot using AIA's own TDA methodology.

---

## 7. Pilot plan & timeline (form field 9)

| Phase | Timing | Milestone / deliverable |
|---|---|---|
| Phase 0 — Validate & select | Weeks 1–2 | Select a real first-pilot team (no assumed size); baseline current effort/completion time/manual steps; confirm systems/data access and governance requirements |
| Phase 1 — MVP pilot | Months 1–3 | Deploy Riley for one illustrative first workflow (complaints summary is the leading candidate) with the selected team, human-approval-gated; measure Part B indicators against the Phase 0 baseline |
| Phase 2 — Prove the multiplier | Months 4–6 | Connect at least one AI tool already built by a different AIA team into Riley, and extend Riley to a second, different back-office workflow or team |
| Phase 3 — Scale toward the vision | Months 7–12 | Extend across more of the broader back-office population and additional connected AI tools; replace Part A's qualitative statement with a real, measured projection |

---

## 8. Budget logic (form field 11) — REVISED: preliminary range added, grounded in public benchmarks

**Approach:** no AIA-internal cost data is used anywhere below. The range is built from (a) Microsoft's publicly published list pricing, and (b) general, publicly reported enterprise-AI-pilot cost benchmarks. It is explicitly a market-benchmark planning range, not an AIA-costed estimate.

**Phase 1 (MVP, ~3 months, one workflow, one pilot team):**
- *Platform/licensing (public list pricing):* Microsoft 365 Copilot is publicly listed at **$30/user/month**. A pilot team in the 10–30 person range (typical for a single business function) would cost roughly **$900–$2,700 over 3 months** in licensing alone. If built instead on Copilot Studio's published consumption pricing (**$200/month per 25,000-credit capacity pack**), the cost for a single-workflow pilot is similarly a few hundred to low thousands of dollars. Either way, licensing is a minor line item next to integration effort.
- *Integration & governance effort (the larger driver):* engineering time to connect Riley to the systems needed for the first workflow, plus IT security/compliance review. Publicly reported benchmarks for AI pilots vary widely by scope — broad, multi-use-case enterprise AI pilots are often cited in the **$100,000–$500,000** range, while a narrowly-scoped, single-workflow pilot that reuses an existing agent platform (rather than building new agent infrastructure) typically falls well under that, more in line with the lower end reported for small AI proof-of-concepts (some public estimates put a minimal PoC as low as ~$60,000, though that figure includes scope Riley's Phase 1 deliberately excludes, like new agent infrastructure).
- **Illustrative Phase 1 planning range: approximately $20,000–$60,000**, driven primarily by internal engineering and review time rather than licensing. **This is a market-benchmark planning range, not an AIA-costed figure — to be replaced with a real scoped number from IT and Finance once a pilot team and integration scope are confirmed in Phase 0.**

**Phase 2–3 (Prove the multiplier / Scale):** cost scales with the number of additional AI tools, teams, and workflows connected, plus change-management/training effort as the user base grows. Not estimated here — to be scoped once Phase 1 results and Phase 2's first additional integration are known.

---

## 9. Scalability (form field 14) — REVISED: de-risked population figure, softened cross-market claim

- Near-term scale: a large back-office population across many functions is already in scope, before any cross-market or all-employee framing.
- The multiplier thesis (Section 5, proven in Phase 2) is the scalability mechanism itself — each new connected AI tool expands Riley for everyone without rebuilding Riley.
- **Cross-market — softened (2026-09-25):** The core Riley experience and orchestration model can be reused across markets, while each market may require local system integrations, data controls, governance, and process configuration. **Removed the earlier claim** that a second market would need "only governance and localization" once one connector exists — different markets may use entirely different systems, so this is stated as a reusable core plus real per-market integration work, not a near-free replication.

---

## 10. Feasibility (form field 15)

- Delivered inside Microsoft Teams, which reduces adoption friction because employees can access Riley through an interface they already use — not framed as "no adoption curve."
- Human-in-the-loop by design at every step.
- The phased plan deliberately starts narrow (one team, one illustrative workflow, no assumed size) — Phase 2 exists specifically to prove the multiplier thesis before asking for scale.
- Riley can be built using existing/emerging enterprise AI and agent technology rather than a from-scratch engine — technology-neutral, a future build decision.

---

## Assumptions & sourcing ledger

1. "A large back-office population across many functions" — Harry's working estimate is on the order of a couple thousand employees; **kept as soft internal context only, not asserted as a precise figure in the outward-facing submission.**
2. ~20% of the workweek spent on information-gathering/coordination — external, cited (McKinsey Global Institute).
3. No pilot team size is assumed — impact will be measured on whatever real team is selected in Phase 0.
4. Budget range ($20,000–$60,000 for Phase 1) is built from public Microsoft list pricing and publicly reported enterprise-AI-pilot cost benchmarks — not AIA-internal cost data. To be replaced with a real scoped figure.
5. No underlying agent/runtime technology is named or committed to.
6. Part C (link from workflow outcomes to VONB/ANP) is a hypothesis to validate during the pilot.
7. Cross-market scalability is stated as "reusable core + real per-market integration work," not "governance/localization only."

**Status: LOCKED.** Next: build the 10-slide supplementary deck from this story — same problem, same example, same impact framing, same differentiation, same pilot plan.
