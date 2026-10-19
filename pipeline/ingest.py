"""Fetch every finished match we don't have yet into the raw layer.

Safe to re-run at any time: matches already saved are skipped, and one failing
match doesn't stop the rest.

Usage:
    python -m pipeline.ingest                        # all sources, all new matches
    python -m pipeline.ingest --source whoscored     # one source
    python -m pipeline.ingest --match-id 1983614 --source whoscored
    python -m pipeline.ingest --limit 5              # at most 5 new matches per source
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.config import CURRENT_SEASON
from pipeline.raw import raw_path, write_raw
from pipeline.sources.understat import UnderstatSource
from pipeline.sources.whoscored import WhoScoredSource

SOURCES = {"understat": UnderstatSource, "whoscored": WhoScoredSource}


def ingest_source(source, season: str, match_ids: list[int] | None, limit: int | None) -> list[int]:
    if match_ids is None:
        played = source.list_matches(season).query("is_result").sort_values("date")
        match_ids = [int(m) for m in played["match_id"]]

    todo = [m for m in match_ids if not raw_path(source.name, season, m).exists()]
    print(f"[{source.name}] {len(match_ids) - len(todo)} already saved, {len(todo)} missing")
    if limit is not None and len(todo) > limit:
        todo = todo[:limit]
        print(f"[{source.name}] fetching the first {limit} (--limit)")

    failed = []
    for i, match_id in enumerate(todo, 1):
        start = time.monotonic()
        try:
            write_raw(source.name, season, match_id, source.get_match(season, match_id))
            print(f"[{source.name}] {i}/{len(todo)} saved {match_id} ({time.monotonic() - start:.0f}s)")
        except Exception as e:  # keep going; report at the end
            failed.append(match_id)
            print(f"[{source.name}] {i}/{len(todo)} FAILED {match_id}: {e}")
    return failed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", default=CURRENT_SEASON)
    parser.add_argument("--source", choices=SOURCES, action="append", help="default: all sources")
    parser.add_argument("--match-id", type=int, action="append")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    failures = {}
    for name in args.source or SOURCES:
        failed = ingest_source(SOURCES[name](), args.season, args.match_id, args.limit)
        if failed:
            failures[name] = failed

    if failures:
        print(f"Finished with failures: {failures}")
        sys.exit(1)
    print("Finished: everything up to date")


if __name__ == "__main__":
    main()
