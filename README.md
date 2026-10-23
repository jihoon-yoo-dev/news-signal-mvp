# news-signal-mvp

**Episode 2 — Box 1:** pull free US market/company headlines from RSS, print them in the terminal, and **dedupe** so a re-run only shows what’s new.

This is the first box of a small DIY Founder / News Signal MVP. It is **not** financial advice and does **not** trade.

## 3-box roadmap

| Box | Role | Status |
|-----|------|--------|
| **1** `ingest_rss.py` | RSS pull + dedupe + terminal output | **This repo (Episode 2)** |
| **2** `extract_company.py` | Best-effort US ticker / company name | Next (Episode 3+) |
| **3** `judge_jev.py` | Bullish / Bearish / Noise (+ short summary) | Later |

## What this repo does

1. Fetches **Google News RSS** (two US-oriented queries).
2. Prints each **new** item as: `published | title | link`
3. Remembers seen item ids in `.data/seen_ids.json` (gitignored) so the next run skips duplicates.
4. Optional `--poll` loop (~1 minute) for a live watch; default is a **one-shot** demo.

### Feed URLs (v1)

| Query | URL |
|-------|-----|
| stock market | `https://news.google.com/rss/search?q=stock+market&hl=en-US&gl=US&ceid=US:en` |
| US stocks | `https://news.google.com/rss/search?q=US+stocks&hl=en-US&gl=US&ceid=US:en` |

Free RSS refreshes on the order of **minutes**, not seconds — that matches how this tool is meant to be used.

## Requirements

- Python **3.12+**
- [uv](https://docs.astral.sh/uv/)

## How to run

```bash
git clone https://github.com/jihoon-yoo-dev/news-signal-mvp.git
cd news-signal-mvp
uv sync
uv run python src/ingest_rss.py
```

Optional ~1-minute polling:

```bash
uv run python src/ingest_rss.py --poll
# or: uv run python src/ingest_rss.py --poll --interval 60
```

Override feeds:

```bash
uv run python src/ingest_rss.py --feed 'https://news.google.com/rss/search?q=nasdaq&hl=en-US&gl=US&ceid=US:en'
```

Copy `.env.example` → `.env` only when later boxes need API keys. Box 1 needs none.

## Sample output

First run (VM smoke, 2026-10-23):

```text
# feeds=2 seen=0 mode=one-shot
2026-10-22 20:28:00 UTC | Nasdaq falls more than 2% for worst day since June ... - CNBC | https://news.google.com/rss/articles/...
2026-10-22 23:41:00 UTC | Stock Market News, Oct. 22, 2026: Tech Selloff Deepens ... - WSJ | https://news.google.com/rss/articles/...
...
# done: new=190 scanned=200 seen_total=190
```

Second run immediately after (same `.data/`):

```text
# feeds=2 seen=190 mode=one-shot
# done: new=0 scanned=200 seen_total=190
```

## Disclaimer

Educational / research demo only. **Not financial advice.** No buy/sell recommendations. Headlines can be wrong, delayed, or duplicated across outlets.

## Next (Episode 3+)

- Box 2: extract US tickers / company names from titles  
- Box 3: Jev (or LLM fallback) → Bullish / Bearish / Noise  
- Later: pipeline glue, Telegram alerts — still no auto-trading in the MVP
