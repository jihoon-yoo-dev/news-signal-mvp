#!/usr/bin/env python3
"""Episode 3 live demo: fresh RSS snapshot → extract → judge → table.

Default mode pulls the **most recent N** US market headlines (target 20,
floor 10 when feeds allow), not “only unseen” seen-id filtering.
Google News RSS is near-real-time best-effort — not an exchange firehose.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

from extract_company import extract_company
from ingest_rss import USER_AGENT, fetch_feed, format_published, item_id
from judge_jev import judge

DEFAULT_LIMIT = 20
MIN_FLOOR = 10

# Primary + widen queries (Google News RSS). Merge, sort by published desc, cap.
PRIMARY_FEEDS: list[str] = [
    (
        "https://news.google.com/rss/search?"
        "q=stock+market&hl=en-US&gl=US&ceid=US:en"
    ),
    (
        "https://news.google.com/rss/search?"
        "q=US+stocks&hl=en-US&gl=US&ceid=US:en"
    ),
]
WIDEN_FEEDS: list[str] = [
    (
        "https://news.google.com/rss/search?"
        "q=earnings+OR+Wall+Street&hl=en-US&gl=US&ceid=US:en"
    ),
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def re_strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text).replace("\n", " ").strip()


def trunc(text: str, width: int) -> str:
    text = text.replace("\n", " ").strip()
    if len(text) <= width:
        return text
    return text[: max(0, width - 1)] + "…"


@dataclass
class HeadlineRow:
    published: str
    published_ts: float  # epoch for sort; 0 if unknown
    title: str
    snippet: str | None
    link: str
    eid: str


def _entry_ts(entry: dict[str, Any]) -> float:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        try:
            dt = datetime(*parsed[:6], tzinfo=timezone.utc)
            return dt.timestamp()
        except (TypeError, ValueError, OverflowError):
            return 0.0
    return 0.0


def _entry_to_row(entry: dict[str, Any]) -> HeadlineRow | None:
    title = (entry.get("title") or "").strip().replace("\n", " ")
    if not title:
        return None
    summary = (entry.get("summary") or entry.get("description") or "").strip()
    if "<" in summary:
        summary = re_strip_tags(summary)
    return HeadlineRow(
        published=format_published(entry),
        published_ts=_entry_ts(entry),
        title=title,
        snippet=summary or None,
        link=(entry.get("link") or "").strip(),
        eid=item_id(entry),
    )


def _fetch_feed_rows(client: httpx.Client, url: str) -> list[HeadlineRow]:
    try:
        feed = fetch_feed(client, url)
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] feed failed: {url} ({exc})", file=sys.stderr)
        return []
    rows: list[HeadlineRow] = []
    for entry in feed.entries:
        row = _entry_to_row(entry)
        if row:
            rows.append(row)
    return rows


def _merge_unique(rows: list[HeadlineRow]) -> list[HeadlineRow]:
    """Dedupe within one fetch (by id and normalized title). Keep newest."""
    by_id: dict[str, HeadlineRow] = {}
    for row in rows:
        key = row.eid or f"title:{row.title.casefold()}"
        prev = by_id.get(key)
        if prev is None or row.published_ts >= prev.published_ts:
            by_id[key] = row
    # Second pass: collapse identical titles that arrived under different ids/feeds.
    by_title: dict[str, HeadlineRow] = {}
    for row in by_id.values():
        tkey = re.sub(r"\s+", " ", row.title).casefold()
        prev = by_title.get(tkey)
        if prev is None or row.published_ts >= prev.published_ts:
            by_title[tkey] = row
    merged = list(by_title.values())
    merged.sort(key=lambda r: (r.published_ts, r.title), reverse=True)
    return merged


def load_live_snapshot(
    *,
    limit: int = DEFAULT_LIMIT,
    min_floor: int = MIN_FLOOR,
) -> tuple[list[HeadlineRow], str]:
    """Fetch, merge, sort by published desc, take top N.

    If primary queries yield fewer than ``min_floor``, widen with extra feeds.
    """
    limit = max(1, limit)
    min_floor = max(1, min(min_floor, limit))
    collected: list[HeadlineRow] = []
    used: list[str] = []

    with httpx.Client(timeout=30.0, headers={"User-Agent": USER_AGENT}) as client:
        for url in PRIMARY_FEEDS:
            used.append(url)
            collected.extend(_fetch_feed_rows(client, url))
        merged = _merge_unique(collected)
        if len(merged) < min_floor:
            for url in WIDEN_FEEDS:
                if url in used:
                    continue
                used.append(url)
                collected.extend(_fetch_feed_rows(client, url))
            merged = _merge_unique(collected)

    top = merged[:limit]
    note = (
        f"live RSS snapshot feeds={len(used)} scanned_unique={len(merged)} "
        f"returned={len(top)} (sorted published desc; not exchange firehose)"
    )
    return top, note


def load_samples(path: Path) -> list[HeadlineRow]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows: list[HeadlineRow] = []
    for i, item in enumerate(raw):
        if isinstance(item, str):
            title, snippet = item, None
        else:
            title = str(item.get("title") or "").strip()
            snippet = item.get("snippet")
            snippet = str(snippet) if snippet else None
        if not title:
            continue
        rows.append(
            HeadlineRow(
                published="sample",
                published_ts=float(len(raw) - i),
                title=title,
                snippet=snippet,
                link="",
                eid=f"sample:{i}:{title[:40]}",
            )
        )
    return rows


def print_table(
    rows: list[HeadlineRow],
    *,
    force_backend: str | None,
) -> str:
    header = (
        f"{'PUBLISHED':<24} | {'TITLE':<42} | {'TICKER/CO':<14} | "
        f"{'LABEL':<8} | {'CONF':>4} | {'REASON':<36} | {'BACKEND':<18} | {'MS':>6}"
    )
    print(header)
    print("-" * len(header))
    first_backend = ""
    for row in rows:
        ex = extract_company(row.title, row.snippet)
        ticker = ex.ticker or "UNKNOWN"
        company = ex.company or "-"
        jd = judge(row.title, row.snippet, force_backend=force_backend)
        if not first_backend:
            first_backend = jd.backend
        ticker_co = trunc(f"{ticker}/{company}", 14)
        reason = jd.reason
        if ticker == "UNKNOWN":
            reason = trunc(f"{reason}; extract:none→UNKNOWN", 72)
        print(
            f"{trunc(row.published, 24):<24} | {trunc(row.title, 42):<42} | "
            f"{ticker_co:<14} | {jd.label:<8} | {jd.confidence:4.2f} | "
            f"{trunc(reason, 36):<36} | {jd.backend:<18} | {jd.latency_ms:6.1f}"
        )
    return first_backend


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Episode 3 demo: fetch recent US headlines → extract → judge "
            "(default: live snapshot of ~20)."
        )
    )
    parser.add_argument(
        "--samples",
        nargs="?",
        const="DEFAULT",
        default=None,
        metavar="PATH",
        help="Use offline samples instead of live RSS (optional path).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Max headlines after merge/sort (default: {DEFAULT_LIMIT}).",
    )
    parser.add_argument(
        "--min-floor",
        type=int,
        default=MIN_FLOOR,
        help=(
            f"If primary feeds yield fewer than this, widen queries "
            f"(default: {MIN_FLOOR})."
        ),
    )
    parser.add_argument(
        "--backend",
        default=None,
        help="Force judge backend: jev | openai | anthropic | heuristic",
    )
    parser.add_argument(
        "--dedupe-seen",
        action="store_true",
        help=(
            "Optional Box-1-style seen-id filter (off by default — live demo "
            "prefers a fresh latest-N snapshot each run)."
        ),
    )
    return parser.parse_args(argv)


def _apply_seen_filter(rows: list[HeadlineRow], root: Path) -> list[HeadlineRow]:
    from ingest_rss import SEEN_PATH, load_seen

    seen = load_seen(root / SEEN_PATH)
    return [r for r in rows if r.eid not in seen]


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = parse_args(argv)
    root = _repo_root()

    if args.samples is not None:
        path = (
            root / "samples" / "headlines.json"
            if args.samples == "DEFAULT"
            else Path(args.samples)
        )
        if not path.exists():
            print(f"samples not found: {path}", file=sys.stderr)
            return 1
        rows = load_samples(path)
        source = f"samples ({path})"
    else:
        rows, source = load_live_snapshot(
            limit=max(1, args.limit),
            min_floor=max(1, args.min_floor),
        )
        if args.dedupe_seen:
            before = len(rows)
            rows = _apply_seen_filter(rows, root)
            source += f"; dedupe-seen kept={len(rows)}/{before}"

    if not rows:
        print("No headlines to judge.", file=sys.stderr)
        return 1

    print(f"# Episode 3 demo — {source}")
    print("# flow: latest headlines → extract_company → judge(+reason) → table")
    print("# note: Google News RSS ≈ near-real-time best-effort, not a firehose")
    print("# disclaimer: educational demo only — not financial advice")
    backend = print_table(rows, force_backend=args.backend)
    print(f"# done: rows={len(rows)} judge_backend={backend}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
