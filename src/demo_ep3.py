#!/usr/bin/env python3
"""Episode 3 demo glue: samples (or live RSS) → extract → judge → table.

Does not claim to be the full multi-episode pipeline — just enough to demo
Box 2 + Box 3 under the hood.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from extract_company import extract_company
from judge_jev import judge


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_samples(path: Path) -> list[tuple[str, str | None]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows: list[tuple[str, str | None]] = []
    for item in raw:
        if isinstance(item, str):
            rows.append((item, None))
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        snippet = item.get("snippet")
        rows.append((title, str(snippet) if snippet else None))
    return rows


def load_from_rss(limit: int) -> list[tuple[str, str | None]]:
    """Reuse Box 1 fetch without mutating seen-id store."""
    import httpx

    from ingest_rss import DEFAULT_FEEDS, USER_AGENT, fetch_feed

    rows: list[tuple[str, str | None]] = []
    with httpx.Client(timeout=30.0, headers={"User-Agent": USER_AGENT}) as client:
        for url in DEFAULT_FEEDS:
            try:
                feed = fetch_feed(client, url)
            except Exception as exc:  # noqa: BLE001
                print(f"[warn] feed failed: {exc}", file=sys.stderr)
                continue
            for entry in feed.entries:
                title = (entry.get("title") or "").strip().replace("\n", " ")
                if not title:
                    continue
                summary = (entry.get("summary") or entry.get("description") or "").strip()
                # Strip crude HTML if present
                if "<" in summary:
                    summary = re_strip_tags(summary)
                rows.append((title, summary or None))
                if len(rows) >= limit:
                    return rows
    return rows[:limit]


def re_strip_tags(text: str) -> str:
    import re

    return re.sub(r"<[^>]+>", " ", text).replace("\n", " ").strip()


def trunc(text: str, width: int) -> str:
    text = text.replace("\n", " ").strip()
    if len(text) <= width:
        return text
    return text[: max(0, width - 1)] + "…"


def print_table(
    rows: list[tuple[str, str | None]],
    *,
    force_backend: str | None,
) -> str:
    """Print a fixed-width table; return backend used on first row."""
    header = (
        f"{'TICKER':<6} {'COMPANY':<12} {'LABEL':<8} {'CONF':>5} "
        f"{'MS':>7} {'BACKEND':<18} HEADLINE"
    )
    print(header)
    print("-" * len(header))
    first_backend = ""
    for title, snippet in rows:
        ex = extract_company(title, snippet)
        jd = judge(title, snippet, force_backend=force_backend)
        if not first_backend:
            first_backend = jd.backend
        ticker = ex.ticker or "-"
        company = trunc(ex.company or "-", 12)
        print(
            f"{ticker:<6} {company:<12} {jd.label:<8} {jd.confidence:5.2f} "
            f"{jd.latency_ms:7.1f} {jd.backend:<18} {trunc(title, 64)}"
        )
    return first_backend


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Episode 3 demo: extract company/ticker then judge signal."
    )
    parser.add_argument(
        "--samples",
        type=Path,
        default=None,
        help="JSON samples path (default: samples/headlines.json).",
    )
    parser.add_argument(
        "--rss",
        action="store_true",
        help="Pull a few live RSS headlines instead of samples.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=8,
        help="Max headlines when using --rss (default: 8).",
    )
    parser.add_argument(
        "--backend",
        default=None,
        help="Force judge backend: jev | openai | anthropic | heuristic",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = parse_args(argv)
    root = _repo_root()

    if args.rss:
        rows = load_from_rss(max(1, args.limit))
        source = f"live RSS (n={len(rows)})"
    else:
        path = args.samples or (root / "samples" / "headlines.json")
        if not path.exists():
            print(f"samples not found: {path}", file=sys.stderr)
            return 1
        rows = load_samples(path)
        source = f"samples ({path})"

    if not rows:
        print("No headlines to judge.", file=sys.stderr)
        return 1

    print(f"# Episode 3 demo — source={source}")
    print("# flow: headline → extract_company → judge → table")
    print("# disclaimer: educational demo only — not financial advice")
    backend = print_table(rows, force_backend=args.backend)
    print(f"# done: rows={len(rows)} judge_backend={backend}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
