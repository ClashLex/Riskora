# Demo runbook

Use this with the actual application. The synthetic sample is deliberately fictional; say so before showing any results. Never describe a disclosure-based ranking as a predicted trade or a calibrated probability.

## Prepare before the desk review

1. Start the backend and frontend using the [root README](../../README.md#start-locally). Keep the management token private and enter it only in the local Data management screen.
2. In Data management, choose **Load synthetic sample**. This creates two fictional funds with 15 monthly snapshots each plus fictional market observations. The operation is idempotent for an already loaded sample.
3. In Evaluation, select **Synthetic sample** and **Monthly**, check readiness, then run **Train and evaluate**. Wait for a completed run before the presentation.
4. Open the synthetic fund in Fund explorer, the saved evaluation, Predictions, and a candidate's supporting signals once. Keep a browser tab at Fund explorer for the live sequence.
5. Have the [deck](Riskora-pitch-deck.pptx) and root README available as the fallback if a service stops. The deck contains actual local UI captures, with synthetic views labelled; do not claim the deck is a live demo.

## Three-minute final demo

| Time | Show | Say |
| --- | --- | --- |
| 0:00–0:35 | Fund explorer: a fictional fund's two dated statements and changes | “A statement reports holdings after the fact. Riskora checks comparable, published snapshots before labelling a new addition.” |
| 0:35–1:15 | Evaluation: synthetic dataset selector, readiness, holdout comparison | “The model is compared with simple baselines on later data. These synthetic numbers check the workflow, not Indian-market accuracy.” |
| 1:15–2:10 | Predictions: choose the same sample fund and period, inspect the ranking | “The ranked list is a research shortlist. Scores are uncalibrated; it does not assert that a manager traded.” |
| 2:10–2:40 | Open one company's supporting signals | “Each candidate can be traced to cutoff-dated holdings and market inputs, with source and date information.” |
| 2:40–3:00 | Return to evaluation or slide 6 | “Next: permissioned historical data, real holdouts, and user interviews.” |

For the five-minute desk review, use the same flow and spend the extra time on source validation, unknown labels, publication-aware splitting, and the limitations in the root README. If the browser fails, show the code paths and deck; clearly state which parts were previously verified and which are currently unavailable.

## Likely Q&A

**Does this predict purchases?** No. The target is a new position in a later comparable public disclosure. Trade timing and intent are not observable.

**Is the reported accuracy real?** The bundled sample is fictional. Real-market performance needs permissioned historical disclosures and an independent evaluation.

**Where does AI help?** The structured classifier orders eligible candidates; optional language-model extraction can turn supplied excerpts into grounded event signals. Neither replaces source review.

**Who pays?** A research-team license is a hypothesis. Interviews and a pilot would test whether it creates enough value.
