from notionsyncyoutube.config import Config
from notionsyncyoutube.errors import ApiError, ConfigError
from notionsyncyoutube.sync import build_sync


def main() -> None:
    try:
        config = Config.from_environment()
        summary = build_sync(config).run()
    except ConfigError as exc:
        raise SystemExit(f"Configuration error: {exc}") from exc
    except ApiError as exc:
        raise SystemExit(f"API error: {exc}") from exc

    print("\nSync summary:")
    print(summary.to_json())


if __name__ == "__main__":
    main()
