"""Download and verify the fixed public HEMOBP Version 3 source files."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import urllib.request
from pathlib import Path


ARTICLE_ID = 6260654
VERSION = 3
METADATA_URL = f"https://api.figshare.com/v2/articles/{ARTICLE_ID}/versions/{VERSION}"
EXPECTED = {
    "d1.csv": {"size": 11130894, "md5": "7db3b48bae2c73e3ecd731dbcd452233"},
    "idp.csv": {"size": 35151, "md5": "31d269f59bf4acc719f392ad9164d08a"},
    "vip.csv": {"size": 262851369, "md5": "ff1589610cf7aa3b3e01ba979b6bdc44"},
}


def md5sum(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_metadata() -> dict:
    request = urllib.request.Request(
        METADATA_URL,
        headers={"User-Agent": "DIAL-ALERT/1.0 academic reproducibility client"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def download_file(url: str, destination: Path) -> None:
    temporary = destination.with_suffix(destination.suffix + ".part")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "DIAL-ALERT/1.0 academic reproducibility client"},
    )
    with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as output:
        shutil.copyfileobj(response, output, length=1024 * 1024)
    temporary.replace(destination)


def acquire(output_dir: Path, requested: set[str], force: bool) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata = load_metadata()
    if int(metadata.get("version", -1)) != VERSION:
        raise RuntimeError(f"Expected Figshare version {VERSION}, received {metadata.get('version')}")

    published = {entry["name"]: entry for entry in metadata.get("files", [])}
    missing_metadata = sorted(set(EXPECTED) - set(published))
    if missing_metadata:
        raise RuntimeError(f"Figshare metadata is missing expected files: {missing_metadata}")

    for name in sorted(requested):
        if name not in EXPECTED:
            raise ValueError(f"Unknown file {name!r}; choose from {sorted(EXPECTED)}")
        destination = output_dir / name
        expected = EXPECTED[name]

        if destination.exists() and not force:
            if destination.stat().st_size == expected["size"] and md5sum(destination) == expected["md5"]:
                print(f"Verified existing {name}")
                continue
            raise RuntimeError(f"Existing {destination} failed verification; rerun with --force")

        print(f"Downloading {name} ({expected['size'] / 1024 / 1024:.1f} MiB)")
        download_file(published[name]["download_url"], destination)
        actual_md5 = md5sum(destination)
        if destination.stat().st_size != expected["size"] or actual_md5 != expected["md5"]:
            destination.unlink(missing_ok=True)
            raise RuntimeError(f"Downloaded {name} failed size or MD5 verification")
        print(f"Verified {name}: {actual_md5}")

    provenance = {
        "article_id": ARTICLE_ID,
        "version": VERSION,
        "doi": metadata.get("doi"),
        "license": metadata.get("license"),
        "files": {name: EXPECTED[name] for name in sorted(requested)},
    }
    (output_dir / "figshare_metadata.json").write_text(
        json.dumps(provenance, indent=2), encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw"))
    parser.add_argument(
        "--files",
        nargs="+",
        default=sorted(EXPECTED),
        help="Subset to download: d1.csv idp.csv vip.csv",
    )
    parser.add_argument("--force", action="store_true", help="Replace existing files")
    args = parser.parse_args()
    try:
        acquire(args.output_dir, set(args.files), args.force)
    except Exception as exc:
        print(f"Data acquisition failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()

