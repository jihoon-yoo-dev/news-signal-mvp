# How to connect Jev (TypeSafe) to this demo

Plain-English setup for people who are not deep into APIs.  
Follow the steps in order. You can still use the demo **without** Jev (keyword heuristic).

> **Not financial advice.** Jev only helps label news for an educational MVP.

---

## 1. What is Jev? (30 seconds)

**Jev** (from TypeSafe / System One) is a **decision-only** model.  
You send a short situation + a multiple-choice question. It returns a **choice** and a **confidence** score. It is **not** a chatbot that writes long answers.

In this project we ask: *bullish / bearish / neutral* for a headline.  
The demo maps **neutral → noise** so the table matches the YouTube series language.

**Access note (honest):** Jev may require **TypeSafe early access / an API key from their dashboard**. Public docs can be thin or change. If you do not have access yet, skip Jev — the demo already works with `heuristic_fallback`.

---

## 2. What this repo actually does with Jev

Code lives in `src/judge_jev.py` → function `_jev_judge`.

When Jev is configured, the MVP sends an **HTTP POST** to:

```text
{JEV_API_BASE}/judge
```

Example: if `JEV_API_BASE=https://api.example.com/v1`, the full URL is  
`https://api.example.com/v1/judge`.

**Request (as coded today):**

- Header: `Authorization: Bearer <your key>`
- Header: `Content-Type: application/json`
- JSON body roughly:

```json
{
  "state": { "headline": "...", "snippet": "..." },
  "question": {
    "type": "choice",
    "options": ["bullish", "bearish", "neutral"]
  }
}
```

**Success response fields the code looks for** (flexible names):

- Choice: `choice` or `label` or `answer.choice`
- Confidence: `confidence` or `probability` or `answer.confidence`
- Reason (optional): `reason` or `rationale` or `answer.reason`

On success the table / CLI shows **`backend=jev`**.

### Important MVP honesty

- This is a **best-effort HTTP shape** for the portfolio demo — not a guarantee of TypeSafe’s final public API.
- Confirm the real **base URL** (and whether the path is really `/judge`) from **TypeSafe docs or your dashboard**.
- If their real path differs (e.g. `/v1/decide` instead of `/judge`), you may need a **small code tweak** in `_jev_judge` once you have official docs. Do not invent URLs.
- The optional Python package name `ai` is **not fully wired**. If that package is installed, the current code deliberately errors and falls back unless you rely on the HTTP path above. Prefer HTTP + env vars for this MVP.

---

## 3. What you need before wiring

1. A TypeSafe / Jev account with **API access** (early access if required).
2. An **API key** from their dashboard.
3. The **API base URL** they give you (host + version prefix — **without** guessing).
4. This repo cloned locally, with `uv` working (`uv sync` already run).

No Jev package is required in `pyproject.toml` today — the call uses **`httpx`** (already installed).

---

## 4. Env vars (exact names)

| Variable | Required for Jev? | Meaning |
|----------|-------------------|---------|
| `JEV_API_KEY` | One of the two keys | Your Jev / TypeSafe secret key |
| `TYPESAFE_API_KEY` | One of the two keys | Alternate name; same role as `JEV_API_KEY` (first non-empty wins: JEV then TYPESAFE) |
| `JEV_API_BASE` | **Yes, with a key** | Base URL only (no trailing `/judge`). Code appends `/judge`. |
| `JUDGE_BACKEND` | Optional | Force backend: `jev` \| `openai` \| `anthropic` \| `heuristic` |

**Rule:** A key **without** `JEV_API_BASE` will **not** invent results — Jev fails closed and the chain falls back.

Optional later (not Jev): `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` for LLM fallback.

---

## 5. Step-by-step: put secrets in `.env`

### Step A — Copy the example file

From the repo root:

```bash
cd /Users/jihoonyoo/projects/news-signal-mvp
cp .env.example .env
```

`.env` is gitignored. **Never commit it. Never paste keys into GitHub Issues or chat logs.**

### Step B — Edit `.env` (fill real values)

Open `.env` in any editor. Uncomment and set:

```bash
JEV_API_KEY=paste_your_real_key_here
JEV_API_BASE=https://YOUR-REAL-BASE-FROM-TYPESAFE
```

Notes:

- Use **either** `JEV_API_KEY` **or** `TYPESAFE_API_KEY` (you do not need both).
- `JEV_API_BASE` should look like a base, e.g. `https://…/v1` — **not** `…/v1/judge` (the code adds `/judge`).
- Optional for testing: `JUDGE_BACKEND=jev` so every run prefers Jev without typing `--backend jev`.

### Step C — Save and stay local

Confirm `.env` is not staged:

```bash
git status
```

You should **not** see `.env` listed as a new file to commit. If you do, stop and check `.gitignore`.

---

## 6. How to verify it worked

### Test 1 — Single headline (clearest)

```bash
cd /Users/jihoonyoo/projects/news-signal-mvp
uv run python src/judge_jev.py 'NVIDIA data-center demand surges' --backend jev
```

**Success looks like:**

```text
label=bullish confidence=0.8xx latency_ms=… backend=jev reason=…
```

The important part: **`backend=jev`**.

**Failure / fallback looks like:**

```text
label=… confidence=… latency_ms=… backend=heuristic_fallback reason=…
```

(or `openai_fallback` / `anthropic_fallback` if those keys exist).  
That means Jev did not complete successfully; the demo degraded honestly.

### Test 2 — Full table demo forced to Jev

```bash
uv run python src/demo_ep3.py --limit 3 --backend jev
```

**Success:** every data row’s `BACKEND` column says `jev`, and the footer looks like:

```text
# done: rows=3 judge_backend=jev
```

**Fallback:** `BACKEND` shows `heuristic_fallback` (or an LLM fallback) even though you asked for `jev`.

### Test 3 — Automatic preference (no force)

If keys + base are set and you run without `--backend`:

```bash
uv run python src/demo_ep3.py --limit 3
```

Jev is tried **first**. Footer / column should show `jev` when the HTTP call succeeds.

---

## 7. Troubleshooting

| Symptom | Likely cause | What to do |
|---------|--------------|------------|
| Key set but still `heuristic_fallback` | Missing `JEV_API_BASE` | Add base URL; key alone is not enough |
| Forced `--backend jev` but not `jev` | 401 / wrong key / wrong base | Check dashboard key; confirm base from TypeSafe docs |
| Timeout / network error | Endpoint unreachable | Check VPN/firewall; confirm URL; retry |
| 404 on `/judge` | Real path differs from MVP assumption | Confirm path in TypeSafe docs; small code tweak may be needed |
| `ai` package installed, odd errors | SDK stub not wired | Prefer HTTP env vars; or uninstall unused `ai` for this MVP |
| Works with heuristic, not Jev | Expected without access | Keep using demo; wire Jev when you have real credentials |

Fallback order when Jev fails: **OpenAI → Anthropic → heuristic** (if those keys exist).

---

## 8. Security checklist

- [ ] Secrets only in local `.env`
- [ ] Never commit `.env`
- [ ] Never put real keys in README screenshots
- [ ] Rotate the key in the TypeSafe dashboard if it leaks

---

## 9. Related docs

- [DEMO_USAGE.md](DEMO_USAGE.md) — how to run the live demo and read the table  
- [README.md](../README.md) — project overview + quick start  
- Code: `src/judge_jev.py` (`judge`, `_jev_judge`)
