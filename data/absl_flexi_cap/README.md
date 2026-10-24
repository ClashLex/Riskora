# ABSL Flexi Cap supplied disclosures

- `raw/` holds the August and September 2026 AMC `.xls` workbooks.
- `normalized/` holds Riskora-format holdings CSVs for August and September 2026.

From the repository root, run `python scripts/load_supplied_disclosures.py` to load both snapshots into the local database. The loader checks that each CSV still matches its workbook. Exact publication dates remain unverified, so these snapshots are available for browsing but excluded from model labels. The [acquisition tools](../../docs/absl-data-acquisition.md) write future downloads under `downloads/`, which is ignored by Git. Candidate URLs and source pages are in `manifests/`; the scheme index and partial August cross-check are in `reference/`.

See [the data review](../../docs/absl-data-review.md) for row counts, conversion details, hashes, and the month-to-month comparison.

The [data-source register](../../DATA_SOURCES.md) records the original URLs and rights status. Exact public release dates and permission to redistribute the original workbooks or screenshots remain unverified; the repository's MIT license does not cover AMC material.
