"""Read and write the immutable raw layer: data/raw/<source>/<season>/<match_id>.json.gz

Each file wraps what the source returned in a small envelope recording where and
when it came from. Files are gzip-compressed (WhoScored match files are ~1 MB of JSON).
"""
import gzip
import json
from datetime import datetime, timezone
from pathlib import Path

from pipeline.config import RAW_DIR


def raw_path(source: str, season: str, match_id: int) -> Path:
    return RAW_DIR / source / season / f"{match_id}.json.gz"


def write_raw(source: str, season: str, match_id: int, data: dict) -> Path:
    path = raw_path(source, season, match_id)
    if path.exists():
        raise FileExistsError(f"{path} already exists; raw files are never overwritten")
    envelope = {
        "source": source,
        "season": season,
        "match_id": match_id,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write to a temp file first so a crash mid-write never leaves a half-file behind.
    tmp = path.with_suffix(".tmp")
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        json.dump(envelope, f, ensure_ascii=False)
    tmp.replace(path)
    return path


def read_raw(path: Path) -> dict:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)
