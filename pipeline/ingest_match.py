"""Save one match's raw shot data to data/raw/<source>/<season>/<match_id>.json.

Raw files are written once and never edited: they're our record of what the
source said. Every later step (cleaning, models, charts) rebuilds from them.

Usage:
    python -m pipeline.ingest_match              # latest finished match
    python -m pipeline.ingest_match --match-id 31248
"""
import argparse
import json
from datetime import datetime, timezone

from pipeline.config import CURRENT_SEASON, RAW_DIR
from pipeline.sources.understat import UnderstatSource


def ingest(source, season: str, match_id: int) -> None:
    out = RAW_DIR / source.name / season / f"{match_id}.json"
    if out.exists():
        print(f"Already have {out.relative_to(RAW_DIR)}, skipping")
        return

    shots = source.get_match_shots(season, match_id)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": source.name,
        "season": season,
        "match_id": match_id,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "shots": shots,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Saved {len(shots)} shots to {out.relative_to(RAW_DIR)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", default=CURRENT_SEASON)
    parser.add_argument("--match-id", type=int)
    args = parser.parse_args()

    source = UnderstatSource()
    match_id = args.match_id
    if match_id is None:
        played = source.list_matches(args.season).query("is_result")
        match_id = int(played.sort_values("date").iloc[-1].match_id)
    ingest(source, args.season, match_id)


if __name__ == "__main__":
    main()
