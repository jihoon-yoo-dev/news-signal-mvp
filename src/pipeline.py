#!/usr/bin/env python3
"""Episode 4 pipeline glue: RSS ingest → extract_company → judge → terminal table.

Reuses Box 1–3 modules (and Episode 3 snapshot helpers). No Telegram, no trading.
Judge order stays honest: Jev → LLM → heuristic when keys are absent.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from demo_ep3 import (
    DEFAULT_LIMIT,
    MIN_FLOOR,
    load_live_snapshot,
    load_samples,
    print_table,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Episode 4 pipeline: RSS → extract_company → judge → table "
            "(default: live latest-N snapshot)."
        )
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
        "--samples",
        nargs="?",
        const="DEFAULT",
        default=None,
        metavar="PATH",
        help="Use offline samples instead of live RSS (optional path).",
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
            "Optional Box-1-style seen-id filter (off by default — pipeline "
            "prefers a fresh latest-N snapshot each run)."
        ),
    )
    return parser.parse_args(argv)


def _apply_seen_filter(rows, root: Path):
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
        rows = load_samples(path)[: max(1, args.limit)]
        source = f"samples ({path}) limit={len(rows)}"
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
        print("No headlines to process.", file=sys.stderr)
        return 1

    print(f"# Episode 4 pipeline — {source}")
    print("# flow: RSS ingest → extract_company → judge → table")
    print("# note: Google News RSS ≈ near-real-time best-effort, not a firehose")
    print("# disclaimer: educational demo only — not financial advice")
    backend = print_table(rows, force_backend=args.backend)
    print(f"# done: rows={len(rows)} judge_backend={backend}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
