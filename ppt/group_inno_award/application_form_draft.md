# Riley — Innovation Idea Awards Application (LOCKED — FINAL)
_Locked from [master_story.md](master_story.md) on 2026-09-25. Fields numbered exactly as in the official form ([submission_form.txt](submission_form.txt)) so you can copy each answer straight across. [BRACKETS] are placeholders I can't fill in for you._

---

### 1. Full Name
[YOUR FULL NAME]

### 2. Which market are you representing?
Hong Kong

### 3. Department
[YOUR DEPARTMENT / FUNCTION]

### 4. Email
[YOUR AIA EMAIL ADDRESS]

### 5. Title
Riley: AIA's Virtual Coworker

### 6. Category
Employee Value; Operations Value

---

### 7. Problem Statement

Across AIA, different teams are independently building their own AI tools and solutions — each one solving a specific problem for a specific group. As this continues, it creates a second, compounding problem: employees don't have a single way to find, learn, and use the AI capabilities already built for them. To complete an end-to-end piece of work, an employee often needs to know which tool applies, learn how to use it, and manually combine its output with results from other tools and systems — work that falls entirely on the employee, no matter how good any individual AI tool becomes.

This is a structural problem, not a single-workflow annoyance, and it is not solved by building another point-solution AI tool — that only adds one more tool to the list employees must discover and learn. It affects a large back-office population across many functions at AIA, all of whom face some version of the same burden: knowing what AI capability exists, where, and how to use it for the outcome they actually need.

This also compounds a more general, well-documented cost. McKinsey Global Institute research estimates that interaction and knowledge workers spend roughly 20% of the workweek — nearly a full day — searching for and gathering information and coordinating across systems. That is general evidence of how much "glue work" already exists between systems and sources; it becomes worse, not better, every time a new AI tool is added without a common way for employees to reach it.

### 8. Proposed Solution

Riley is AIA's virtual coworker: an AI colleague employees talk to naturally inside Microsoft Teams, the way they would message a colleague, to get an outcome completed rather than a single task performed.

An employee describes the outcome they want — for example: "Review the latest customer complaints, identify the most common issues, compare them with the previous quarter, research any relevant external information, prepare a management summary, and draft a presentation." Riley decides what it needs to complete this: internal AIA data and documents, approved internal systems, AI tools and solutions already built by other AIA teams, approved external/online resources, and other business tools available to the employee. Riley plans the work, executes the necessary steps, and combines the results into a finished piece of work. The employee remains responsible for the outcome throughout: they review, verify, correct, and approve Riley's work before anything is finalized. This example is illustrative — a candidate first pilot, not the definition of what Riley does.

The feedback loop is central to the idea, not a safety add-on. Every correction, approval, and piece of feedback an employee gives helps Riley get better at understanding AIA's specific work, selecting the right tools, following AIA's business processes, and avoiding mistakes it has made before — so Riley becomes a more capable colleague the longer it works at AIA.

What makes this different from building another AI tool, and different from a generic AI assistant, is not that Riley can complete multi-step work — agent technology broadly is moving quickly in that direction across the industry, and Riley's value should not depend on staying ahead of that curve. The innovation is the AIA-specific layer above it:

- **A common employee-facing layer.** Instead of employees discovering and learning each team's individual AI tool, they only need to know how to talk to Riley.
- **A multiplier on AIA's own AI investment.** Every new AI capability any team connects to Riley increases what Riley can do for every employee — Riley's value compounds with AIA's innovation activity instead of competing with it.
- **A coworker that learns AIA, specifically, over time**, through the accumulated feedback loop described above.

Riley proposes a common employee-facing layer designed to bring these capabilities together. Riley can be built using existing or emerging enterprise AI and agent technology rather than a from-scratch engine — the underlying runtime is a fast-moving, increasingly commoditized layer across the industry, and is intentionally left as a future build decision rather than a claim in this proposal. The idea is the common, governed, continuously-learning coworker layer connecting AIA's data, systems, internal AI capabilities, and approved external information — not the engine underneath it.

---

### 9. Timeline

**Phase 0 — Validate & select (Weeks 1–2):** Select a real first-pilot team; baseline current effort, completion time, and manual steps for the target workflow; confirm systems/data access and governance requirements with IT security and compliance.

**Phase 1 — MVP pilot (Months 1–3):** Deploy Riley for one illustrative first workflow (the customer-complaints example is the leading candidate) with the selected team, with every output human-approval-gated. Measure the workflow-level indicators below against the Phase 0 baseline.

**Phase 2 — Prove the multiplier (Months 4–6):** Connect at least one AI tool already built by a different AIA team into Riley, and extend Riley to a second, different back-office workflow or team. This phase exists specifically to prove that Riley resolves AIA's AI-fragmentation problem in practice — it is the core of the idea, not an optional extension.

**Phase 3 — Scale toward the vision (Months 7–12):** Extend across more of AIA's back-office population and additional connected AI tools; replace the qualitative opportunity-scale statement in the Impact section with a real, measured projection built from Phase 1–2 data.

### 10. Resources

Submitted as an individual idea. To execute, this would need:

- **A pilot business-unit sponsor** in Hong Kong willing to host Phase 0–1 with a real team.
- **A small build pod**, assembled during Phase 0: a product/business owner (this applicant), an AI/automation engineer or implementation partner, and part-time support from an IT security/compliance reviewer.
- **Group Innovation Office mentorship and support**, as offered to shortlisted finalists under the award program itself.
- **Access to relevant system and data owners** for the systems Riley would need to connect to during the pilot.
- **Access to whatever enterprise AI/agent platform capability AIA already has, is evaluating, or chooses to adopt**, so the pilot is not spent building an agent runtime from scratch.

### 11. Budget

This estimate uses only public, externally sourced benchmarks — no AIA-internal cost data — and is presented as a preliminary planning range, to be replaced with a real scoped figure once Phase 0 confirms a pilot team and integration scope.

**Phase 1 (MVP, ~3 months, one workflow, one pilot team):**

- *Platform/licensing:* Microsoft 365 Copilot is publicly listed at $30/user/month. A pilot team in the 10–30 person range (typical for a single business function) would cost roughly $900–$2,700 over 3 months in licensing alone. An alternative, Copilot Studio's published consumption pricing ($200/month per 25,000-credit capacity pack), lands in a similar range for a single-workflow pilot. Licensing is a minor cost line either way.
- *Integration & governance effort:* the larger cost driver is engineering time to connect Riley to the systems needed for the first workflow, plus IT security and compliance review. Publicly reported AI pilot costs vary widely by scope: broad, multi-use-case enterprise AI pilots are often cited in the $100,000–$500,000 range, while a narrowly-scoped, single-workflow pilot that reuses an existing agent platform (rather than building new agent infrastructure) typically costs substantially less.
- **Illustrative Phase 1 planning range: approximately $20,000–$60,000**, driven mainly by internal engineering and review time rather than licensing. This is a market-benchmark planning range, not an AIA-costed estimate.

**Phase 2 (Prove the multiplier) and Phase 3 (Scale):** cost scales with the number of additional AI tools, teams, and workflows connected, plus change-management and training effort as the user base grows. Not estimated here — to be scoped once Phase 1 results and Phase 2's first additional integration are known.

### 12. Impact

Rather than presenting a single headline savings figure built on stacked assumptions, this submission takes a deliberately conservative approach: AIA has a large back-office population across many functions. This defines the realistic scale of opportunity if Riley proves effective — stated here as the scale of the opportunity, not converted into a projected hours-saved or FTE-capacity number, because doing so would require several unproven assumptions stacked into a figure that would look more precise than the evidence currently supports.

Instead, Impact will be demonstrated through a workflow-level measurement plan, applied to the real pilot team selected in Phase 0:

- **Active employee effort per completed task** — time the employee actually spends working the task, before vs. after Riley.
- **End-to-end completion time** — elapsed time from request to finished, approved output.
- **Manual steps / systems touched** — number of separate tools an employee previously used manually vs. now handled by Riley, directly evidencing the fragmentation problem being solved.
- **Rework rate** — share of Riley's outputs needing significant correction before approval, and how quickly this improves via the feedback loop.
- **Quality** — accuracy/completeness of output vs. a human-only baseline, assessed by the reviewing employee.
- **Adoption** — share of eligible pilot employees actively using Riley weekly/monthly, and repeat-usage rate.

These are real, measurable indicators from Phase 1 — not assumptions. Once this data exists, it — not a pre-built model — is what will be used to project Riley's impact across AIA's broader back-office population in Phase 3.

Directionally, faster and better-supported work in back-office functions plausibly supports operational efficiency and, indirectly, factors that feed AIA's VONB/ANP economics (e.g., service quality, persistency). This submission treats that link as a hypothesis to validate during the pilot, using AIA's own TDA reporting methodology, rather than a number to assert now.

### 13. Creativity

Riley's originality isn't a claim about out-building the broader agent-technology market — that layer is evolving quickly across the industry and will keep improving regardless of what AIA builds. Riley's originality is in being AIA's own common employee-facing coworker: the layer that unifies AIA's data, systems, and — critically — the growing set of AI capabilities AIA's own teams are already building, so that every new AI investment compounds Riley's value instead of adding one more tool employees have to learn on their own. A continuously-learning feedback loop tuned specifically to AIA's own processes and mistakes is not something available in a generic, off-the-shelf assistant. **Riley proposes a common employee-facing layer designed to bring these capabilities together** — addressing a fragmentation problem that grows, not shrinks, as more point-solution AI tools are built across the sector.

### 14. Scalability

A large back-office population across many functions is already in scope, before any cross-market framing. Beyond that: the multiplier mechanism proven in Phase 2 (connecting another team's AI tool into Riley) is itself the scalability mechanism — each new connected AI capability expands what Riley can do for every employee, without Riley needing to be rebuilt. **The core Riley experience and orchestration model can be reused across markets, while each market may require local system integrations, data controls, governance, and process configuration** — different markets may run different systems, so cross-market scale is treated as reusable core plus real local integration work, not a near-free replication.

### 15. Feasibility

Riley is delivered inside Microsoft Teams, which reduces adoption friction because employees can access it through an interface they already use — not a claim that there is no adoption curve at all, since trust and habitual use still need to be earned through real, reliable results. Every output is reviewed and approved by the employee before any action is taken, addressing the most obvious risk and governance objection directly. The rollout plan deliberately starts narrow — one real team, one illustrative workflow, no assumed team size — so the broader vision is proven step by step rather than taken on faith; Phase 2 exists specifically to prove the multiplier thesis before any request for scale. Riley can also be built on existing or emerging enterprise AI/agent technology rather than a from-scratch engine, reducing net-new engineering risk — the specific underlying platform is a build decision left open in this submission, not a commitment made here.
