from __future__ import annotations

import unittest
from unittest.mock import patch

from notionsyncyoutube.config import (
    NOTION_DATA_SOURCE_VERSION,
    NOTION_VERSION,
    Config,
    env_bool,
    validate_optional_value,
    validate_required_value,
)
from notionsyncyoutube.errors import ConfigError


class ConfigValidationTests(unittest.TestCase):
    def test_required_value_rejects_missing_and_placeholder_values(self) -> None:
        with self.assertRaisesRegex(ConfigError, "Missing required"):
            validate_required_value("NOTION_TOKEN", None)

        with self.assertRaisesRegex(ConfigError, "placeholder"):
            validate_required_value("NOTION_TOKEN", "secret_xxx")

    def test_optional_value_allows_empty_values(self) -> None:
        self.assertIsNone(validate_optional_value("NOTION_DATA_SOURCE_ID", None))
        self.assertIsNone(validate_optional_value("NOTION_DATA_SOURCE_ID", ""))

    def test_env_bool_recognizes_explicit_truthy_values(self) -> None:
        with patch.dict("os.environ", {"FEATURE_ENABLED": "yes"}, clear=True):
            self.assertTrue(env_bool("FEATURE_ENABLED", False))

        with patch.dict("os.environ", {"FEATURE_ENABLED": "off"}, clear=True):
            self.assertFalse(env_bool("FEATURE_ENABLED", True))

    def test_config_uses_data_source_api_version_when_configured(self) -> None:
        environment = {
            "YOUTUBE_API_KEY": "api-key",
            "YOUTUBE_PLAYLIST_ID": "playlist-id",
            "NOTION_TOKEN": "notion-token",
            "NOTION_DATABASE_ID": "database-id",
            "NOTION_DATA_SOURCE_ID": "data-source-id",
        }

        with (
            patch.dict("os.environ", environment, clear=True),
            patch("notionsyncyoutube.config.load_dotenv_if_present"),
        ):
            config = Config.from_environment()

        self.assertEqual(NOTION_DATA_SOURCE_VERSION, config.notion_version)

    def test_config_uses_legacy_api_version_without_data_source(self) -> None:
        environment = {
            "YOUTUBE_API_KEY": "api-key",
            "YOUTUBE_PLAYLIST_ID": "playlist-id",
            "NOTION_TOKEN": "notion-token",
            "NOTION_DATABASE_ID": "database-id",
        }

        with (
            patch.dict("os.environ", environment, clear=True),
            patch("notionsyncyoutube.config.load_dotenv_if_present"),
        ):
            config = Config.from_environment()

        self.assertEqual(NOTION_VERSION, config.notion_version)


if __name__ == "__main__":
    unittest.main()
