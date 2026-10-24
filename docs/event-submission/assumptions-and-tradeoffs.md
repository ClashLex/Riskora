# Assumptions and trade-offs

These are implementation decisions in the current prototype, not validated business facts.

| Decision | Reason | Cost or remaining test |
| --- | --- | --- |
| Predict a **new disclosed position** | A later portfolio statement is observable and can define a label | It cannot reveal a trade, trade date, or manager intent |
| Require comparable, complete statement pairs | Absence is meaningful only when the earlier statement is complete | User attestation and weight totals are imperfect completeness checks |
| Restrict candidates and features to cutoff-known data | Avoid making a historical prediction using later information | A limited known universe can miss genuinely new securities |
| Use user-normalized CSV rather than automatic scraping | Keeps the first prototype source-agnostic and reviewable | Import is manual; original formats and licenses require separate review |
| Keep fictional sample separate from user imports | Makes the full workflow demoable without real data | Sample metrics say nothing about Indian-market performance |
| Use logistic regression and simple baselines | Training and contributions can be inspected | Nonlinear patterns may be missed; scores are not calibrated |
| Make language-model extraction optional | Holdings ranking works without hosted credentials | Event features are unavailable unless configured and validated |
| Use SQLite and a management token | Low setup cost for an in-person or hosted demo | No multi-user access controls; the free hosted demo sleeps and its database is ephemeral |

The next evidence gates are permissioned source files, publication-date audits, real held-out evaluation across funds and periods, and interviews with intended users. No commercial value or predictive accuracy is assumed before those gates.
