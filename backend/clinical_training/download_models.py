"""Download only registry models whose license status is explicitly approved.

Run this on the inference/training host, not in the web API or GitHub Actions.
Weights are stored outside the repository by default.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from huggingface_hub import HfApi, snapshot_download

REGISTRY = Path(__file__).parents[1] / "model_registry.json"
APPROVED = {"verified_open_license", "terms_reviewed_and_accepted"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-ids", required=True, help="Comma-separated registry IDs")
    parser.add_argument("--cache-dir", default=str(Path.home() / ".cache" / "ytemo-models"))
    parser.add_argument("--confirm-license-review", action="store_true")
    args = parser.parse_args()
    if not args.confirm_license_review:
        raise SystemExit("Phải xác nhận đã đọc model card và license bằng --confirm-license-review.")

    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    entries = {item["id"]: item for item in registry["models"]}
    cache = Path(args.cache_dir).expanduser()
    cache.mkdir(parents=True, exist_ok=True)
    for model_id in [item.strip() for item in args.model_ids.split(",") if item.strip()]:
        if model_id not in entries:
            raise SystemExit(f"Model không có trong registry: {model_id}")
        entry = entries[model_id]
        if entry.get("license_status") not in APPROVED:
            raise SystemExit(
                f"{model_id} chưa được duyệt license: {entry.get('license_status')}. "
                "Không tự động tải model có điều khoản chưa được xem xét."
            )
        target = cache / model_id
        info = HfApi().model_info(entry["model_id"])
        resolved_revision = info.sha
        snapshot_download(
            repo_id=entry["model_id"],
            revision=resolved_revision,
            local_dir=str(target),
        )
        manifest = {
            "registry_id": model_id,
            "model_id": entry["model_id"],
            "resolved_revision": resolved_revision,
            "license": entry["license"],
            "license_url": entry.get("license_url"),
            "downloaded_path": str(target),
        }
        (target / "ytemo_model_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Downloaded {model_id}@{resolved_revision} -> {target}")


if __name__ == "__main__":
    main()
