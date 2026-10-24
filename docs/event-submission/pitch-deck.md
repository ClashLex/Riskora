# Riskora pitch deck

The [PowerPoint deck](Riskora-pitch-deck.pptx) has **six slides**, matching the limit recorded in the [handbook summary](README.md). Its speaker notes cover a three-minute presentation and likely questions for the two-minute Q&A. Use the [demo runbook](demo-runbook.md) to show the app live; the deck is supporting material.

The deck is generated from [the Python source](../../scripts/build_pitch_deck.py) and three screenshots captured from the working local app on 24 October 2026. Rebuild it from the repository root with:

```powershell
python -m pip install python-pptx
python scripts/build_pitch_deck.py
```

| Slide | Speaking point | Evidence and limits |
| --- | --- | --- |
| 1. Working MVP | Riskora turns dated fund disclosures into a traceable research shortlist. | Actual app screenshot of an observed ABSL Flexi Cap statement. Its public release date remains unverified. |
| 2. Problem and insight | Late publication, incomplete statements, and absent holdings require different treatment. Unknown cases stay unknown. | The target is a new position in a later comparable statement, not a purchase order or trade date. |
| 3. Product demonstration | Inspect holdings, review evaluation, rank candidates, and open supporting evidence. | Actual app screenshot of the **fictional synthetic sample**, labelled on the slide. The ranking score is relative, not a calibrated probability. |
| 4. AI and technical execution | Source validation and point-in-time features feed a logistic classifier; later-period checks and a final holdout compare it with simple baselines. | Actual synthetic evaluation screenshot. The displayed holdout has 14 cases and 2 additions; it does **not** establish Indian-market predictive accuracy. Optional LLM extraction is unconfigured in this demo. |
| 5. Value and viability | Test whether an auditable shortlist saves analyst time and improves research review. | Research-team licensing is a hypothesis. No customer interviews, paying users, or willingness-to-pay evidence are claimed. |
| 6. Proof and next steps | The app, CSV import, observed disclosure review, and synthetic model run work today. Ask for two research teams and permissioned historical data for a measured pilot. | Release dates and data-use rights need verification; real-market holdouts and user testing remain to be done. |

The deck covers the handbook's judging areas: problem relevance (slides 1–2), innovation (2–3), technical execution (3–4), UX/UI (1 and 3), business viability (5–6), and presentation (the three-minute notes and live runbook). Team names in the file are Ansil Muhammed N S and Muhammed Ihsan K I; the notes identify Ansil's frontend and interface work and Ihsan's backend, data, and event implementation work. The [live synthetic demo](https://riskora-demo.onrender.com/) is linked on slide 6. The separate [AI impact statement](ai-impact-statement.md) and event eligibility details remain separate submission items.
