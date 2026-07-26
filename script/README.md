# Quick MVP YouTube to Notion Sync

`fetch-to-notion.py` is the quick MVP/local workflow. It uses `yt-dlp` to fetch
a playlist, writes a JSON cache, then updates Notion from that cache.

The formal workflow is `main.py`, which uses the official YouTube Data API.

## Requirements

- Python 3.10 or newer
- `uv`
- `YOUTUBE_PLAYLIST_ID`
- `NOTION_TOKEN`
- `NOTION_DATABASE_ID`

The script loads `.env` from the current working directory when present.

## Commands

Fetch only:

```bash
uv run python script/fetch-to-notion.py fetch
```

Update Notion from the existing cache:

```bash
uv run python script/fetch-to-notion.py update
```

Fetch and update:

```bash
uv run python script/fetch-to-notion.py sync
```

Use a custom cache file:

```bash
uv run python script/fetch-to-notion.py fetch --cache-file data/youtube-playlist.json
uv run python script/fetch-to-notion.py update --cache-file data/youtube-playlist.json
```

## Environment

Required for fetch:

```bash
YOUTUBE_PLAYLIST_ID="your_youtube_playlist_id"
```

Use only the playlist ID. The script derives:

```txt
https://www.youtube.com/playlist?list=<YOUTUBE_PLAYLIST_ID>
```

Required for update:

```bash
NOTION_TOKEN="secret_xxx"
NOTION_DATABASE_ID="your_notion_database_id"
```

Optional:

```bash
NOTION_DATA_SOURCE_ID="your_notion_data_source_id"
NOTION_USE_DEFAULT_TEMPLATE=true
YOUTUBE_PLAYLIST_CACHE_FILE="/tmp/youtube-playlist.json"
YOUTUBE_ENRICH_LENGTHS=true
YTDLP_ENABLE_REMOTE_COMPONENTS=false
```

Set `NOTION_DATA_SOURCE_ID` and `NOTION_USE_DEFAULT_TEMPLATE=true` to apply the
Notion data source's default template when creating new pages. Existing pages
are not templated again; they only receive metadata updates.

`YOUTUBE_ENRICH_LENGTHS=false` skips per-video duration fetching when a faster
metadata-only sync is preferred.

`YTDLP_ENABLE_REMOTE_COMPONENTS=true` lets `yt-dlp` fetch remote extractor
components at runtime. Keep it disabled unless a local run needs it.

The Lambda build bundles a pinned Linux x86_64 Deno runtime and matching
`yt-dlp-ejs` package. Local runs use Deno when available, then fall back to
Node.js. Duration enrichment uses playlist metadata first and only makes a
per-video request when the playlist entry has no duration.

## Notion Schema

Required properties:

| Property   | Type      | Notes                                      |
| ---------- | --------- | ------------------------------------------ |
| `Title`    | Title     | Video title                                |
| `Category` | Select    | Set to `Youtube`                           |
| `Status`   | Status    | Set to `Backlog` only for newly created pages |
| `URL`      | URL       | YouTube watch URL                          |
| `Video ID` | Rich text | Deduplication key                          |

Optional:

| Property | Type   | Notes           |
| -------- | ------ | --------------- |
| `Length` | Select | Duration bucket |

Length options must match exactly:

```txt
<= 15m
16-30m
31-60m
60m+
```

## Behavior

- `fetch` fails if `yt-dlp` cannot extract the playlist.
- `update` creates missing Notion pages.
- New pages apply the default Notion template when `NOTION_USE_DEFAULT_TEMPLATE=true`.
- Existing pages are updated by `Video ID`.
- Existing page `Status` is preserved.
- `update` and `sync` exit non-zero when any page update/create fails.
- The default cache path is the OS temp directory, usually `/tmp/youtube-playlist.json`.
