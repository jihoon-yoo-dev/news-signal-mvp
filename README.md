# news-signal-mvp

A small **educational** demo: recent **US stock news** → find a **ticker/company** (best effort) → classify **bullish / bearish / noise** with a short **reason**.

**Not financial advice. Does not trade.**

Full plain-English walkthrough (every flag, column meanings, sample rows): **[docs/DEMO_USAGE.md](docs/DEMO_USAGE.md)**.

**Want to connect Jev (TypeSafe)?** Step-by-step env + verify guide: **[docs/JEV_SETUP.md](docs/JEV_SETUP.md)**.  
Without Jev keys the demo still runs using the built-in keyword judge.

---

## What is this?

| Step | What happens |
|------|----------------|
| 1. Headlines | Pull a fresh snapshot of recent US market / stock headlines (free Google News RSS). |
| 2. Extract | Guess company + ticker when possible (`UNKNOWN` if not). |
| 3. Judge | Label **bullish**, **bearish**, or **noise**, plus confidence, a one-line reason, and latency. |

Built for the DIY Founder “News Signal MVP” series (Episode 3 = extract + judge). You can run it with **no API keys**.

---

## How to run the Episode 3 demo

### Quick start (copy-paste)

Needs Python **3.12+** and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/jihoon-yoo-dev/news-signal-mvp.git
cd news-signal-mvp
uv sync
uv run python src/demo_ep3.py
```

Default: about **20** newest headlines → extract → judge → print a table.

### Useful variants

```bash
# Shorter table
uv run python src/demo_ep3.py --limit 5

# Repeatable offline examples (no live network news)
uv run python src/demo_ep3.py --samples

# Force simple keyword judge (works without API keys)
uv run python src/demo_ep3.py --backend heuristic

# See every option
uv run python src/demo_ep3.py --help
```

All flags (`--limit`, `--min-floor`, `--backend`, `--samples`, `--dedupe-seen`, `--help`) are documented with “when to use” and example output in **[docs/DEMO_USAGE.md](docs/DEMO_USAGE.md)**.

---

## Reading the table

```text
PUBLISHED | TITLE | TICKER/CO | LABEL | CONF | REASON | BACKEND | MS
```

| Column | Meaning |
|--------|---------|
| **PUBLISHED** | Headline publish time (UTC), or `sample` offline. |
| **TITLE** | News headline (may be shortened). |
| **TICKER/CO** | e.g. `AAPL/Apple`, or `UNKNOWN/-`. |
| **LABEL** | `bullish` / `bearish` / `noise`. |
| **CONF** | How sure the judge is of that label (`0`–`1`). |
| **REASON** | Short explanation (e.g. keywords it matched). |
| **BACKEND** | Which judge ran (see below). |
| **MS** | Judge time in milliseconds. |

Example (offline samples):

```text
sample | Apple unveils new AI features; AAPL share… | AAPL/Apple | bullish | 0.79 | bullish keywords: jump, after-hours… | heuristic_fallback | 0.0
sample | Tesla recalls 40,000 vehicles over softwa… | TSLA/Tesla | bearish | 0.92 | bearish keywords: slide, slides, re… | heuristic_fallback | 0.0
```

---

## Backends (brief)

| Name in output | Plain English |
|----------------|----------------|
| `jev` | Optional decision API (needs keys + base URL). Setup: **[docs/JEV_SETUP.md](docs/JEV_SETUP.md)**. |
| `openai_fallback` / `anthropic_fallback` | Optional LLM JSON classify (needs those API keys). |
| `heuristic_fallback` | Built-in keyword rules — **normal when you have no keys**. |

Order without forcing a backend: Jev → LLM → heuristic. Failures degrade honestly; the demo never invents a successful Jev result.

Optional keys: copy `.env.example` → `.env` (never commit secrets). For Jev you need **both** a key (`JEV_API_KEY` or `TYPESAFE_API_KEY`) **and** `JEV_API_BASE`.

---

## 3-box roadmap

| Box | File | Role | Status |
|-----|------|------|--------|
| 1 | `ingest_rss.py` | RSS pull + seen-id dedupe | Episode 2 |
| 2 | `extract_company.py` | Best-effort ticker / company | Episode 3 |
| 3 | `judge_jev.py` | Bullish / bearish / noise + reason | Episode 3 |

Live demo glue: `src/demo_ep3.py` (fresh latest-N snapshot by default; `--dedupe-seen` is optional).

---

## Limitations (honest)

- Google News RSS is **near-real-time best-effort**, not an exchange firehose — delays and duplicates happen.
- Ticker extract is **best-effort**; many rows will be `UNKNOWN`.
- Labels (especially keyword heuristic) can be **wrong**.
- **Not financial advice.** Educational / engineering demo only.

---

## Next (Episode 4+)

Pipeline glue, optional alerts, latency experiments — still **no auto-trading** in the MVP.
