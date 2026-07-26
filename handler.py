from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path
from typing import Any


def _load_quick_sync_module() -> Any:
    module_path = Path(__file__).parent / "script" / "fetch-to-notion.py"
    spec = importlib.util.spec_from_file_location("fetch_to_notion", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load quick sync module: {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Run one YouTube-to-Notion synchronization job.

    The EventBridge event is intentionally not used: the Lambda is a daily
    full synchronization, so the same handler also works for a manual test
    invocation.
    """
    del event, context

    quick_sync = _load_quick_sync_module()
    cache_path = Path(tempfile.gettempdir()) / "youtube-playlist.json"
    result = quick_sync.sync(cache_path)

    if result.get("errors", 0) > 0:
        raise RuntimeError(f"Synchronization completed with errors: {result}")

    return result
