from __future__ import annotations

import os
from dataclasses import dataclass

from notionsyncyoutube.dotenv import load_dotenv_if_present
from notionsyncyoutube.errors import ConfigError


NOTION_VERSION = "2022-06-28"

DEFAULT_CATEGORY = "Youtube"
DEFAULT_STATUS = "Backlog"


@dataclass(frozen=True)
class Config:
    youtube_api_key: str
    youtube_playlist_id: str
    notion_token: str
    notion_database_id: str
    notion_version: str = NOTION_VERSION
    default_category: str = DEFAULT_CATEGORY
    default_status: str = DEFAULT_STATUS

    @classmethod
    def from_environment(cls) -> "Config":
        load_dotenv_if_present()

        required_values = {
            "YOUTUBE_API_KEY": os.getenv("YOUTUBE_API_KEY"),
            "YOUTUBE_PLAYLIST_ID": os.getenv("YOUTUBE_PLAYLIST_ID"),
            "NOTION_TOKEN": os.getenv("NOTION_TOKEN"),
            "NOTION_DATABASE_ID": os.getenv("NOTION_DATABASE_ID"),
        }
        missing = [name for name, value in required_values.items() if not value]

        if missing:
            joined = ", ".join(missing)
            raise ConfigError(f"Missing required environment variable(s): {joined}")

        return cls(
            youtube_api_key=required_values["YOUTUBE_API_KEY"] or "",
            youtube_playlist_id=required_values["YOUTUBE_PLAYLIST_ID"] or "",
            notion_token=required_values["NOTION_TOKEN"] or "",
            notion_database_id=required_values["NOTION_DATABASE_ID"] or "",
        )
