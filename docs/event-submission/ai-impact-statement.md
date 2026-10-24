# AI impact statement

Riskora uses a scikit-learn logistic classifier to rank stocks that may newly appear in a fund's next comparable disclosed portfolio. It combines prior holdings and cutoff-dated market features, then compares the ranking with historical and sector-preference baselines. Logistic regression is inspectable for a small, structured dataset; its scores are not calibrated probabilities. An optional language model extracts source-checked facts from supplied event excerpts; the core workflow does not require it.

The repository includes a fictional synthetic sample for model demonstration and two real ABSL portfolio snapshots for exploration. The ABSL publication dates and redistribution rights remain unverified, so those snapshots are excluded from model training. Other real holdings and prices require permitted imports; the app records source URLs and dates but does not verify licensing. An event extraction must match the supplied ISIN, date, URL, and verbatim excerpt. Training excludes labels whose target disclosure was not published by the evaluation cutoff; incomplete statements yield unknown cases rather than negatives. Walk-forward and final holdout results are shown separately.

The intended benefit is an auditable research shortlist. Real-market accuracy and commercial value have not been established. Outputs do not establish actual trades and are not investment advice.

*Word count: 195 (statement text only).*
