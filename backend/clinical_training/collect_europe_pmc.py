"""Collect Europe PMC Open Access full-text articles with item-level license checks.

This is a source acquisition step only. It does not generate training examples,
approve medical claims, or imply that every open-access license permits every
downstream use. Original XML, SHA-256 and metadata are retained.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote

import requests

API = "https://www.ebi.ac.uk/europepmc/webservices/rest"
ALLOWED = {
    "cc by 4.0": "CC-BY-4.0",
    "cc by 3.0": "CC-BY-3.0",
    "cc0 1.0": "CC0-1.0",
    "cc0": "CC0-1.0",
    "public domain": "US-GOV-PD",
}
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "YTeMo-OpenClinicalDataCollector/0.1 (research provenance client)"})


def normalize_license(value: str) -> str | None:
    normalized = re.sub(r"\s+", " ", (value or "").strip().lower())
    for fragment, canonical in ALLOWED.items():
        if fragment == normalized or normalized.endswith("/" + fragment.replace(" ", "-")):
            return canonical
    if "creativecommons.org/licenses/by/4.0" in normalized:
        return "CC-BY-4.0"
    if "creativecommons.org/licenses/by/3.0" in normalized:
        return "CC-BY-3.0"
    if "creativecommons.org/publicdomain/zero/1.0" in normalized:
        return "CC0-1.0"
    return None


def article_text(xml_bytes: bytes) -> str:
    root = ET.fromstring(xml_bytes)
    return " ".join(part.strip() for part in root.itertext() if part and part.strip())


def collect(query: str, output_dir: Path, page_size: int = 25, max_records: int = 100) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    originals = output_dir / "originals"
    originals.mkdir(exist_ok=True)
    manifest_path = output_dir / "source_manifest.jsonl"
    seen = set()
    if manifest_path.exists():
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            try:
                seen.add(json.loads(line).get("sha256"))
            except json.JSONDecodeError:
                continue

    start = 0
    collected = skipped_license = skipped_missing_id = duplicates = 0
    with manifest_path.open("a", encoding="utf-8") as manifest:
        while collected + skipped_license + skipped_missing_id + duplicates < max_records:
            params = {
                "query": f"({query}) AND OPEN_ACCESS:Y",
                "format": "json",
                "pageSize": min(max(page_size, 1), 100),
                "resultType": "core",
                "cursorMark": "*" if start == 0 else cursor,
            }
            response = SESSION.get(f"{API}/search", params=params, timeout=(5, 30))
            response.raise_for_status()
            payload = response.json()
            results = payload.get("resultList", {}).get("result", [])
            if not results:
                break
            cursor = payload.get("nextCursorMark")
            for item in results:
                pmcid = item.get("pmcid")
                if not pmcid:
                    skipped_missing_id += 1
                    continue
                license_value = item.get("license") or item.get("licenseStatement") or ""
                canonical_license = normalize_license(license_value)
                if canonical_license not in {"CC-BY-4.0", "CC-BY-3.0", "CC0-1.0"}:
                    skipped_license += 1
                    continue
                xml_response = SESSION.get(f"{API}/{quote(pmcid)}/fullTextXML", timeout=(5, 45))
                if xml_response.status_code != 200:
                    continue
                raw = xml_response.content
                digest = hashlib.sha256(raw).hexdigest()
                if digest in seen:
                    duplicates += 1
                    continue
                text_content = article_text(raw)
                if len(text_content) < 500:
                    continue
                original_path = originals / f"{pmcid}_{digest[:12]}.xml"
                original_path.write_bytes(raw)
                record = {
                    "source_id": pmcid,
                    "source_url": f"https://europepmc.org/articles/{pmcid}",
                    "publisher": item.get("journalTitle"),
                    "title": item.get("title"),
                    "authors": item.get("authorString"),
                    "published_at": item.get("firstPublicationDate"),
                    "license": canonical_license,
                    "license_raw": license_value,
                    "license_url": item.get("license"),
                    "source_version": item.get("firstPublicationDate"),
                    "sha256": digest,
                    "original_path": str(original_path),
                    "text_characters": len(text_content),
                    "collection_method": "Europe PMC OA fullTextXML",
                    "training_status": "SOURCE_ONLY_REQUIRES_CLAIM_AND_CLINICAL_REVIEW",
                }
                manifest.write(json.dumps(record, ensure_ascii=False) + "\n")
                manifest.flush()
                seen.add(digest)
                collected += 1
                if collected >= max_records:
                    break
                time.sleep(0.15)
            if not cursor or cursor == params["cursorMark"]:
                break
            start += len(results)

    return {
        "collected": collected,
        "skipped_license": skipped_license,
        "skipped_missing_pmcid": skipped_missing_id,
        "duplicates": duplicates,
        "manifest": str(manifest_path),
        "note": "Collected source originals only; not yet approved for SFT or patient-facing use.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True, help="Europe PMC query expression")
    parser.add_argument("--output-dir", default="artifacts/europe_pmc")
    parser.add_argument("--page-size", type=int, default=25)
    parser.add_argument("--max-records", type=int, default=100)
    args = parser.parse_args()
    print(json.dumps(collect(args.query, Path(args.output_dir), args.page_size, args.max_records), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
