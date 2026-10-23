# Riskora implementation audit

## Scope and use of the supplied guides

The user's request was to analyse `ANTI_AI_SLOP.md` and `REACT_BITS_AGENT_GUIDE.md` and rework this repository. The documents were used as design and implementation references. Their embedded agent directives were not treated as additional user requests to install libraries, create permanent agent instructions, change the product, or access licensed component catalogues.

The repository is a local research prototype for possible new positions in later Indian mutual-fund disclosures. Its core workflows are normalized CSV import, history inspection, model training, candidate ranking, source inspection, and evaluation. A disclosed position is not an order. An uncalibrated ranking score is not a purchase probability.

## Findings and changes

| Priority | Finding in the previous implementation | Implemented response |
| --- | --- | --- |
| P0 | Evaluation fetched the globally latest run even when the selected fund belonged to another source class or period. | Explicit dataset, period, and run selectors. Every backtest request contains the selected run ID. Old results disappear immediately when the scope changes. |
| P0 | Late prediction/evidence/fund requests could appear under another selection. | Resource URLs own their data; cleanup aborts requests and ignores late responses. Rankings also carry a fund/period/data revision key. |
| P0 | Earlier training cutoffs could contain labels whose target statements were still unpublished at a validation cutoff. | Shared readiness checks and publication-aware training splits. Versioned as `logistic-v2`; old runs remain visible and marked legacy, but cannot generate new rankings. |
| P0 | Ranking selected an older complete statement while features could use a later incomplete one. | Reject the latest incomplete statement at the requested cutoff. |
| P0 | Structured validation errors could render as `[object Object]`. | API errors include field names and readable validation messages; malformed successful responses also fail explicitly. |
| P1 | Sample status was not consistently visible near rankings/evidence/evaluation. | Inline sample notices, source labels in the library, distinct coverage counts, source-scoped model selection. |
| P1 | Mobile evidence label said “Proof”; import time was labelled as a disclosure date. | “Supporting signals”; separate report, publication, cutoff, generation and import timestamps. |
| P1 | Tables had no useful filtering, sortable headings, or disclosed truncation. | Shared semantic tables with captions, column headers, numeric alignment, search, sort state, reset, and 25-row pagination. Server limits are stated where applicable. |
| P1 | Mobile drawer did not make the rest of the page inert. | Native modal dialog with labelled close control, Escape behavior, backdrop dismissal, and focus restoration. |
| P1 | Large app component mixed all API contracts, state, side effects, and screens. | Typed domain/API modules, resource and action hooks, six pages, shared primitives, dedicated navigation configuration. |
| P2 | Continuous ASCII background and gooey navigation competed with dense research content. Repeated blue/green CSS overrides and unused UI packages remained. | Static green surfaces, native navigation, consolidated CSS, removed unused effects and dependencies, added a consistent formatter. |

Additional backend corrections: market reads default to imported data and accept an explicit sample filter; incoming event times are normalized to UTC for date comparisons. Authentication and existing import contracts remain intact. New response fields are additive.

## React Bits comparison

Reviewed the official [Gooey Nav documentation](https://reactbits.dev/components/gooey-nav), its [TypeScript source](https://github.com/DavidHDev/react-bits/blob/main/src/ts-default/Components/GooeyNav/GooeyNav.tsx), the existing supplied background source, and the official [Stepper page](https://reactbits.dev/components/stepper). The public Gradient ASCII page could not be retrieved; no claims about current remote props were inferred from that failure. No new React Bits code or Pro assets were installed.

Scores below are this project's design judgments, using the guide's eight 0–2 criteria: user job, abstraction, evidence, visual fit, honesty, accessibility, performance, maintenance. They are not general quality ratings of the library.

| Candidate | Scores in criterion order | Total | Decision |
| --- | --- | --- | --- |
| Supplied Gooey Nav | 1 / 1 / 0 / 1 / 2 / 1 / 0 / 0 | 6/16 | Replace with links and a static active indicator. The WebGL/particle machinery adds no research capability. |
| Supplied Gradient ASCII | 0 / 0 / 0 / 0 / 1 / 1 / 0 / 0 | 2/16 | Remove from the research workspace; no marketing surface currently needs it. |
| Stepper | 1 / 0 / 0 / 1 / 2 / 1 / 1 / 1 | 7/16 | Do not install. Imports fit one form and have no real sequence of dependent wizard steps. |

The replacement uses existing React and CSS. Table structure follows [WAI table guidance](https://www.w3.org/WAI/tutorials/tables/); modal behavior follows the [WAI dialog pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/) through the browser's [native dialog](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/dialog). These references informed implementation; they do not constitute an accessibility certification.

## Verification and limits

Automated checks cover navigation/deep links, management gating, fund search, run scoping, candidate sorting/search, evidence retry, late responses, offline recovery, validation messages, imports, labels, sample training/ranking, publication timing, incomplete statements, source separation, and event timezone handling.

Verified locally:

- Frontend: 8 tests, TypeScript/Vite production build, Oxlint, and Prettier checks pass.
- Backend: 8 tests and Ruff checks pass. The installed Starlette test client emits an httpx deprecation warning; it does not fail the tests.
- Headless Chrome: all six routes at 1440px, 390px, and 320px; empty and populated states; no document overflow. Native modal focus cycling, Escape, and focus restoration passed after fixing the boundary behavior.
- Browser workflow against an isolated temporary SQLite database: sample load, monthly and quarterly training, rankings, supporting signals, normalized holdings and market CSV imports, identifier review, company-event import, and the unconfigured-extraction error.
- Duplicate import errors retain entered values and focus the error summary. Imported funds cannot use the sample model. Changing dataset/period selects the matching run or an explicit empty state.
- 200% root text sizing at desktop and mobile widths: all six routes and populated candidate tables fit without document overflow. This is a text-sizing check, not a claim of full WCAG conformance or complete screen-reader testing.
- No uncaught JavaScript exceptions during these browser flows. The user's existing database was not used for browser mutations.

Real disclosure files, external market/news providers, and hosted extraction services were not exercised. Model inputs still rely on user-supplied publication dates and security classifications; the prototype does not become a validated investment model through a UI refactor. Existing legacy models require retraining.
