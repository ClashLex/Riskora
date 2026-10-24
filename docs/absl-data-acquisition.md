# ABSL data acquisition

The source manifests, scheme index, reference check, and optional download tools for Aditya Birla Sun Life Flexi Cap research are integrated into this repository. The canonical workbooks and normalized CSVs are in [`data/absl_flexi_cap/`](../data/absl_flexi_cap/README.md). Acquisition scripts are in `scripts/`.

## Current status

- The manifest lists 45 **candidate** monthly AMC archive URLs from January 2023 through September 2026. August and September 2026 were retrieved and checked on 24 October 2026. The other links have not been verified.
- Both downloaded 2026 workbooks match the corresponding normalized Riskora CSVs. The original August workbook was byte-for-byte identical to the downloaded copy. See the [data review](absl-data-review.md).
- The manifest does **not** verify the public release dates. Riskora currently stores the two snapshots as observed, ineligible for model labels.
- A one-day NSE download check produced 83 matching price rows. Those rows have not been imported into Riskora. Historical price coverage is still missing.

The two AMC archive URLs worked with HTTP GET during this review. Earlier HEAD checks returned 404, so a HEAD result alone should not be used to decide that a file is unavailable. The [AMC portfolio page](https://mutualfund.adityabirlacapital.com/forms-and-downloads/portfolio) is the primary source page.

## Portfolio archives

From the repository root:

```powershell
python -m pip install -r backend/requirements.txt
python scripts/download_absl_portfolios.py --from-month 2026-08 --to-month 2026-09
```

Use `--dry-run` to inspect selected manifest URLs without contacting the source. The downloader checks archive formats, validates cached files, limits download and extraction sizes, blocks unsafe ZIP paths, preserves SHA-256 hashes in its log, and stops on HTTP 403 or 429. Archives and extracted workbooks go under ignored `data/absl_flexi_cap/downloads/portfolios/`. Review `download_log.csv`. A successful download does not establish the publication date or that the scheme sheet is comparable with another month.

To collect more periods, change `--from-month` and `--to-month`, inspect each downloaded workbook, and normalize the `BSLEQTY` sheet using `scripts/normalize_absl_xls.py`. The parser validates the workbook layout and will stop if an older workbook differs. Do not import a historical snapshot as complete until its statement coverage and publication date have been checked.

## NSE equity bhavcopies

The NSE tool uses the union of all CSVs under `data/absl_flexi_cap/normalized/` as its default ISIN universe, including stocks that disappeared between August and September. This is still a small, incomplete historical universe; add earlier holdings before a historical market download to reduce survivorship bias. The tool writes one Riskora market CSV per month and preserves downloaded daily ZIPs under ignored `data/absl_flexi_cap/downloads/`.

Start with a narrow date range:

```powershell
python scripts/download_nse_bhavcopy.py --start 2026-10-08 --end 2026-10-08 --dry-run
python scripts/download_nse_bhavcopy.py --start 2026-10-08 --end 2026-10-08
```

Each output row has an optional `source_url` column containing its exact daily archive URL. Riskora's market importer now retains that URL; the import form's batch URL is used only if a row has no URL. Select an output CSV in **Data management → Market prices** and use the [NSE reports page](https://www.nseindia.com/all-reports) as the batch source URL. Raw closes are not adjusted for corporate actions, so return features can be distorted. The exporter keeps these values out of `adjusted_close`.

NSE changed equity bhavcopy format in July 2024; the script chooses the legacy or UDiFF URL based on the observation date. Missing archives and source restrictions are logged. The [NSE reports page](https://www.nseindia.com/all-reports) is the authoritative discovery page.

## Other supplied files

- `data/absl_flexi_cap/reference/scheme_index_2026-09-30.csv` identifies Flexi Cap as AMC code `AB008`, short code `BSLEQTY`.
- `data/absl_flexi_cap/reference/absl_flexicap_2026-08_summary_check.csv` is a partial third-party cross-check. It is not a complete portfolio and must not be imported as one.
- `data/absl_flexi_cap/manifests/data_sources.csv` lists the primary source pages; `absl_monthly_portfolio_manifest.csv` in the same folder lists candidate archive URLs.

Public portfolio statements show reported positions, not orders or execution dates. Verify data use terms, publication dates, completeness, and identifier changes before treating a historical evaluation as evidence of predictive performance.
