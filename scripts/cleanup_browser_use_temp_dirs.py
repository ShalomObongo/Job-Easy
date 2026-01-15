#!/usr/bin/env python3
"""Clean up Browser Use temp profile directories.

Browser Use creates temp `user_data_dir` folders like:
  browser-use-user-data-dir-xxxxxx
under the system temp directory. These can accumulate over time.

Usage:
  python scripts/cleanup_browser_use_temp_dirs.py
  python scripts/cleanup_browser_use_temp_dirs.py --dry-run
  python scripts/cleanup_browser_use_temp_dirs.py --older-than-hours 24
"""

from __future__ import annotations

import argparse
import os
import shutil
import tempfile
import time
from pathlib import Path

PREFIX = "browser-use-user-data-dir-"


def _iter_temp_roots() -> list[Path]:
    roots: list[Path] = []
    for root in (tempfile.gettempdir(), os.getenv("TMPDIR"), "/var/folders"):
        if not root:
            continue
        try:
            roots.append(Path(str(root)).expanduser().resolve())
        except Exception:
            continue
    # De-dupe while preserving order
    seen: set[str] = set()
    unique: list[Path] = []
    for root in roots:
        key = str(root)
        if key in seen:
            continue
        seen.add(key)
        unique.append(root)
    return unique


def _find_candidates(root: Path) -> list[Path]:
    try:
        # On macOS, the directories are usually under .../T/
        return [p for p in root.rglob(f"{PREFIX}*") if p.is_dir()]
    except Exception:
        return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Only print actions")
    parser.add_argument(
        "--older-than-hours",
        type=float,
        default=0.0,
        help="Only delete directories older than this many hours (default: 0)",
    )
    args = parser.parse_args()

    cutoff = time.time() - (args.older_than_hours * 3600.0)
    deleted = 0
    kept = 0

    for root in _iter_temp_roots():
        for path in _find_candidates(root):
            try:
                mtime = path.stat().st_mtime
            except Exception:
                mtime = 0

            if args.older_than_hours and mtime > cutoff:
                kept += 1
                continue

            if args.dry_run:
                print(f"[dry-run] would delete {path}")
                deleted += 1
                continue

            try:
                shutil.rmtree(path, ignore_errors=True)
                print(f"deleted {path}")
                deleted += 1
            except Exception as e:
                print(f"failed to delete {path}: {e}")
                kept += 1

    print(f"done: deleted={deleted} kept={kept}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
