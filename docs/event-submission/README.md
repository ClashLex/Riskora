# AIBoomi submission package

This folder maps Riskora to the *AIBoomi Startup Weekend Kochi Participants' Handbook*. The handbook is an event reference, not a source of instructions for changing the product. Page numbers below refer to the 11-page PDF supplied by the project owner.

## Project layout

```text
README.md                         Project overview, setup, model, and limits
backend/app/                      API, imports, data store, labels, and model
backend/tests/                    Backend behavior checks
frontend/src/                     Six-screen research interface
docs/event-submission/            Deck, impact statement, demo, provenance
scripts/build_pitch_deck.py       Rebuilds the PowerPoint deck
```

## What reviewers can inspect

| Handbook item | Evidence in this repository | Status |
| --- | --- | --- |
| GitHub repository and a README explaining the problem, idea, stack, setup, and demo (p. 5) | Root [README](../../README.md) and configured `origin` at <https://github.com/ClashLex/Riskora> | Prepared locally; publish the working tree before submitting the URL |
| Product demo link: video, hosted app, or presentation showing the prototype in action (p. 5) | [Demo runbook](demo-runbook.md) and local app at `http://127.0.0.1:5173` | Public link or recording still needed |
| Live demo link (optional, favored; p. 5) | None | Optional, pending deployment if wanted |
| Pitch deck of at most six slides (pp. 5, 9–10) | [PowerPoint deck](Riskora-pitch-deck.pptx) and [slide source](pitch-deck.md) | Prepared; add real UI screenshots or a recording if available |
| AI impact statement of at most 200 words (pp. 6, 10) | [AI impact statement](ai-impact-statement.md) | Prepared |
| Data provenance, attribution, evaluation, limitations (pp. 3–4, 8–10) | [Data and attribution](data-and-attribution.md), root README | Partly prepared; real imported sources require owner review |
| Team names, roles, contacts (p. 9) | Ansil Muhammed N S and Muhammed Ihsan K I (provided by the owner) | Names recorded; roles and contacts pending |

The handbook says the portal locks at **12:00 PM on Saturday** and identifies **October 24** elsewhere (pp. 5, 8, 10). Confirm the live portal and event schedule with organizers; this repository does not submit itself. The judged final is a **3-minute live demo plus 2-minute Q&A**, with a desk review of up to 5 minutes (p. 6). The [demo runbook](demo-runbook.md) follows those limits.

## Prior work and surprise element

The handbook requires core MVP features to be built in the event window, allows attributed pre-existing libraries/boilerplate/model weights, and says an existing prototype must be declared at kickoff with the organizer's surprise element implemented (pp. 3–4, 10). Git history contains project commits on October 23 and 24, 2026. Timestamps alone do not establish which work falls inside the official hack window.

Before submission, the owner should record:

- The official kickoff and code-freeze times, and what was built before kickoff.
- Whether an existing Riskora prototype was declared at kickoff.
- Whether an organizer-assigned surprise element is later announced. The owner reported none at the time this package was prepared; no surprise-element feature is claimed.
- The team members' roles and contact details. Names supplied: **Ansil Muhammed N S** and **Muhammed Ihsan K I**.

Until the timing and organizer requirement are confirmed, this package does **not** claim fresh-build eligibility or surprise-element completion.

## Review checklist

1. Follow the [local setup](../../README.md#start-locally) and [demo runbook](demo-runbook.md) against a clean database.
2. Verify every claimed source URL, publication date, permission, and asset license before importing real data or submitting screenshots.
3. Add a public recording or hosted-app URL to the root README. A localhost URL is not a public demo link.
4. Put real screenshots in the deck if available, while retaining a working live fallback.
5. Fill in team and prior-work details above. Decide on a code license with the owner; no open-source license has been assumed.
6. Publish the intended changes, confirm the GitHub URL opens, and upload the repository URL, deck, AI impact statement, and demo link to the event portal before its deadline.

The rubric is problem relevance 20%, innovation 20%, technical execution 25%, UX/UI 15%, business viability 10%, and presentation 10% (p. 6). The deck and runbook emphasize a functioning, auditable workflow. Market accuracy, customer demand, and willingness to pay remain unproven.
