#!/usr/bin/env python3
"""Download candidate ABSL monthly portfolio archives from the supplied manifest."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import stat
import time
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

import requests

LANDING = "https://mutualfund.adityabirlacapital.com/forms-and-downloads/portfolio"
ALLOWED_HOSTS = {"mutualfund.adityabirlacapital.com", "abcscprod.azureedge.net"}
MAX_DOWNLOAD = 50 * 1024 * 1024
MAX_EXTRACTED = 500 * 1024 * 1024
MAX_MEMBERS = 500
HEADERS = {
    "User-Agent": "RiskoraResearchDataAcquisition/1.0 (local research)",
    "Referer": LANDING,
    "Accept": "*/*",
}


def project_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "backend" / "app").is_dir():
            return parent
    raise RuntimeError("Run this script inside the Riskora project.")


def check_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS or parsed.username:
        raise ValueError(f"Unexpected portfolio source URL: {url}")


def read_limited(response: requests.Response) -> bytes:
    chunks = []
    size = 0
    for chunk in response.iter_content(chunk_size=1024 * 1024):
        size += len(chunk)
        if size > MAX_DOWNLOAD:
            raise ValueError("Portfolio archive exceeds the 50 MB download limit.")
        chunks.append(chunk)
    return b"".join(chunks)


def valid_archive(data: bytes, suffix: str) -> bool:
    if suffix == "zip":
        return zipfile.is_zipfile(io.BytesIO(data))
    if suffix == "xls":
        return data.startswith(bytes.fromhex("D0CF11E0A1B11AE1"))
    return False


def safe_extract_zip(data: bytes, target: Path) -> None:
    """Reject unsafe entries before writing any files."""
    accepted = []
    total = 0
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        members = archive.infolist()
        if len(members) > MAX_MEMBERS:
            raise ValueError("Portfolio ZIP contains too many entries.")
        for member in members:
            raw_name = member.filename.replace("\\", "/")
            path = PurePosixPath(raw_name)
            mode = member.external_attr >> 16
            if (
                path.is_absolute()
                or not path.parts
                or any(part in {".", ".."} for part in path.parts)
                or ":" in path.parts[0]
                or stat.S_ISLNK(mode)
            ):
                raise ValueError(f"Unsafe portfolio ZIP entry: {member.filename}")
            total += member.file_size
            if total > MAX_EXTRACTED:
                raise ValueError("Portfolio ZIP exceeds the 500 MB extracted size limit.")
            accepted.append((member, path))
        target.mkdir(parents=True, exist_ok=True)
        root = target.resolve()
        for member, path in accepted:
            destination = target.joinpath(*path.parts).resolve()
            if not destination.is_relative_to(root):
                raise ValueError(f"Unsafe portfolio ZIP destination: {member.filename}")
            if member.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, destination.open("wb") as output:
                while chunk := source.read(1024 * 1024):
                    output.write(chunk)


def download(argv: list[str] | None = None) -> list[dict]:
    data_dir = project_root() / "data" / "absl_flexi_cap"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=data_dir / "manifests" / "absl_monthly_portfolio_manifest.csv",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=data_dir / "downloads" / "portfolios",
    )
    parser.add_argument("--from-month", default="2023-01", help="inclusive YYYY-MM")
    parser.add_argument("--to-month", default="2026-09", help="inclusive YYYY-MM")
    parser.add_argument("--no-extract", action="store_true")
    parser.add_argument("--sleep", type=float, default=0.3, help="seconds before each request")
    parser.add_argument(
        "--dry-run", action="store_true", help="list selected URLs without requests"
    )
    args = parser.parse_args(argv)
    if args.from_month > args.to_month:
        parser.error("--from-month must not follow --to-month")
    with args.manifest.open(newline="", encoding="utf-8-sig") as stream:
        rows = [
            row
            for row in csv.DictReader(stream)
            if args.from_month <= row["report_date"][:7] <= args.to_month
        ]
    for row in rows:
        check_url(row["source_url"])
        if row["expected_format"].lower() not in {"zip", "xls"}:
            raise ValueError(f"Unexpected format for {row['report_date']}.")
    if args.dry_run:
        for row in rows:
            print(row["report_date"], row["source_url"])
        return []

    output = args.out.resolve()
    output.mkdir(parents=True, exist_ok=True)
    log: list[dict] = []
    with requests.Session() as session:
        session.headers.update(HEADERS)
        for row in rows:
            report_date = row["report_date"]
            suffix = row["expected_format"].lower()
            target = output / report_date[:7] / f"ABSLMF_portfolio_{report_date}.{suffix}"
            result = {
                **row,
                "local_file": str(target),
                "status": "",
                "bytes": 0,
                "sha256": "",
                "final_url": "",
                "detail": "",
            }
            try:
                if target.exists():
                    data = target.read_bytes()
                    if not valid_archive(data, suffix):
                        raise ValueError("Cached file is not a valid archive; review it manually.")
                    result["status"] = "already_present"
                    result["final_url"] = row["source_url"]
                else:
                    time.sleep(max(0.0, args.sleep))
                    with session.get(row["source_url"], timeout=(15, 90), stream=True) as response:
                        check_url(response.url)
                        result["final_url"] = response.url
                        if response.status_code in {403, 429}:
                            result["status"] = f"http_{response.status_code}"
                            result["detail"] = "Source restriction; stop and use the official page."
                            log.append(result)
                            print(report_date, result["status"])
                            break
                        if response.status_code == 404:
                            result["status"] = "not_found"
                            result["detail"] = (
                                "Candidate URL returned 404; find a replacement on the AMC page."
                            )
                            log.append(result)
                            print(report_date, result["status"])
                            continue
                        response.raise_for_status()
                        data = read_limited(response)
                    if not valid_archive(data, suffix):
                        raise ValueError("Response does not match the expected archive format.")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
                    result["status"] = "downloaded"
                result["bytes"] = len(data)
                result["sha256"] = hashlib.sha256(data).hexdigest()
                if suffix == "zip" and not args.no_extract:
                    extract_to = target.parent / f"{target.stem}_extracted"
                    if not extract_to.exists():
                        safe_extract_zip(data, extract_to)
            except (requests.RequestException, OSError, ValueError, zipfile.BadZipFile) as exc:
                result["status"] = "error"
                result["detail"] = f"{type(exc).__name__}: {exc}"
            log.append(result)
            print(report_date, result["status"], result["detail"])

    log_file = output / "download_log.csv"
    fields = [
        "report_date",
        "source_url",
        "expected_format",
        "publication_date_verified",
        "notes",
        "local_file",
        "status",
        "bytes",
        "sha256",
        "final_url",
        "detail",
    ]
    with log_file.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(log)
    print("Download log:", log_file)
    return log


if __name__ == "__main__":
    download()
