#!/usr/bin/env python3
"""Episode 3 Box 3 — bullish / bearish / noise judge with confidence + latency.

Backend order (honest; never fabricates Jev success):
1. Jev / TypeSafe — if JEV_API_KEY (or TYPESAFE_API_KEY) is set and a client works
2. LLM JSON classify — if OPENAI_API_KEY or ANTHROPIC_API_KEY is set
3. Deterministic keyword heuristic — offline fallback (clearly labeled)

Every path attaches a short ``reason`` (1 brief clause).
Series language uses **noise** (Jev neutral maps to noise).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from dataclasses import asdict, dataclass
from typing import Any, Literal

from dotenv import load_dotenv

Label = Literal["bullish", "bearish", "noise"]

BULLISH_TERMS = (
    "surge",
    "surges",
    "jump",
    "jumps",
    "rally",
    "rallies",
    "soar",
    "soars",
    "record high",
    "beats estimates",
    "beat estimates",
    "raises guidance",
    "upgrade",
    "upgraded",
    "profit",
    "growth",
    "expands",
    "expansion",
    "breakthrough",
    "wins contract",
    "strong demand",
    "after-hours trading",
)

BEARISH_TERMS = (
    "fall",
    "falls",
    "drop",
    "drops",
    "slide",
    "slides",
    "plunge",
    "plunges",
    "misses",
    "miss estimates",
    "cuts guidance",
    "downgrade",
    "downgraded",
    "recall",
    "recalls",
    "lawsuit",
    "probe",
    "scrutiny",
    "layoff",
    "layoffs",
    "bankruptcy",
    "fraud",
    "warning",
    "slowdown",
    "weak demand",
)

NOISE_TERMS = (
    "mixed",
    "awaits",
    "await",
    "unchanged",
    "sideways",
    "commentary",
    "what to know",
    "preview",
    "calendar",
    "jobs data",
    "fed officials",
    "traders await",
)


@dataclass(frozen=True)
class JudgeResult:
    label: Label
    confidence: float
    latency_ms: float
    backend: str
    reason: str
    raw: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _clip_reason(text: str, *, max_len: int = 72) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    if not cleaned:
        return "no rationale"
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 1] + "…"


def _normalize_label(value: str) -> Label:
    v = (value or "").strip().lower()
    if v in {"bullish", "bull", "positive", "positive_news", "호재"}:
        return "bullish"
    if v in {"bearish", "bear", "negative", "negative_news", "악재"}:
        return "bearish"
    return "noise"


def _env_key(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return None


def _matched_terms(text: str, terms: tuple[str, ...]) -> list[str]:
    return [t for t in terms if t in text]


def _heuristic_judge(headline: str, snippet: str | None = None) -> JudgeResult:
    started = time.perf_counter()
    text = f"{headline or ''} {snippet or ''}".lower()
    bull_terms = _matched_terms(text, BULLISH_TERMS)
    bear_terms = _matched_terms(text, BEARISH_TERMS)
    noise_terms = _matched_terms(text, NOISE_TERMS)
    bull = len(bull_terms)
    bear = len(bear_terms)
    noise_hits = len(noise_terms)

    if bull == 0 and bear == 0:
        label: Label = "noise"
        conf = 0.55 if noise_hits else 0.4
        if noise_terms:
            reason = f"noise keywords: {', '.join(noise_terms[:3])}"
        else:
            reason = "no clear polarity keywords"
    elif bull > bear:
        label = "bullish"
        conf = min(0.92, 0.55 + 0.12 * bull - 0.08 * bear)
        reason = f"bullish keywords: {', '.join(bull_terms[:3])}"
    elif bear > bull:
        label = "bearish"
        conf = min(0.92, 0.55 + 0.12 * bear - 0.08 * bull)
        reason = f"bearish keywords: {', '.join(bear_terms[:3])}"
    else:
        label = "noise"
        conf = 0.45
        reason = "mixed bullish/bearish keyword counts"

    if noise_hits and abs(bull - bear) <= 1:
        label = "noise"
        conf = max(conf, 0.5)
        reason = f"broad/wait cues: {', '.join(noise_terms[:3])}"

    latency_ms = (time.perf_counter() - started) * 1000.0
    return JudgeResult(
        label=label,
        confidence=round(conf, 3),
        latency_ms=round(latency_ms, 3),
        backend="heuristic_fallback",
        reason=_clip_reason(reason),
        raw={
            "bull_hits": bull,
            "bear_hits": bear,
            "noise_hits": noise_hits,
            "bull_terms": bull_terms,
            "bear_terms": bear_terms,
            "noise_terms": noise_terms,
        },
    )


def _openai_judge(headline: str, snippet: str | None, api_key: str) -> JudgeResult:
    """Minimal OpenAI Chat Completions JSON classify (optional dependency)."""
    import httpx

    started = time.perf_counter()
    prompt = {
        "headline": headline,
        "snippet": snippet or "",
        "task": (
            "Classify the market implication for a US-listed company if any. "
            "Return ONLY JSON: "
            '{"label":"bullish|bearish|noise","confidence":0.0-1.0,'
            '"reason":"one short clause"}. '
            "Use noise for neutral, unclear, or market-wide with no company edge. "
            "reason must be one brief clause, no trading advice."
        ),
    }
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    payload = {
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": "You are a strict JSON classifier for news signal demos.",
            },
            {"role": "user", "content": json.dumps(prompt)},
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
    content = data["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    label = _normalize_label(str(parsed.get("label", "noise")))
    try:
        conf = float(parsed.get("confidence", 0.5))
    except (TypeError, ValueError):
        conf = 0.5
    conf = max(0.0, min(1.0, conf))
    reason = _clip_reason(str(parsed.get("reason") or f"openai label={label}"))
    latency_ms = (time.perf_counter() - started) * 1000.0
    return JudgeResult(
        label=label,
        confidence=round(conf, 3),
        latency_ms=round(latency_ms, 3),
        backend="openai_fallback",
        reason=reason,
        raw={"model": model},
    )


def _anthropic_judge(headline: str, snippet: str | None, api_key: str) -> JudgeResult:
    import httpx

    started = time.perf_counter()
    model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest").strip()
    user = (
        "Classify this headline for a US stock news demo. "
        'Return ONLY JSON: {"label":"bullish|bearish|noise","confidence":0.0-1.0,'
        '"reason":"one short clause"}. '
        "noise = neutral/unclear/market-wide. No trading advice.\n"
        f"headline: {headline}\n"
        f"snippet: {snippet or ''}"
    )
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": 160,
        "temperature": 0,
        "messages": [{"role": "user", "content": user}],
    }
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
    parts = data.get("content") or []
    text = ""
    for part in parts:
        if isinstance(part, dict) and part.get("type") == "text":
            text += part.get("text") or ""
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError("Anthropic response missing JSON object")
    parsed = json.loads(match.group(0))
    label = _normalize_label(str(parsed.get("label", "noise")))
    try:
        conf = float(parsed.get("confidence", 0.5))
    except (TypeError, ValueError):
        conf = 0.5
    conf = max(0.0, min(1.0, conf))
    reason = _clip_reason(str(parsed.get("reason") or f"anthropic label={label}"))
    latency_ms = (time.perf_counter() - started) * 1000.0
    return JudgeResult(
        label=label,
        confidence=round(conf, 3),
        latency_ms=round(latency_ms, 3),
        backend="anthropic_fallback",
        reason=reason,
        raw={"model": model},
    )


def _jev_judge(headline: str, snippet: str | None, api_key: str) -> JudgeResult:
    """Attempt a Jev/TypeSafe-style call if an SDK or HTTP endpoint is configured.

    This deliberately fails closed into the caller when the product API is
    unavailable — we never invent a successful Jev response.
    """
    started = time.perf_counter()
    base = os.getenv("JEV_API_BASE", "").strip()
    try:
        import ai  # type: ignore  # noqa: F401

        raise RuntimeError(
            "Jev/TypeSafe Python SDK detected but wired client not configured "
            "for this MVP yet — set JEV_API_BASE for HTTP or use LLM/heuristic."
        )
    except ImportError:
        pass

    if not base:
        raise RuntimeError(
            "JEV_API_KEY set but JEV_API_BASE missing; refusing to invent Jev results"
        )

    import httpx

    payload = {
        "state": {"headline": headline, "snippet": snippet or ""},
        "question": {
            "type": "choice",
            "options": ["bullish", "bearish", "neutral"],
        },
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=30.0) as client:
        response = client.post(base.rstrip("/") + "/judge", headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    choice = (
        data.get("choice")
        or data.get("label")
        or (data.get("answer") or {}).get("choice")
        or "neutral"
    )
    try:
        conf = float(
            data.get("confidence")
            or data.get("probability")
            or (data.get("answer") or {}).get("confidence")
            or 0.5
        )
    except (TypeError, ValueError):
        conf = 0.5
    label = _normalize_label(str(choice))
    rationale = (
        data.get("reason")
        or data.get("rationale")
        or (data.get("answer") or {}).get("reason")
        or f"jev choice={choice}"
    )
    latency_ms = (time.perf_counter() - started) * 1000.0
    return JudgeResult(
        label=label,
        confidence=round(max(0.0, min(1.0, conf)), 3),
        latency_ms=round(latency_ms, 3),
        backend="jev",
        reason=_clip_reason(str(rationale)),
        raw={"endpoint": "judge"},
    )


def judge(
    headline: str,
    snippet: str | None = None,
    *,
    force_backend: str | None = None,
) -> JudgeResult:
    """Judge one headline. Prefer Jev → LLM → heuristic unless forced."""
    load_dotenv()
    force = (force_backend or os.getenv("JUDGE_BACKEND") or "").strip().lower()

    if force in {"heuristic", "fallback", "heuristic_fallback"}:
        return _heuristic_judge(headline, snippet)

    jev_key = _env_key("JEV_API_KEY", "TYPESAFE_API_KEY")
    openai_key = _env_key("OPENAI_API_KEY")
    anthropic_key = _env_key("ANTHROPIC_API_KEY")

    errors: list[str] = []

    if force in {"jev", "typesafe"} or (not force and jev_key):
        if not jev_key:
            errors.append("Jev forced but no API key")
        else:
            try:
                return _jev_judge(headline, snippet, jev_key)
            except Exception as exc:  # noqa: BLE001 — demo path must degrade
                errors.append(f"jev: {exc}")

    if force in {"openai", "llm"} or (not force and openai_key and force != "anthropic"):
        if openai_key and force != "anthropic":
            try:
                return _openai_judge(headline, snippet, openai_key)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"openai: {exc}")

    if force == "anthropic" or (not force and anthropic_key):
        if anthropic_key:
            try:
                return _anthropic_judge(headline, snippet, anthropic_key)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"anthropic: {exc}")

    result = _heuristic_judge(headline, snippet)
    if errors:
        raw = dict(result.raw or {})
        raw["degraded_from"] = errors
        return JudgeResult(
            label=result.label,
            confidence=result.confidence,
            latency_ms=result.latency_ms,
            backend=result.backend,
            reason=result.reason,
            raw=raw,
        )
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Episode 3 Box 3: judge bullish/bearish/noise with confidence."
    )
    parser.add_argument("headline", nargs="?", help="Headline to classify.")
    parser.add_argument("--snippet", default=None, help="Optional snippet.")
    parser.add_argument(
        "--backend",
        default=None,
        help="Force backend: jev | openai | anthropic | heuristic",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.headline:
        print(
            "Usage: uv run python src/judge_jev.py "
            "'NVIDIA data-center demand surges'"
        )
        return 2
    result = judge(args.headline, args.snippet, force_backend=args.backend)
    print(
        f"label={result.label} confidence={result.confidence:.3f} "
        f"latency_ms={result.latency_ms:.1f} backend={result.backend} "
        f"reason={result.reason}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
