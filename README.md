# news-signal-mvp

**US stock news → company/ticker → bullish / bearish / noise** (with confidence).

Educational MVP for faster decision-quality experiments. **Not a trading bot. Not financial advice.**

Works on **Windows and Mac** if you have `git` and [uv](https://docs.astral.sh/uv/).

---

## Why this exists

Built from a client brief: take recent US stock headlines, guess the company/ticker when possible, then label each row **bullish**, **bearish**, or **noise** (plus a confidence score and a short reason).

Goal: a small tool you can run locally to experiment with news → signal quality — not auto-trading, not alerts.

---

## How it’s designed

Three boxes glued by one script:

| Box | What it does | File |
|-----|----------------|------|
| 1. Ingest | Pull recent headlines from free Google News RSS | `src/ingest_rss.py` |
| 2. Extract | Best-effort company + ticker (`UNKNOWN` if unclear) | `src/extract_company.py` |
| 3. Judge | Label bullish / bearish / noise + confidence + reason | `src/judge_jev.py` |
| Glue | Runs 1 → 2 → 3 and prints a table | `src/pipeline.py` |

**Judge order (honest):** Jev → LLM (OpenAI/Anthropic) → `heuristic_fallback`.

- With no API keys, you get the built-in **keyword heuristic**. That is normal.
- The demo never fakes a successful Jev result. If keys/base URL are missing or the call fails, it falls through and says so in the `BACKEND` column.

---

## How to run

### 1. Clone

```bash
git clone https://github.com/jihoon-yoo-dev/news-signal-mvp.git
cd news-signal-mvp
```

### 2. Install uv (once)

See [uv install docs](https://docs.astral.sh/uv/getting-started/installation/). Then:

```bash
uv sync
```

Needs Python **3.12+** (uv will manage it).

### 3. Optional API keys

```bash
cp .env.example .env
```

Leave `.env` empty to use the heuristic judge.  
To try real AI backends, fill keys in `.env` (never commit that file):

- **Jev / TypeSafe:** key **and** `JEV_API_BASE` (see [docs/JEV_SETUP.md](docs/JEV_SETUP.md))
- **or** `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` for LLM fallback

### 4. Run the pipeline

```bash
uv run python src/pipeline.py
```

Default: about **20** newest headlines → extract → judge → terminal table.

Useful options:

```bash
# Fewer rows (faster / smaller demos)
uv run python src/pipeline.py --limit 5

# Offline sample headlines (no live RSS)
uv run python src/pipeline.py --samples

# Force keyword judge (no API keys needed)
uv run python src/pipeline.py --backend heuristic

uv run python src/pipeline.py --help
```

### 5. Read the table

```text
PUBLISHED | TITLE | TICKER/CO | LABEL | CONF | REASON | BACKEND | MS
```

| Column | Meaning |
|--------|---------|
| **PUBLISHED** | Headline time (UTC), or `sample` offline |
| **TITLE** | News headline (may be shortened) |
| **TICKER/CO** | e.g. `AAPL/Apple`, or `UNKNOWN/-` |
| **LABEL** | `bullish` / `bearish` / `noise` |
| **CONF** | Confidence `0`–`1` |
| **REASON** | Short explanation |
| **BACKEND** | Which judge ran (`jev`, `openai_fallback`, `anthropic_fallback`, or `heuristic_fallback`) |
| **MS** | Judge time in milliseconds |

Example (offline samples):

```text
sample | Apple unveils new AI features; AAPL share… | AAPL/Apple | bullish | 0.79 | bullish keywords: jump, after-hours… | heuristic_fallback | 0.0
sample | Tesla recalls 40,000 vehicles over softwa… | TSLA/Tesla | bearish | 0.92 | bearish keywords: slide, slides, re… | heuristic_fallback | 0.0
```

More flag detail: [docs/DEMO_USAGE.md](docs/DEMO_USAGE.md).

---

## Current constraints / limitations

- **News source:** free Google News RSS — near-real-time best effort, **not** an exchange firehose. Delays and duplicates happen.
- **Ticker extract:** best-effort; many rows will be `UNKNOWN`.
- **Without API keys:** judge is a **keyword heuristic**, not a real AI call. Labels can be wrong.
- **No Telegram / email alerts** yet.
- **No auto-trading.**
- **Not financial advice.** Educational / engineering demo only.

---

## Build-in-public Shorts (DIY Founder)

How this MVP was built in public:

| Episode | Topic | Link |
|---------|--------|------|
| 1 | Brief / plan | https://www.youtube.com/shorts/mvtQNNoDVy8 |
| 2 | RSS ingest | https://youtube.com/shorts/1QidkyEhb1Y |
| 3 | Extract + judge | https://youtube.com/shorts/2y8BhumiUhE |
| 4 | Full pipeline glue | https://youtube.com/shorts/iZb0yA1QDcg |
