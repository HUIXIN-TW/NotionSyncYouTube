from __future__ import annotations

import os
from dataclasses import dataclass

from notionsyncyoutube.dotenv import load_dotenv_if_present
from notionsyncyoutube.errors import ConfigError


NOTION_VERSION = "2022-06-28"

DEFAULT_CATEGORY = "Youtube"
DEFAULT_STATUS = "Backlog"
PLACEHOLDER_VALUES = {
    "secret_xxx",
    "your_notion_database_id",
    "your_youtube_api_key",
    "your_youtube_playlist_id",
}


def validate_required_value(name: str, value: str | None) -> str:
    if not value:
        raise ConfigError(f"Missing required environment variable: {name}")

    if value in PLACEHOLDER_VALUES or value.startswith("your_"):
        raise ConfigError(
            f"{name} still uses a placeholder value. Set the real value before running sync."
        )

    return value


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
        return cls(
            youtube_api_key=validate_required_value(
                "YOUTUBE_API_KEY",
                required_values["YOUTUBE_API_KEY"],
            ),
            youtube_playlist_id=validate_required_value(
                "YOUTUBE_PLAYLIST_ID",
                required_values["YOUTUBE_PLAYLIST_ID"],
            ),
            notion_token=validate_required_value(
                "NOTION_TOKEN",
                required_values["NOTION_TOKEN"],
            ),
            notion_database_id=validate_required_value(
                "NOTION_DATABASE_ID",
                required_values["NOTION_DATABASE_ID"],
            ),
        )
