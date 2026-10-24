# Interface audit — 24 October 2026

“AI slop” is an opinion about a result, not a reliable test of how a site was made. In [one Reddit discussion](https://www.reddit.com/r/webdesign/comments/1uhuovu/preventing_the_ai_slop_look/), commenters disagree about whether rounded corners or gradients mean anything on their own. An [indexed X post](https://x.com/nikunj/status/2059775166696366276) likewise calls a handmade design potentially “slop.” Direct X pages returned 403 during this audit, so X search excerpts were treated as limited context rather than verified design guidance.

The useful recurring complaints were more concrete: repeated template layouts and filler copy, decoration unrelated to the task, weak contrast, controls or links with no useful destination, and unclear user journeys. See [Reddit feedback on a generic site](https://www.reddit.com/r/webdesign/comments/1twmqmn/website_was_called_generic_how_to_improve/), [Reddit examples of weak content design](https://www.reddit.com/r/webdesign/comments/1wkj84c/most_aimade_looking_websites/), and [GOV.UK's interface writing guidance](https://www.gov.uk/service-manual/design/writing-for-user-interfaces). A second [indexed X post](https://x.com/damienghader/status/2062156647246475290) advocates a consistent component system; this was consistent with the existing shared UI components, but its full post could not be verified here.

## Changes made

| Problem in Riskora | Change |
| --- | --- |
| An unlinked “Riskora / Research” breadcrumb and repeated page descriptions took space on every screen. | Removed them and gave each page a task-specific heading. |
| Sidebar and footer repeated generic product claims, including the prediction score caveat on unrelated screens. | Removed them. The score caveat remains beside predictions. |
| Fund search and source filters appeared even with zero funds. | Show a plain empty message until funds exist. |
| The empty overview repeated warnings and method notes after its import action. | Show the import action first; show checks and methodology once data exists. |
| Imported and synthetic provenance notices were verbose. | Shortened them while retaining the source-verification and synthetic-performance limits. |
| The fund table showed an arbitrary first 200 change records. | Sort by latest cutoff, return the total count, and disclose truncation in the UI. Results now have readable labels. |
| Secondary text and data tables were small. | Increased the base type size and key label, table, and navigation sizes. Preserved the requested dark green palette. |

No fake performance numbers, decorative animations, gradient backgrounds, or numbered marketing cards were found in the current frontend. Synthetic results remain explicitly labelled. Rounded corners, icons, and dark colors were retained where they support the existing interface; none is evidence of “AI slop” by itself.

## Verification

Frontend build, lint, and 8 tests pass; backend 8 tests pass. Browser checks covered all six routes at 1440, 390, and 320 CSS pixels and at 200% root text size. There was no document overflow or uncaught JavaScript exception. The mobile fund drawer retained keyboard focus and restored focus on close. This check is not a formal accessibility audit; [WCAG contrast guidance](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum) remains the standard for any future palette changes.
