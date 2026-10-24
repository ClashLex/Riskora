# AI impact statement

Riskora uses a scikit-learn logistic classifier to rank stocks that may newly appear in a fund's next comparable disclosed portfolio. It combines prior holdings and cutoff-dated market features, then compares the ranking with historical and sector-preference baselines. Logistic regression is inspectable for a small, structured dataset; its scores are not calibrated probabilities. An optional language model extracts source-checked facts from supplied event excerpts; the core workflow does not require it.

The repository ships fictional synthetic data only. Real holdings and prices must be imported by a user from sources they are permitted to use; source URLs and dates are recorded, but the app does not verify source ownership or licensing. An event extraction must match the supplied ISIN, date, URL, and verbatim excerpt. Training excludes labels whose target disclosure was not published by the evaluation cutoff; incomplete statements yield unknown cases rather than negatives. Walk-forward and final holdout results are shown separately.

The intended benefit is an auditable research shortlist. Real-market accuracy and commercial value have not been established. Outputs do not establish actual trades and are not investment advice.

*Word count: 180 (statement text only).*
