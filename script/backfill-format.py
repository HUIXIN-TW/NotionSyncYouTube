"""One-time Notion Category -> Format migration; defaults to dry-run."""

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from notionsyncyoutube.backfill import backfill
from notionsyncyoutube.dotenv import load_dotenv_if_present
from notionsyncyoutube.http import HttpClient


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes to Notion (default is dry-run)",
    )
    args = parser.parse_args()
    load_dotenv_if_present()
    token = os.getenv("NOTION_TOKEN")
    data_source_id = os.getenv("NOTION_DATA_SOURCE_ID")
    if not token or not data_source_id:
        parser.error("NOTION_TOKEN and NOTION_DATA_SOURCE_ID are required")

    result = backfill(
        HttpClient(), token=token, data_source_id=data_source_id, apply=args.apply
    )
    print(result)
    if result["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
