"""The whole refresh in one command: ingest new matches -> bronze -> dbt build.

Run this after each matchweek:
    python -m pipeline.run                 # everything
    python -m pipeline.run --skip-ingest   # rebuild tables from data already saved
"""
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.config import DATA_DIR, ROOT

DBT_DIR = ROOT / "dbt"


def step(name: str, cmd: list[str], **kwargs) -> None:
    print(f"\n=== {name} ===", flush=True)
    start = time.monotonic()
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        sys.exit(f"{name} failed (exit code {result.returncode})")
    print(f"=== {name} done in {time.monotonic() - start:.0f}s ===", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-ingest", action="store_true")
    args = parser.parse_args()

    python = sys.executable
    if not args.skip_ingest:
        step("ingest", [python, "-m", "pipeline.ingest"], cwd=ROOT)
    step("bronze", [python, "-m", "pipeline.bronze"], cwd=ROOT)

    dbt_env = {
        **os.environ,
        "DBT_PROFILES_DIR": str(DBT_DIR),
        "DBT_TARGET_PATH": str(DATA_DIR / "dbt" / "target"),
        "DBT_LOG_PATH": str(DATA_DIR / "dbt" / "logs"),
        "DBT_DUCKDB_PATH": str(DATA_DIR / "warehouse.duckdb"),
        "PREMISTATS_ROOT": str(ROOT),  # lets the xG Python model find the trained model
    }
    dbt = Path(python).with_name("dbt.exe" if os.name == "nt" else "dbt")
    step("dbt build", [str(dbt), "build"], cwd=DBT_DIR, env=dbt_env)


if __name__ == "__main__":
    main()
