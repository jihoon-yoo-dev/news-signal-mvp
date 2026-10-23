#!/usr/bin/env python3
"""Episode 2 Box 1 — RSS ingest + dedupe for US market headlines.

Pulls Google News RSS, prints new items as `published | title | link`,
and persists seen ids under `.data/` so re-runs skip duplicates.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import feedparser
import httpx
from dotenv import load_dotenv

# Google News RSS — free, broad, recent US market / company headlines.
# Documented in README; override via --feed if needed.
DEFAULT_FEEDS: list[str] = [
    (
        "https://news.google.com/rss/search?"
        "q=stock+market&hl=en-US&gl=US&ceid=US:en"
    ),
    (
        "https://news.google.com/rss/search?"
        "q=US+stocks&hl=en-US&gl=US&ceid=US:en"
    ),
]

USER_AGENT = "news-signal-mvp/0.1 (+https://github.com/jihoon-yoo-dev/news-signal-mvp)"
SEEN_PATH = Path(".data/seen_ids.json")
POLL_SECONDS = 60


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_seen(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return set()
    if isinstance(raw, list):
        return {str(x) for x in raw}
    if isinstance(raw, dict) and "ids" in raw:
        return {str(x) for x in raw["ids"]}
    return set()


def save_seen(path: Path, ids: set[str], *, max_ids: int = 5000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Keep newest-ish by dropping arbitrary oldest when over cap (set has no order;
    # we store a list sorted for stable files). Cap prevents unbounded growth.
    ordered = sorted(ids)
    if len(ordered) > max_ids:
        ordered = ordered[-max_ids:]
    path.write_text(
        json.dumps({"ids": ordered}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def item_id(entry: dict[str, Any]) -> str:
    for key in ("id", "guid", "link"):
        value = entry.get(key)
        if value:
            return str(value).strip()
    title = (entry.get("title") or "").strip()
    published = (entry.get("published") or entry.get("updated") or "").strip()
    return f"{published}|{title}"


def format_published(entry: dict[str, Any]) -> str:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        try:
            dt = datetime(*parsed[:6], tzinfo=timezone.utc)
            return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except (TypeError, ValueError, OverflowError):
            pass
    return (entry.get("published") or entry.get("updated") or "unknown").strip()


def fetch_feed(client: httpx.Client, url: str) -> feedparser.FeedParserDict:
    response = client.get(url, follow_redirects=True)
    response.raise_for_status()
    return feedparser.parse(response.content)


def ingest_once(
    feeds: list[str],
    seen: set[str],
    *,
    client: httpx.Client,
) -> tuple[int, int]:
    """Fetch feeds, print new items, update `seen`. Returns (new_count, scanned)."""
    new_count = 0
    scanned = 0
    # Collect then print so multi-feed dedupe within one run is consistent.
    fresh: list[tuple[str, str, str, str]] = []

    for url in feeds:
        try:
            feed = fetch_feed(client, url)
        except httpx.HTTPError as exc:
            print(f"[warn] fetch failed: {url} ({exc})", file=sys.stderr)
            continue
        for entry in feed.entries:
            scanned += 1
            eid = item_id(entry)
            if not eid or eid in seen:
                continue
            seen.add(eid)
            title = (entry.get("title") or "").strip().replace("\n", " ")
            link = (entry.get("link") or "").strip()
            published = format_published(entry)
            fresh.append((eid, published, title, link))
            new_count += 1

    for _eid, published, title, link in fresh:
        print(f"{published} | {title} | {link}")

    return new_count, scanned


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Episode 2 Box 1: pull US market headlines from Google News RSS."
    )
    parser.add_argument(
        "--poll",
        action="store_true",
        help=f"Re-fetch every {POLL_SECONDS}s until Ctrl-C (default: one-shot).",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=POLL_SECONDS,
        metavar="SEC",
        help=f"Polling interval in seconds (default: {POLL_SECONDS}).",
    )
    parser.add_argument(
        "--feed",
        action="append",
        dest="feeds",
        metavar="URL",
        help="Override default feeds (repeatable). Default: two Google News queries.",
    )
    parser.add_argument(
        "--seen-file",
        type=Path,
        default=None,
        help="Path to seen-id store (default: .data/seen_ids.json under repo root).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = parse_args(argv)
    root = _repo_root()
    seen_path = args.seen_file or (root / SEEN_PATH)
    feeds = args.feeds or list(DEFAULT_FEEDS)

    seen = load_seen(seen_path)
    print(
        f"# feeds={len(feeds)} seen={len(seen)} mode={'poll' if args.poll else 'one-shot'}",
        flush=True,
    )

    with httpx.Client(timeout=30.0, headers={"User-Agent": USER_AGENT}) as client:
        while True:
            new_count, scanned = ingest_once(feeds, seen, client=client)
            save_seen(seen_path, seen)
            print(
                f"# done: new={new_count} scanned={scanned} seen_total={len(seen)}",
                flush=True,
            )
            if not args.poll:
                break
            time.sleep(max(1, args.interval))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
