import argparse
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from yt_dlp import YoutubeDL

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from notionsyncyoutube.dotenv import load_dotenv_if_present
from notionsyncyoutube.duration import DurationMapper
from notionsyncyoutube.errors import ApiError
from notionsyncyoutube.config import (
    ConfigError,
    NOTION_DATA_SOURCE_VERSION,
    NOTION_VERSION,
    validate_optional_value,
    validate_required_value,
)
from notionsyncyoutube.http import HttpClient
from notionsyncyoutube.models import Video
from notionsyncyoutube.notion import NotionClient


DEFAULT_STATUS = "Backlog"
DEFAULT_CACHE_FILE = str(Path(tempfile.gettempdir()) / "youtube-playlist.json")
PLAYLIST_URL_TEMPLATE = "https://www.youtube.com/playlist?list={playlist_id}"


# -------------------------
# Env helpers
# -------------------------


def require_env(name: str) -> str:
    value = os.environ.get(name)

    try:
        return validate_required_value(name, value)
    except ConfigError as exc:
        raise RuntimeError(str(exc)) from exc


def optional_env(name: str) -> str | None:
    value = os.environ.get(name)

    try:
        return validate_optional_value(name, value)
    except ConfigError as exc:
        raise RuntimeError(str(exc)) from exc


def env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)

    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


# -------------------------
# YouTube via yt-dlp
# -------------------------


def build_ytdlp_opts(*, extract_flat: bool = False) -> dict:
    """
    Build yt-dlp options.

    YouTube extraction requires a JavaScript runtime.
    The Lambda bundle includes Deno, while local runs may use Deno or Node.js.

    remote_components enables yt-dlp to fetch the EJS challenge solver when needed.
    This reduces YouTube n-challenge warnings.
    """
    opts = {
        "quiet": True,
        "skip_download": True,
        "ignoreerrors": False,
    }

    if env_bool("YTDLP_ENABLE_REMOTE_COMPONENTS", False):
        opts["remote_components"] = ["ejs:github"]

    if extract_flat:
        opts["extract_flat"] = True

    bundled_deno_path = Path(__file__).resolve().parent.parent / "bin" / "deno"
    deno_path = shutil.which("deno")
    if bundled_deno_path.is_file():
        deno_path = str(bundled_deno_path)

    if deno_path:
        opts["js_runtimes"] = {
            "deno": {
                "path": deno_path,
            },
        }
    else:
        node_path = shutil.which("node")
        if node_path:
            opts["js_runtimes"] = {
                "node": {
                    "path": node_path,
                },
            }
        else:
            print(
                "WARN   no supported JavaScript runtime found; "
                "yt-dlp may emit JavaScript runtime warnings."
            )

    return opts


def fetch_playlist_items_with_ytdlp(playlist_url: str) -> list[dict]:
    """
    Fetch playlist items using yt-dlp.

    This does not need a YouTube Data API key.
    It does not download videos.
    It only extracts playlist metadata.
    """
    ydl_opts = build_ytdlp_opts(extract_flat=True)

    videos: list[dict] = []

    with YoutubeDL(ydl_opts) as ydl:
        playlist_info = ydl.extract_info(playlist_url, download=False)

    entries = playlist_info.get("entries", []) if playlist_info else []

    for entry in entries:
        if not entry:
            continue

        video_id = entry.get("id")
        title = entry.get("title")

        if not video_id or not title:
            continue

        if title in {"Deleted video", "Private video"}:
            continue

        duration = entry.get("duration")
        if isinstance(duration, (int, float)):
            duration = int(duration)
        else:
            duration = None

        videos.append(
            {
                "video_id": video_id,
                "title": title,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "duration_seconds": duration,
            }
        )

    return videos


def build_playlist_url(playlist_id: str) -> str:
    return PLAYLIST_URL_TEMPLATE.format(playlist_id=playlist_id)


def fetch_video_detail_with_ytdlp(video_url: str) -> dict | None:
    """
    Optional: fetch per-video detail.

    Used for duration because flat playlist extraction may not always include full metadata.
    This is slower than flat playlist extraction.
    """
    ydl_opts = build_ytdlp_opts(extract_flat=False)

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)

    return info


def map_duration_seconds_to_length(duration_seconds: int | None) -> str | None:
    """
    Match the current Notion Length options:
      <= 15m
      16-30m
      31-60m
      60m+
    """
    return DurationMapper().map_seconds_to_length(duration_seconds)


def enrich_video_lengths(videos: list[dict]) -> list[dict]:
    """
    Fetch duration for each video using yt-dlp.

    This is optional but useful because the Notion DB has Length.
    If sync becomes too slow, set:

      export YOUTUBE_ENRICH_LENGTHS=false
    """
    enriched = []

    for index, video in enumerate(videos, start=1):
        try:
            duration = video.get("duration_seconds")
            duration_source = "playlist"

            if duration is None:
                detail = fetch_video_detail_with_ytdlp(video["url"])
                duration = detail.get("duration") if detail else None
                duration_source = "video"

            video["duration_seconds"] = duration
            video["length"] = map_duration_seconds_to_length(duration)

            duration_label = f"{duration}s" if duration is not None else "unknown duration"
            length_label = video["length"] or "unknown length"
            print(
                f"DETAIL {index}/{len(videos)} "
                f"{video['title']} [{video['video_id']}] "
                f"{duration_label} "
                f"{length_label} "
                f"source={duration_source}"
            )

        except Exception as exc:
            print(f"WARN   failed to fetch duration for {video['video_id']}: {exc}")
            video["length"] = None

        enriched.append(video)

    return enriched


# -------------------------
# Notion
# -------------------------


def build_notion_client() -> NotionClient:
    data_source_id = optional_env("NOTION_DATA_SOURCE_ID")

    return NotionClient(
        token=require_env("NOTION_TOKEN"),
        database_id=require_env("NOTION_DATABASE_ID"),
        data_source_id=data_source_id,
        notion_version=os.getenv("NOTION_VERSION")
        or (NOTION_DATA_SOURCE_VERSION if data_source_id else NOTION_VERSION),
        http_client=HttpClient(),
    )


def video_from_cache_record(record: dict) -> Video:
    video_id = record.get("video_id")
    title = record.get("title")
    url = record.get("url")
    length = record.get("length")

    if not isinstance(video_id, str) or not video_id:
        raise RuntimeError("Cache record is missing video_id")

    if not isinstance(title, str) or not title:
        raise RuntimeError(f"Cache record {video_id} is missing title")

    if not isinstance(url, str) or not url:
        raise RuntimeError(f"Cache record {video_id} is missing url")

    if length is not None and not isinstance(length, str):
        raise RuntimeError(f"Cache record {video_id} has invalid length")

    return Video(
        video_id=video_id,
        title=title,
        url=url,
        length=length,
    )


def format_video_label(video: dict) -> str:
    title = video.get("title", "<unknown title>")
    video_id = video.get("video_id", "<unknown id>")

    return f"{title} [{video_id}]"


# -------------------------
# Cache helpers
# -------------------------


def write_videos(path: Path, videos: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(videos, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def read_videos(path: Path) -> list[dict]:
    if not path.exists():
        raise RuntimeError(f"Cache file does not exist: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(data, list):
        raise RuntimeError(f"Expected a list of videos in {path}")

    return data


# -------------------------
# Step 1: fetch YouTube playlist
# -------------------------


def fetch_all_from_youtube_playlist(output_path: Path) -> list[dict]:
    playlist_id = require_env("YOUTUBE_PLAYLIST_ID")
    playlist_url = build_playlist_url(playlist_id)

    print("Step 1/2: fetching YouTube playlist items with yt-dlp...")
    videos = fetch_playlist_items_with_ytdlp(playlist_url)

    print(f"Fetched {len(videos)} YouTube videos.")

    if env_bool("YOUTUBE_ENRICH_LENGTHS", True):
        print("Enriching video lengths with yt-dlp...")
        videos = enrich_video_lengths(videos)
    else:
        print("Skipping duration enrichment.")

    write_videos(output_path, videos)
    print(f"Wrote playlist cache to {output_path}")

    return videos


# -------------------------
# Step 2: update Notion
# -------------------------


def update_notion_from_videos(videos: list[dict]) -> dict:
    notion_client = build_notion_client()
    use_default_template = env_bool("NOTION_USE_DEFAULT_TEMPLATE", False)
    notion_client.verify_database_access()
    notion_client.verify_create_target(use_default_template)

    created = 0
    updated = 0
    errors = 0

    print("Step 2/2: updating Notion database...")

    for video in videos:
        try:
            video_model = video_from_cache_record(video)
            existing = notion_client.find_page_by_video_id(video_model.video_id)

            if existing:
                page_id = existing.get("id")

                if not isinstance(page_id, str):
                    raise RuntimeError("Existing Notion page has no string id")

                notion_client.update_video_page(
                    page_id,
                    video_model,
                )
                updated += 1
                print(f"UPDATE {video_model.title} [{video_model.video_id}]")
                continue

            notion_client.create_video_page(
                video_model,
                status=DEFAULT_STATUS,
                use_default_template=use_default_template,
            )
            created += 1
            print(f"CREATE {video_model.title} [{video_model.video_id}]")

        except Exception as exc:
            errors += 1
            print(f"ERROR  {format_video_label(video)}: {exc}")

    return {
        "source": "yt-dlp",
        "fetched": len(videos),
        "created": created,
        "updated_existing": updated,
        "errors": errors,
        "synced_at": datetime.now(timezone.utc).isoformat(),
    }


def update_notion_from_cache(input_path: Path) -> dict:
    videos = read_videos(input_path)
    print(f"Loaded {len(videos)} videos from {input_path}")
    return update_notion_from_videos(videos)


def sync(cache_path: Path) -> dict:
    videos = fetch_all_from_youtube_playlist(cache_path)
    return update_notion_from_videos(videos)


# -------------------------
# CLI
# -------------------------


def print_summary(summary: dict) -> None:
    print("\nSync summary:")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch a YouTube playlist, then update a Notion database.",
    )

    parser.add_argument(
        "step",
        nargs="?",
        default="sync",
        choices=("fetch", "update", "sync"),
        help=("fetch: only fetch playlist to JSON; " "update: update Notion from JSON; " "sync: run fetch then update"),
    )

    parser.add_argument(
        "--cache-file",
        default=os.environ.get("YOUTUBE_PLAYLIST_CACHE_FILE", DEFAULT_CACHE_FILE),
        help="JSON file used between the fetch and update steps.",
    )

    return parser.parse_args()


def main() -> None:
    load_dotenv_if_present()
    args = parse_args()
    cache_file = Path(args.cache_file)

    try:
        if args.step == "fetch":
            fetched_videos = fetch_all_from_youtube_playlist(cache_file)
            print_summary(
                {
                    "source": "yt-dlp",
                    "fetched": len(fetched_videos),
                    "cache_file": str(cache_file),
                    "synced_at": None,
                }
            )
            return

        if args.step == "update":
            summary = update_notion_from_cache(cache_file)
            print_summary(summary)
            if summary["errors"] > 0:
                raise SystemExit(1)
            return

        summary = sync(cache_file)
        print_summary(summary)
        if summary["errors"] > 0:
            raise SystemExit(1)
    except (ApiError, RuntimeError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
