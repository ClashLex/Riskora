# AIBoomi submission package

This folder maps Riskora to the *AIBoomi Startup Weekend Kochi Participants' Handbook*. The handbook is an event reference, not a source of instructions for changing the product. Page numbers below refer to the 11-page PDF supplied by the project owner.

## Project layout

```text
README.md                         Project overview, setup, model, and limits
backend/app/                      API, imports, data store, labels, and model
backend/tests/                    Backend behavior checks
frontend/src/                     Six-screen research interface
docs/event-submission/            Editable deck, impact statement, demo, provenance
```

## What reviewers can inspect

| Handbook item | Evidence in this repository | Status |
| --- | --- | --- |
| GitHub repository and a README explaining the problem, idea, stack, setup, and demo (p. 5) | Root [README](../../README.md) and public repository at <https://github.com/ClashLex/Riskora> | Public repository reachable; push the final local revision before submitting the URL |
| Product demo link: video, hosted app, or presentation showing the prototype in action (p. 5) | [Live synthetic demo](https://riskora-demo.onrender.com/) and [demo runbook](demo-runbook.md) | Available; homepage, API, and sample ranking checked on 24 October 2026 |
| Live demo link (optional, favored; p. 5) | [Riskora on Render](https://riskora-demo.onrender.com/) | Available; free service may take time to wake |
| Pitch deck of at most six slides (pp. 5, 9–10) | [PowerPoint deck](Riskora-pitch-deck.pptx) and [slide guide](pitch-deck.md) | Prepared with six slides, a labelled schematic interface, and speaker notes; the live demo link is supplied separately |
| AI impact statement of at most 200 words (pp. 6, 10) | [AI impact statement](ai-impact-statement.md) | Prepared |
| Data provenance, attribution, evaluation, limitations (pp. 3–4, 8–10) | [Data-source register](../../DATA_SOURCES.md), [data and attribution](data-and-attribution.md), root README | Sources documented; ABSL release dates and redistribution rights remain unverified |
| Team names, roles, contacts (p. 9) | Ansil Muhammed N S: frontend and interface; Muhammed Ihsan K I: backend, data, and event implementation | Names and roles recorded; owner says public contact details are not needed |

The handbook says the portal locks at **12:00 PM on Saturday** and identifies **October 24** elsewhere (pp. 5, 8, 10). Confirm the live portal and event schedule with organizers; this repository does not submit itself. The judged final is a **3-minute live demo plus 2-minute Q&A**, with a desk review of up to 5 minutes (p. 6). The [demo runbook](demo-runbook.md) follows those limits.

## Prior work and surprise element

The handbook requires core MVP features to be built in the event window, allows attributed pre-existing libraries/boilerplate/model weights, and says an existing prototype must be declared at kickoff with the organizer's surprise element implemented (pp. 3–4, 10). The owner reports that the idea changed repeatedly before the team settled on Riskora and built its current version on 24 October 2026. Git history also contains related exploratory commits on 23 October. These earlier commits should be disclosed accurately; timestamps alone do not establish which work falls inside the official hack window.

Before submission, the owner should record:

- The official kickoff and code-freeze times, which the owner has not supplied.
- How organizers want the related 23 October exploratory work reported. The owner says no earlier prototype was declared at kickoff.
- Whether organizers subsequently announce a surprise element. The owner reports none was assigned when asked; no surprise-element feature is claimed.
- Private contact details in the event portal only if the organizers request them; the owner says only project roles need to appear here.

Until the timing and organizer requirement are confirmed, this package does **not** claim fresh-build eligibility or surprise-element completion. The team roles and external component attribution are recorded in the root README and [third-party notices](../../THIRD_PARTY_NOTICES.md).

## Review checklist

1. Follow the [local setup](../../README.md#start-locally) and [demo runbook](demo-runbook.md) against a clean database.
2. Verify every claimed source URL, publication date, permission, and asset license before importing real data or submitting screenshots.
3. Recheck the [hosted demo](https://riskora-demo.onrender.com/) just before judging; keep the local setup as a fallback if the free service is waking or unavailable.
4. Rehearse the live app and the deck's speaker notes within the three-minute limit. The deck uses diagrams and a labelled schematic interface; keep the live app ready to show the working product.
5. Confirm the prior-work details above with organizers. The team's original code uses [MIT](../../LICENSE); adapted React Bits components and AMC data have separate rights.
6. Publish the intended changes, confirm the GitHub URL opens, and upload the repository URL, deck, AI impact statement, and demo link to the event portal before its deadline.

The rubric is problem relevance 20%, innovation 20%, technical execution 25%, UX/UI 15%, business viability 10%, and presentation 10% (p. 6). The deck and runbook emphasize a functioning, auditable workflow. Market accuracy, customer demand, and willingness to pay remain unproven.
