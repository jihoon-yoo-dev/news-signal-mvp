# news-signal-mvp

**Episode 3 — Box 2 + Box 3:** pull a **fresh snapshot** of recent US market headlines, extract a best-effort **company/ticker**, then **judge** **bullish / bearish / noise** with **confidence**, a short **reason**, and latency.

This is a DIY Founder / News Signal MVP. It is **not** financial advice and does **not** trade.

## 3-box roadmap

| Box | Role | Status |
|-----|------|--------|
| **1** `ingest_rss.py` | RSS pull + dedupe + terminal output | Shipped (Episode 2) |
| **2** `extract_company.py` | Best-effort US ticker / company name | **This episode** |
| **3** `judge_jev.py` | Bullish / Bearish / Noise + confidence + reason | **This episode** (Jev → LLM → heuristic) |

## What Episode 3 does

1. **Default live demo** (`demo_ep3.py`): fetch Google News RSS, **merge**, **sort by published desc**, take top **N≈20** (widen queries if under 10).
2. **Box 2** — `extract_company.py`: `$TICKER`, `(TICKER)`, known aliases; otherwise **UNKNOWN**.
3. **Box 3** — `judge_jev.py`: **Jev** → **OpenAI/Anthropic JSON** → **keyword heuristic**; every path returns a short **reason**.
4. Prints: `published | title | ticker/company | label | confidence | reason | backend | latency`.

### Live-demo design notes

- Google News RSS is **near-real-time best-effort**, not an exchange firehose.
- Live mode prefers **latest N by time** each run (fresh snapshot). Within one fetch, duplicate ids/titles are collapsed.
- Box 1 **seen-id dedupe** stays available for cron-style ingest (`ingest_rss.py`) and optionally via `demo_ep3.py --dedupe-seen` — **off by default** in the live demo.
- `neutral` from a model maps to series language **noise**.

## Requirements

- Python **3.12+**
- [uv](https://docs.astral.sh/uv/)

## How to run Episode 3 (one command)

```bash
git clone https://github.com/jihoon-yoo-dev/news-signal-mvp.git
cd news-signal-mvp
uv sync
uv run python src/demo_ep3.py
```

Default: live RSS snapshot of up to **20** newest headlines → extract → judge.

```bash
# Cap / widen floor
uv run python src/demo_ep3.py --limit 20 --min-floor 10

# Force heuristic judge
uv run python src/demo_ep3.py --backend heuristic

# Offline fixtures (no network)
uv run python src/demo_ep3.py --samples

# Optional Box-1-style seen filter (not the live default)
uv run python src/demo_ep3.py --dedupe-seen
```

Single-box helpers:

```bash
uv run python src/extract_company.py 'Apple unveils new AI features; AAPL shares jump'
uv run python src/judge_jev.py 'NVIDIA data-center demand surges; NVDA hits fresh record high'
```

Box 1 (Episode 2) cron-style ingest + seen-id dedupe:

```bash
uv run python src/ingest_rss.py
```

## Credentials (optional)

Copy `.env.example` → `.env` and fill only what you have. **Never commit `.env`.**

| Variable | Effect |
|----------|--------|
| `JEV_API_KEY` / `TYPESAFE_API_KEY` + `JEV_API_BASE` | Prefer Jev HTTP judge |
| `OPENAI_API_KEY` | LLM JSON fallback (+ reason) |
| `ANTHROPIC_API_KEY` | Anthropic JSON fallback (+ reason) |
| *(none)* | Offline **heuristic_fallback** (keyword reason) |

If Jev access is blocked or misconfigured, the demo **degrades honestly** — it does not invent a successful Jev response.

## Sample table shape

```text
# Episode 3 demo — live RSS snapshot feeds=2 scanned_unique=… returned=20 …
# flow: latest headlines → extract_company → judge(+reason) → table
# note: Google News RSS ≈ near-real-time best-effort, not a firehose
# disclaimer: educational demo only — not financial advice
PUBLISHED              | TITLE                                      | TICKER/CO      | LABEL    | CONF | REASON                               | BACKEND            |     MS
-----------------------|--------------------------------------------|----------------|----------|------|--------------------------------------|--------------------|-------
2026-10-26 22:01:00 UTC | Some US stock headline …                  | AAPL/Apple     | bullish  | 0.79 | bullish keywords: jump, growth       | heuristic_fallback |    0.1
…
# done: rows=20 judge_backend=heuristic_fallback
```

## Disclaimer

Educational / research / software-engineering demo only. **Not financial advice.** No buy/sell recommendations. Extraction is best-effort; labels and reasons can be wrong. Headlines can be delayed, duplicated, or misleading.

## Next (Episode 4+)

- Tighten the full `pipeline.py` glue  
- Optional Telegram alerts  
- Latency experiment (publish → signal) — still **no auto-trading** in the MVP
