# YouTube Inbox to Notion

Sync videos from a YouTube playlist into a Notion backlog database.

The formal workflow uses `main.py` with the official YouTube Data API. For
quick MVP/local runs, `script/fetch-to-notion.py` uses `yt-dlp`, so it only
needs a YouTube playlist ID and does not need a YouTube API key.

```txt
Formal:   YouTube Data API -> Notion database
Quick MVP: YouTube playlist ID -> local JSON cache -> Notion database
```

## Requirements

- Python 3.10 or newer
- `uv`
- A public or unlisted YouTube playlist ID
- A Notion internal integration token
- A Notion database shared with that integration

The formal `main.py` workflow also requires a YouTube Data API key.

Node.js is recommended for `yt-dlp` YouTube extraction. The script still runs
without Node, but `yt-dlp` may emit JavaScript runtime warnings.

## Install

```bash
uv sync
```

## Configuration

For local runs, both entry points load `.env` from the current directory when it
exists. Shell environment values take priority.

```bash
YOUTUBE_PLAYLIST_ID="your_youtube_playlist_id"

NOTION_TOKEN="secret_xxx"
NOTION_DATABASE_ID="your_notion_database_id"
```

For the formal `main.py` workflow, also set:

```bash
YOUTUBE_API_KEY="your_youtube_api_key"
```

For the quick MVP `yt-dlp` script, only set the playlist ID. The script derives
the playlist URL internally.

Optional:

```bash
NOTION_DATA_SOURCE_ID="your_notion_data_source_id"
NOTION_USE_DEFAULT_TEMPLATE=false
YOUTUBE_ENRICH_LENGTHS=true
YOUTUBE_PLAYLIST_CACHE_FILE="/tmp/youtube-playlist.json"
YTDLP_ENABLE_REMOTE_COMPONENTS=false
```

Set `NOTION_DATA_SOURCE_ID` and `NOTION_USE_DEFAULT_TEMPLATE=true` to apply the
Notion data source's default template when creating new pages. Existing pages
are never templated again; they only receive metadata updates. Template support
uses Notion's data source API, so the sync automatically uses Notion API version
`2025-09-03` when `NOTION_DATA_SOURCE_ID` is present.

`YTDLP_ENABLE_REMOTE_COMPONENTS=true` lets `yt-dlp` fetch remote extractor
components at runtime. Keep it disabled unless you explicitly need it.

## Run Formal Workflow

```bash
uv run python main.py
```

## Run Quick MVP Workflow

Fetch the playlist into a cache file:

```bash
uv run python script/fetch-to-notion.py fetch
```

Update Notion from the cache:

```bash
uv run python script/fetch-to-notion.py update
```

Run both steps:

```bash
uv run python script/fetch-to-notion.py sync
```

The default cache file is `/tmp/youtube-playlist.json` on macOS/Linux. Override
it with `YOUTUBE_PLAYLIST_CACHE_FILE` or `--cache-file`.

If any Notion item fails to update, `update` and `sync` exit non-zero after
printing the summary.

## Notion Schema

The Notion database must contain these properties:

| Property   | Type      | Description                                     |
| ---------- | --------- | ----------------------------------------------- |
| `Title`    | Title     | Video title from YouTube.                       |
| `Category` | Select    | Static value set to `Youtube`.                  |
| `Status`   | Status    | Set to `Backlog` only when creating new pages.  |
| `URL`      | URL       | Canonical YouTube watch URL.                    |
| `Video ID` | Rich text | Stable YouTube video ID used for deduplication. |

Optional property:

| Property | Type   | Description                                          |
| -------- | ------ | ---------------------------------------------------- |
| `Length` | Select | Duration bucket derived from YouTube video duration. |

The `Length` select options must match exactly:

```txt
<= 15m
16-30m
31-60m
60m+
```

## Sync Behavior

- New videos create new Notion pages.
- New pages apply the Notion default template when `NOTION_USE_DEFAULT_TEMPLATE=true`.
- Existing pages are found by `Video ID`.
- Existing pages are updated for metadata such as title, URL, category, and length.
- Existing page `Status` is preserved, so `Active` or `Done` is not reset to `Backlog`.
- Deleted/private YouTube placeholders are skipped.
- The script does not delete Notion pages or remove videos from YouTube.

## Project Structure

```txt
main.py                          Formal YouTube Data API entrypoint
script/fetch-to-notion.py        Quick MVP two-step yt-dlp workflow
notionsyncyoutube/config.py      Environment and .env configuration
notionsyncyoutube/dotenv.py      Minimal .env parser
notionsyncyoutube/http.py        JSON HTTP client
notionsyncyoutube/youtube.py     YouTube Data API client
notionsyncyoutube/notion.py      Notion API client
notionsyncyoutube/duration.py    Shared duration parsing and Length mapping
notionsyncyoutube/sync.py        Formal API sync orchestration
notionsyncyoutube/models.py      Shared data models
notionsyncyoutube/errors.py      Shared exception types
```

## Formal API Workflow

`main.py` uses the official YouTube Data API:

```bash
YOUTUBE_API_KEY="your_youtube_api_key"
YOUTUBE_PLAYLIST_ID="your_youtube_playlist_id"
NOTION_TOKEN="secret_xxx"
NOTION_DATABASE_ID="your_notion_database_id"

uv run python main.py
```
