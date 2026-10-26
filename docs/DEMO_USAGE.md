# How to use the Episode 3 live demo

Plain-English guide for `demo_ep3.py`. You do **not** need to be a developer to follow the quick start — copy, paste, run.

> **Not financial advice.** This is an educational software demo. Labels are guesses for learning — never buy/sell instructions.

---

## What is this?

**News Signal MVP** is a small classroom-style program that:

1. Pulls recent **US stock / market headlines** (from free Google News RSS),
2. Tries to find a **company name and ticker** in each headline (best effort),
3. Classifies each headline as **bullish**, **bearish**, or **noise**,
4. Shows a **short reason**, a **confidence** score, and how long the judge took.

Think of it as: *headline → “which company?” → “good news / bad news / unclear?”* — printed as a table in your terminal.

---

## Quick start (copy and paste)

You need [uv](https://docs.astral.sh/uv/) and Python 3.12+.

```bash
git clone https://github.com/jihoon-yoo-dev/news-signal-mvp.git
cd news-signal-mvp
uv sync
uv run python src/demo_ep3.py
```

That default run:

- Fetches a **fresh snapshot** of about **20** newest headlines,
- Extracts ticker/company when it can,
- Judges each row (usually `heuristic_fallback` if you have no API keys),
- Prints a table.

No API keys are required for the default demo.

---

## What the output columns mean

Example header:

```text
PUBLISHED | TITLE | TICKER/CO | LABEL | CONF | REASON | BACKEND | MS
```

| Column | Plain English |
|--------|----------------|
| **PUBLISHED** | When the news item says it was published (UTC). |
| **TITLE** | The headline text (may be shortened to fit the table). |
| **TICKER/CO** | Best-effort `TICKER/Company`. If unknown → `UNKNOWN/-`. |
| **LABEL** | `bullish` (more positive), `bearish` (more negative), or `noise` (unclear / broad market / no clear company edge). |
| **CONF** | Confidence from `0.00`–`1.00`. Higher = the judge is more sure of *that label* — still not advice. |
| **REASON** | One short clause explaining the label (e.g. which keywords). |
| **BACKEND** | Which judge ran: `jev`, `openai_fallback`, `anthropic_fallback`, or `heuristic_fallback`. |
| **MS** | How many milliseconds the judge took for that row. |

### Realistic sample rows

**Offline samples** (stable, good for learning the table):

```text
sample | Apple unveils new AI features; AAPL share… | AAPL/Apple     | bullish | 0.79 | bullish keywords: jump, after-hours… | heuristic_fallback | 0.0
sample | Tesla recalls 40,000 vehicles over softwa… | TSLA/Tesla     | bearish | 0.92 | bearish keywords: slide, slides, re… | heuristic_fallback | 0.0
sample | Fed officials signal patience on rate cut… | UNKNOWN/-      | noise   | 0.55 | broad/wait cues: commentary, fed of… | heuristic_fallback | 0.0
```

**Live RSS** (titles change every run; shape stays the same):

```text
2026-10-26 23:30:16 UTC | US stocks end higher as Anthropic's IPO f… | UNKNOWN/- | noise | 0.40 | no clear polarity keywords; extract:none→UNKNOWN | heuristic_fallback | 0.0
2026-10-26 21:36:18 UTC | Stocks rise as Nvidia gains and AI shares… | NVDA/NVIDIA | noise | 0.40 | no clear polarity keywords | heuristic_fallback | 0.0
```

Lines that start with `#` are status notes (source, disclaimer, row count) — not table data.

---

## Backends (who is “judging”?)

The program tries judges in this order **unless you force one**:

| Backend | What it is | When you see it |
|---------|------------|-----------------|
| **Jev** (`jev`) | A decision-style API (needs keys + endpoint). | Only if `JEV_API_KEY` / `TYPESAFE_API_KEY` and `JEV_API_BASE` are set and working. |
| **LLM** (`openai_fallback` / `anthropic_fallback`) | A small JSON classify call to OpenAI or Anthropic. | If those API keys exist and Jev didn’t win. |
| **Heuristic** (`heuristic_fallback`) | Simple keyword rules in this repo. | **Normal with no API keys.** Also used if cloud judges fail. |

**Having no keys is fine.** For most GitHub readers, `heuristic_fallback` is expected.

Optional: copy `.env.example` → `.env` and fill keys. Never commit `.env`.

---

## Every `demo_ep3.py` option (from `--help`)

Run `uv run python src/demo_ep3.py --help` anytime to see the same list.

### `-h` / `--help`

- **Meaning:** Show the built-in help text and exit.
- **When:** You forgot a flag name.
- **Example:**

```bash
uv run python src/demo_ep3.py --help
```

- **Output:** Usage text in the terminal (no headline table).

---

### *(no flags)* — default live demo

- **Meaning:** Fetch recent US market headlines now, keep about 20 newest, extract + judge.
- **When:** Everyday “show me what’s new” demo.
- **Example:**

```bash
uv run python src/demo_ep3.py
```

- **Output shape:**

```text
# Episode 3 demo — live RSS snapshot feeds=2 scanned_unique=197 returned=20 …
PUBLISHED | TITLE | TICKER/CO | LABEL | CONF | REASON | BACKEND | MS
…
# done: rows=20 judge_backend=heuristic_fallback
```

---

### `--limit LIMIT`

- **Meaning:** After merge/sort, keep at most this many headlines. Default **20**.
- **When:** You want a shorter or longer table (e.g. 5 for a quick look, 20 for a fuller snapshot).
- **Example:**

```bash
uv run python src/demo_ep3.py --limit 5
```

- **Output:** Same columns; `# done: rows=5 …` (or fewer if the feeds returned less).

---

### `--min-floor MIN_FLOOR`

- **Meaning:** If the first RSS queries return fewer than this many unique headlines, the demo **widens** with extra Google News queries, then merges again. Default **10**.
- **When:** You care about “at least roughly this many rows” on a quiet feed day. Usually leave at 10.
- **Example:**

```bash
uv run python src/demo_ep3.py --limit 20 --min-floor 10
```

- **Output:** Same table; status line may show more `feeds=` if widen ran.

---

### `--backend BACKEND`

- **Meaning:** Force which judge to use: `jev` | `openai` | `anthropic` | `heuristic`.
- **When:** Compare backends, or lock to keywords for a predictable demo (`heuristic`).
- **Example:**

```bash
uv run python src/demo_ep3.py --limit 3 --backend heuristic
```

- **Output:** `BACKEND` column shows `heuristic_fallback` (or another backend if keys work and you forced that name).

```text
2026-10-26 23:30:16 UTC | US stocks end higher as Anthropic's IPO f… | UNKNOWN/- | noise | 0.40 | no clear polarity keywords; extract… | heuristic_fallback | 0.0
# done: rows=3 judge_backend=heuristic_fallback
```

If you force `jev` / `openai` / `anthropic` without working credentials, the demo **falls back** honestly (often to heuristic) instead of inventing success.

---

### `--samples` and `--samples PATH`

- **Meaning:** Skip live RSS. Use built-in example headlines (`samples/headlines.json`), or a JSON file you pass.
- **When:** No network, airplane mode, or you want a **repeatable** teaching demo.
- **Examples:**

```bash
uv run python src/demo_ep3.py --samples
uv run python src/demo_ep3.py --samples samples/headlines.json
```

- **Output:**

```text
# Episode 3 demo — samples (…/samples/headlines.json)
sample | Apple unveils new AI features; AAPL share… | AAPL/Apple | bullish | 0.79 | bullish keywords: jump, after-hours… | heuristic_fallback | 0.0
sample | Tesla recalls 40,000 vehicles over softwa… | TSLA/Tesla | bearish | 0.92 | bearish keywords: slide, slides, re… | heuristic_fallback | 0.0
# done: rows=8 judge_backend=heuristic_fallback
```

---

### `--dedupe-seen`

- **Meaning:** After building the latest-N snapshot, drop headlines whose ids were already stored by Box 1’s seen-id file (`.data/seen_ids.json`). **Off by default.**
- **When:** You already run `ingest_rss.py` as a “remember what I saw” watcher and only want rows that look new to that store. For the normal live demo, **leave this off** so every run shows a fresh latest-N snapshot.
- **Example:**

```bash
uv run python src/demo_ep3.py --limit 20 --dedupe-seen
```

- **Output:** Same table; status line may include `dedupe-seen kept=K/N`. Row count can be lower (even zero if everything was already seen).

---

## Related helpers (optional)

These are separate small tools — not required for the main demo.

```bash
# Box 2 only — extract ticker/company from one headline
uv run python src/extract_company.py 'Apple unveils new AI features; AAPL shares jump'

# Box 3 only — judge one headline
uv run python src/judge_jev.py 'NVIDIA data-center demand surges; NVDA hits fresh record high'

# Box 1 — pull headlines with seen-id dedupe (cron-style watcher)
uv run python src/ingest_rss.py
```

---

## Limitations (short and honest)

- **RSS delay:** Google News RSS is near-real-time **best effort**, not a stock-exchange firehose. Headlines can lag or repeat across outlets.
- **Best-effort extract:** Many headlines have no clear ticker → `UNKNOWN`. The alias list is small on purpose for this MVP.
- **Labels can be wrong:** Especially on the keyword heuristic. Confidence is not a guarantee.
- **Not financial advice:** Educational / engineering demo only. No buy/sell recommendations. Do not trade on this output.

---

## Need the short version?

See the Quick start in the root [README.md](../README.md).
