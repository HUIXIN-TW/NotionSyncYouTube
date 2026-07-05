# YouTube Inbox to Notion

Sync videos from a YouTube playlist into a Notion backlog database.

The current implementation is intentionally small and one-way:

```txt
YouTube playlist -> Notion database
```

It fetches every video from a configured YouTube playlist, checks whether each
video already exists in Notion by `Video ID`, and creates a new Notion page only
for missing videos.

## Use Case

This project supports a simple knowledge backlog workflow:

1. Save videos quickly into a YouTube playlist, usually named `Inbox`.
2. Run the sync script.
3. Review and manage the imported videos in Notion.
4. Track status, category, URL, video ID, and optional duration bucket in Notion.

YouTube is treated as the capture surface. Notion is treated as the backlog and
workflow surface.

## Current Behavior

The script currently:

- Fetches all items from `YOUTUBE_PLAYLIST_ID`.
- Skips deleted and private YouTube placeholder videos.
- Fetches video durations with the YouTube `videos.list` API.
- Deduplicates records using the stable YouTube `videoId`.
- Creates missing Notion pages.
- Sets `Category` to `Youtube`.
- Sets `Status` to `Backlog`.
- Adds a canonical YouTube watch URL.
- Optionally maps video duration into a Notion `Length` select option.
- Prints a JSON sync summary at the end.

The script does not:

- Remove videos from YouTube.
- Delete Notion pages.
- Update existing Notion pages.
- Read private playlists.
- Read YouTube Watch Later.
- Write back from Notion to YouTube.

## Requirements

- Python 3.10 or newer.
- A YouTube Data API key.
- A public or unlisted YouTube playlist ID.
- A Notion internal integration token.
- A Notion database shared with that integration.

The script uses only the Python standard library. No package installation is
required.

## Project Structure

```txt
main.py                          Local entrypoint
notionsyncyoutube/config.py      Environment and .env configuration
notionsyncyoutube/dotenv.py      Minimal .env parser
notionsyncyoutube/http.py        JSON HTTP client
notionsyncyoutube/youtube.py     YouTube Data API client
notionsyncyoutube/notion.py      Notion API client
notionsyncyoutube/duration.py    YouTube duration parsing and Length mapping
notionsyncyoutube/sync.py        Sync orchestration
notionsyncyoutube/models.py      Shared data models
notionsyncyoutube/errors.py      Shared exception types
```

## Configuration

Set these environment variables before running the script.

For local runs, the script also reads a `.env` file from the current directory
when one exists. Values already present in the shell environment take priority.

Use `.env.example` as the template for local configuration.

```bash
YOUTUBE_API_KEY="your_youtube_api_key"
YOUTUBE_PLAYLIST_ID="your_youtube_playlist_id"

NOTION_TOKEN="secret_xxx"
NOTION_DATABASE_ID="your_notion_database_id"
```

## Notion Database Schema

The Notion database must contain these properties:

| Property   | Type   | Description |
| ---------- | ------ | ----------- |
| `Title`    | Title  | Video title from YouTube. |
| `Category` | Select | Static value set to `Youtube`. |
| `Status`   | Status | Static value set to `Backlog`. |
| `URL`      | URL    | Canonical YouTube watch URL. |
| `Video ID` | Text   | Stable YouTube video ID used for deduplication. |

Optional property:

| Property | Type   | Description |
| -------- | ------ | ----------- |
| `Length` | Select | Duration bucket derived from YouTube video duration. |

The `Length` select options must match the values produced by the script:

```txt
<= 15m
30–60m
60m+
```

Note: the script currently maps videos from 16 to 60 minutes into `30–60m`
because there is no separate `15-30m` bucket.

## Why `Video ID` Is the Unique Key

The sync uses YouTube `videoId`, not the URL, for deduplication. The same video
can appear in several URL forms:

```txt
https://www.youtube.com/watch?v=abc123
https://youtu.be/abc123
https://www.youtube.com/watch?v=abc123&t=60s
https://m.youtube.com/watch?v=abc123
```

The stable identifier is:

```txt
abc123
```

Keep `Video ID` in the Notion database even if it is hidden from the main view.

## Run

```bash
python main.py
```

Example output:

```txt
Fetching YouTube playlist items...
Fetched 12 YouTube videos.
SKIP   Existing video title [abc123]
CREATE New video title [def456]

Sync summary:
{
  "fetched": 12,
  "created": 1,
  "skipped_existing": 11,
  "errors": 0,
  "synced_at": "2026-07-05T08:00:00+00:00"
}
```

## Sync Logic

```txt
Fetch playlist items from YouTube
Fetch durations for those videos
For each video:
  Query Notion where Video ID equals videoId
  If a page exists:
    skip it
  If no page exists:
    create a new Notion page
Print sync summary
```

## Field Mapping

| Source | Notion property |
| ------ | --------------- |
| `snippet.title` | `Title` |
| `contentDetails.videoId` | `Video ID` |
| `https://www.youtube.com/watch?v=<videoId>` | `URL` |
| Static value `Youtube` | `Category` |
| Static value `Backlog` | `Status` |
| `contentDetails.duration` from `videos.list` | `Length` |

## Limitations

- Existing Notion pages are skipped, even if the YouTube title or duration has changed.
- Notion `Status` is hard-coded as a Notion `status` property, not a `select`.
- Notion `Category` and `Length` are hard-coded as `select` properties.
- The script raises an error on missing environment variables.
- A Notion page creation can fail if a configured select/status option does not exist.
- YouTube API quota and Notion API rate limits are not handled with retries.
- There is no dry-run mode.
- There are no tests yet.

## Future Direction

The intended next stage is controlled reverse sync, not full conflict-based
two-way sync.

Desired long-term behavior:

```txt
YouTube captures new items.
Notion owns canonical backlog state.
YouTube Inbox is reconciled from Notion for records where Status != Done.
Done records are not pushed back into YouTube Inbox.
```

Potential future work:

- Add OAuth for private playlists and playlist write operations.
- Store YouTube `playlistItemId` for future playlist cleanup.
- Add Notion-to-YouTube reconciliation.
- Remove playlist items when the Notion status becomes `Done`.
- Update existing Notion metadata when title or duration changes.
- Add dry-run mode.
- Add structured logging and retries.
- Add GitHub Actions or AWS Lambda scheduled execution.
- Add Notion schema validation.
- Add CLI arguments for playlist and database IDs.
- Add tests for duration parsing and Notion payload generation.
