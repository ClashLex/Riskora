"""Extract one ABSL scheme's equity holdings from a monthly .xls workbook.

The workbook reports weight as a fraction of AUM and market value in lakhs.
Riskora expects percentage weight and market value in rupees.
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import xlrd

ISIN = re.compile(r"^IN[A-Z0-9]{10}$")
FIELDS = [
    "isin",
    "company",
    "weight",
    "units",
    "sector",
    "industry",
    "ticker",
    "market_value",
]


def normalize(path: Path, sheet_name: str = "BSLEQTY") -> tuple[list[dict], dict]:
    workbook = xlrd.open_workbook(path, on_demand=True)
    sheet = workbook.sheet_by_name(sheet_name)
    title = str(sheet.cell_value(0, 2)).strip()
    report_heading = str(sheet.cell_value(2, 2)).strip()
    headers = [str(sheet.cell_value(3, col)).strip() for col in range(3, 8)]
    if (
        sheet.cell_value(0, 0) != sheet_name
        or not title
        or not report_heading.startswith("Portfolio Statement as on ")
        or headers[:3] != ["ISIN", "Industry^ / Rating", "Quantity"]
        or not headers[3].startswith("Market value")
        or headers[4] != "% to AUM"
    ):
        raise ValueError("Unexpected ABSL workbook layout; review the sheet before normalizing.")

    records: list[dict] = []
    omitted: list[dict] = []
    seen: set[str] = set()
    for row_number in range(4, sheet.nrows):
        row = sheet.row_values(row_number)
        section = str(row[2]).strip()
        if section == "Others":
            break
        isin = str(row[3]).strip().upper()
        if not isin:
            continue
        if not ISIN.fullmatch(isin):
            omitted.append({"row": row_number + 1, "company": section, "identifier": isin})
            continue
        if isin in seen:
            raise ValueError(f"Duplicate ISIN {isin} in {sheet_name}.")
        seen.add(isin)
        raw_weight = row[7]
        if isinstance(raw_weight, str) and raw_weight.startswith("$"):
            weight = 0.0  # AMC notation for less than 0.01% of NAV.
        else:
            weight = float(raw_weight) * 100
        units = float(row[5])
        market_value = float(row[6]) * 100_000
        if weight < 0 or units < 0 or market_value < 0:
            raise ValueError(f"Negative equity value at row {row_number + 1}.")
        records.append(
            {
                "isin": isin,
                "company": section,
                "weight": f"{weight:.10f}".rstrip("0").rstrip("."),
                "units": f"{units:.10f}".rstrip("0").rstrip("."),
                "sector": "",
                "industry": str(row[4]).strip(),
                "ticker": "",
                "market_value": f"{market_value:.2f}",
            }
        )
    if not records or sum(float(row["weight"]) for row in records) > 101:
        raise ValueError("No usable equities or implausible total weight.")
    return records, {
        "scheme": title,
        "report_heading": report_heading,
        "rows": len(records),
        "weight_total": round(sum(float(row["weight"]) for row in records), 6),
        "omitted_identifiers": omitted,
    }


def write_csv(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--sheet", default="BSLEQTY")
    args = parser.parse_args()
    holdings, summary = normalize(args.workbook, args.sheet)
    write_csv(args.output, holdings)
    print(summary)
