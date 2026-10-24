# Supplied ABSL Flexi Cap data review

Reviewed 24 October 2026. This records what is present in this workspace and what the application can safely infer from it.

| Report date | File | Usable Indian-ISIN equity rows | Weight total | SHA-256 |
| --- | --- | ---: | ---: | --- |
| 31 Aug 2026 | `data/absl_flexi_cap/raw/31082026_ABSLMF_MonthlyDisclosure.xls` → `data/absl_flexi_cap/normalized/ABSLMF_BSLEQTY_2026-08-31.csv` | 84 | 98.4452% | CSV `ca095ecd813c2a2bc2352c736a1ed327a0775ccd1d068bbaddb5b8b85a0cf796` |
| 30 Sep 2026 | `data/absl_flexi_cap/raw/30092026_ABSLMF_MonthlyDisclosure.xls` → `data/absl_flexi_cap/normalized/ABSLMF_BSLEQTY_2026-09-30.csv` | 82 | 97.8734% | CSV `cddfef993085a60081bae3636b3a91fdd3bd5774b1a549c0bb00effc5be33614` |

The August workbook SHA-256 is `68a8279d8c7c2f1d259784664827837eba260983d69fbc06646e860c45206dc8`; September's is `8eb8ef4f1a34084f1ed8b29080a563f11e8c5780e8e935598d7d2dde045faac7`. The August workbook's `Index` sheet maps code `AB008` and short code `BSLEQTY` to **ADITYA BIRLA SUN LIFE FLEXI CAP FUND**. The `BSLEQTY` sheets state their respective month-end report dates. The parser reads only the equity section. It converts workbook `% to AUM` fractions to percentage points and `Rs. in Lakhs` market values to rupees. Each workbook has two zero-weight unlisted rows with valid Indian ISINs. Each also has one zero-value unlisted row, Magnasound (India) Pvt Ltd., with identifier `IDIA00028484`, which fails Riskora's Indian ISIN format check and is omitted. Cash, reverse repo, and other assets are outside the equity import.

Both CSVs match their source workbook on ISIN, company, industry, weight, units, and market value. The August workbook downloaded from the AMC archive is byte-for-byte identical to the previously supplied file; the September workbook was retained in `raw/` after its CSV was checked. The September CSV has no duplicate ISINs and no conflicting company names for ISINs shared with August. `sector` and `ticker` are blank in both files; AMC industry classifications are retained in `industry`.

## Month-to-month descriptive comparison

The two files share 80 ISINs. September contains two ISINs absent from August: Cipla Ltd. (0.6785% weight) and Travel Food Services Ltd. (0.0287%). Four August ISINs are absent from September: Sun Pharmaceutical Industries Ltd., Havells India Ltd., Avenue Supermarts Ltd., and Tube Investments of India Ltd. Among the 80 shared ISINs, 18 have more than 1% higher unit counts, 53 have unchanged units, and nine have fewer units. These are differences between reported snapshots, not observed orders or proof of a manager's intent. The 0.1% default materiality threshold would include Cipla and exclude Travel Food Services if the pair later becomes comparable.

## Provenance and model eligibility

The [acquisition tools](absl-data-acquisition.md) contains a 45-month URL manifest and download scripts. Its August and September 2026 AMC archive URLs worked with GET on 24 October 2026, although earlier HEAD requests returned 404. Archive SHA-256 values are `30a2b953a6d518b3653ff7b5f08f8ffa48591c0841d9abc5572b784b91f5f47e` (August) and `529d07916e835e3d97fab4c039cdff704008e68b7c9846e886975f6460611596` (September). Other manifest URLs have not been verified. A single NSE bhavcopy day was also downloaded as an adapter check and yielded 83 matching observations; it was not imported into the application. Downloaded archives and prices are under ignored `data/absl_flexi_cap/downloads/`. The manifest's publication-date fields remain explicitly unverified. Neither the archive ZIP entry timestamps nor the [AMC portfolio page](https://mutualfund.adityabirlacapital.com/forms-and-downloads/portfolio) establish the first public release date.

`scripts/load_supplied_disclosures.py` loads these snapshots into the local database with `availability_basis=observed` and the script run date as a conservative availability cutoff. It marks both snapshots incomplete for labeling, even though their equity weights exceed 90%. This allows the Fund explorer to show the positions without creating false positive or negative training examples. The local readiness check reports **zero usable periods**. A real model evaluation needs additional consecutive snapshots, verified publication dates and completeness, and point-in-time market observations across the candidate universe. The secondary-source August summary in `data/absl_flexi_cap/reference/` is a cross-check only; it is not a full snapshot.

To inspect normalization without replacing the canonical CSVs after installing backend requirements:

```powershell
python scripts/normalize_absl_xls.py data/absl_flexi_cap/raw/31082026_ABSLMF_MonthlyDisclosure.xls data/absl_flexi_cap/downloads/normalized_check/ABSLMF_BSLEQTY_2026-08-31.csv
python scripts/normalize_absl_xls.py data/absl_flexi_cap/raw/30092026_ABSLMF_MonthlyDisclosure.xls data/absl_flexi_cap/downloads/normalized_check/ABSLMF_BSLEQTY_2026-09-30.csv
```
