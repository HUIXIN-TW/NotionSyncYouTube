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
NOTION_USE_DEFAULT_TEMPLATE=true
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
| `Format`   | Multi-select | Includes `Video`; retains other Format tags. |
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
- Existing pages are updated for metadata such as title, URL, format, and length.
- Existing page `Status` is preserved, so `Active` or `Done` is not reset to `Backlog`.
- `Category` is not required, read, or written; existing values are left untouched.
- The `Format` multi-select option `Video` must exist in the Notion data source.
- Updates add `Video` only when missing; existing Format selections (e.g. `PDF`) are preserved.
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

## Deploy to AWS Lambda with Pulumi

The `infra/` Pulumi project deploys `handler.lambda_handler` and creates an
EventBridge schedule that runs every four hours, starting at 00:00 UTC. The
Lambda uses the `yt-dlp` workflow, so a public playlist does not require a
YouTube API key. The build bundles a pinned Linux x86_64 Deno runtime and
matching `yt-dlp-ejs` solver so yt-dlp can handle YouTube's JavaScript
challenges in Lambda.
Duration enrichment uses flat playlist metadata first and only falls back to a
per-video request when a playlist entry does not include duration.

Install and authenticate the AWS CLI and Pulumi CLI first, then install the
Pulumi dependencies and build the Lambda bundle:

```bash
uv pip install -r infra/requirements.txt
./script/build-lambda.sh
cd infra
pulumi stack init personal-sandbox
```

Store or rotate the Notion token in SSM Parameter Store as a `SecureString`.
This command is repeatable and keeps the value out of Pulumi state and Lambda
environment configuration:

```bash
aws ssm put-parameter \
  --profile personal-sandbox \
  --region ap-southeast-2 \
  --name NOTION_TOKEN \
  --type SecureString \
  --value "$NOTION_TOKEN" \
  --overwrite
```

Configure the required non-secret Pulumi values. The local, gitignored stack
configuration pins deployment to the `personal-sandbox` AWS profile and account
`590184055616`:

```txt
YouTubePlaylistId
NotionTokenParameterName
NotionDatabaseId
```

```bash
pulumi config set youtubePlaylistId "$YOUTUBE_PLAYLIST_ID"
pulumi config set notionTokenParameterName NOTION_TOKEN
pulumi config set notionDatabaseId "$NOTION_DATABASE_ID"
pulumi config set notionDataSourceId "${NOTION_DATA_SOURCE_ID:-}"
pulumi config set notionUseDefaultTemplate "${NOTION_USE_DEFAULT_TEMPLATE:-true}"
pulumi config set youtubeEnrichLengths "${YOUTUBE_ENRICH_LENGTHS:-true}"
pulumi up
```

`NotionDataSourceId`, `NotionUseDefaultTemplate`, and `YoutubeEnrichLengths` are
configurable. Lambda receives only the SSM parameter name and has
`ssm:GetParameter` permission scoped to that single parameter. The handler
retrieves and decrypts the token at invocation time.

To invoke the deployed function once immediately:

```bash
aws lambda invoke \
  --profile personal-sandbox \
  --function-name "$(pulumi stack output notion-sync-youtube_name)" \
  --cli-binary-format raw-in-base64-out \
  --payload '{}' /tmp/youtube-notion-sync-response.json
cat /tmp/youtube-notion-sync-response.json
```

To inspect scheduled executions:

```bash
aws logs tail /aws/lambda/<function-name> --follow
```

## One-Time Notion Format Backfill

To migrate existing pages without altering `Category` or overwriting a populated
`Format`, use the following dry-run first (local environment with the Notion
integration token and `NOTION_DATA_SOURCE_ID`):

```bash
uv run python script/backfill-format.py
uv run python script/backfill-format.py --apply
```

This script maps legacy `Youtube -> Video`, `Podcast/Audible -> Audio`, and
`Kindle -> Ebook`. Generic `Book` entries are left unchanged because their
actual medium cannot be determined from the category. `EPUB` and `PDF` are
available in the new Format schema, but neither is inferred from Book alone.

After checking that the remaining YouTube entries all have `Format = Video`,
change the Notion YouTube and ActiveVideo view filters from `Category = Youtube`
to multi-select `Format contains Video`. Keep the legacy views unchanged until the backfill
finishes to prevent existing items disappearing from view. This migration is
not part of the scheduled Lambda sync.

For tests: `python -m unittest discover -s tests -v`.
