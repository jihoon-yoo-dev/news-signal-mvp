# news-signal-mvp

**Episode 3 — Box 2 + Box 3:** extract a best-effort US **company/ticker** from each headline, then **judge** it as **bullish / bearish / noise** with a **confidence** score and latency.

This is a DIY Founder / News Signal MVP. It is **not** financial advice and does **not** trade.

## 3-box roadmap

| Box | Role | Status |
|-----|------|--------|
| **1** `ingest_rss.py` | RSS pull + dedupe + terminal output | Shipped (Episode 2) |
| **2** `extract_company.py` | Best-effort US ticker / company name | **This episode** |
| **3** `judge_jev.py` | Bullish / Bearish / Noise + confidence | **This episode** (Jev → LLM → heuristic) |

## What Episode 3 does

1. Takes headlines from `samples/headlines.json` (offline demo) or a few live RSS items.
2. **Box 2** — `extract_company.py`: rules for `$TICKER`, `(TICKER)`, known company aliases, bare known tickers.
3. **Box 3** — `judge_jev.py`: tries **Jev** if credentials exist; else **OpenAI/Anthropic JSON** classify if a key exists; else a clearly labeled **keyword heuristic** fallback.
4. Prints a table: ticker · company · label · confidence · latency · backend · headline.

`neutral` from a model is mapped to series language **noise**.

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

That uses offline samples (no API keys required). Force the heuristic:

```bash
uv run python src/demo_ep3.py --backend heuristic
```

Optional: a few live RSS headlines (still extract → judge):

```bash
uv run python src/demo_ep3.py --rss --limit 6
```

Single-box helpers:

```bash
uv run python src/extract_company.py 'Apple unveils new AI features; AAPL shares jump'
uv run python src/judge_jev.py 'NVIDIA data-center demand surges; NVDA hits fresh record high'
```

Box 1 (Episode 2) still works:

```bash
uv run python src/ingest_rss.py
```

## Credentials (optional)

Copy `.env.example` → `.env` and fill only what you have. **Never commit `.env`.**

| Variable | Effect |
|----------|--------|
| `JEV_API_KEY` / `TYPESAFE_API_KEY` + `JEV_API_BASE` | Prefer Jev HTTP judge |
| `OPENAI_API_KEY` | LLM JSON fallback |
| `ANTHROPIC_API_KEY` | Anthropic JSON fallback |
| *(none)* | Offline **heuristic_fallback** (demo still works) |

If Jev access is blocked or misconfigured, the demo **degrades honestly** — it does not invent a successful Jev response.

## Sample table (heuristic)

```text
# Episode 3 demo — source=samples (samples/headlines.json)
# flow: headline → extract_company → judge → table
# disclaimer: educational demo only — not financial advice
TICKER COMPANY      LABEL     CONF      MS BACKEND            HEADLINE
------ ------------ -------- ----- ------- ------------------ --------
AAPL   Apple        bullish   0.67     0.1 heuristic_fallback Apple unveils new AI features; AAPL shares jump…
NVDA   NVIDIA       bullish   0.79     0.0 heuristic_fallback NVIDIA data-center demand surges; NVDA hits…
TSLA   Tesla        bearish   0.67     0.0 heuristic_fallback Tesla recalls 40,000 vehicles…; TSLA slides
…
# done: rows=8 judge_backend=heuristic_fallback
```

## Disclaimer

Educational / research / software-engineering demo only. **Not financial advice.** No buy/sell recommendations. Extraction is best-effort; labels can be wrong. Headlines can be delayed, duplicated, or misleading.

## Next (Episode 4+)

- Tighten the full `pipeline.py` glue + richer summary field  
- Optional Telegram alerts  
- Latency experiment (publish → signal) — still **no auto-trading** in the MVP
