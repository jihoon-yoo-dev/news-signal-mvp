#!/usr/bin/env python3
"""Episode 3 Box 2 — best-effort US company / ticker extraction from a headline.

Rules-first (no paid NLP). Looks for $TICKER, (TICKER), known company names,
and bare known tickers. Returns company + ticker + confidence.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import asdict, dataclass
from typing import Iterable

# Small curated map for the MVP demo — not a full universe.
# Keys are lowercase aliases that may appear in headlines.
COMPANY_ALIASES: dict[str, tuple[str, str]] = {
    "apple": ("Apple", "AAPL"),
    "aapl": ("Apple", "AAPL"),
    "nvidia": ("NVIDIA", "NVDA"),
    "nvda": ("NVIDIA", "NVDA"),
    "tesla": ("Tesla", "TSLA"),
    "tsla": ("Tesla", "TSLA"),
    "microsoft": ("Microsoft", "MSFT"),
    "msft": ("Microsoft", "MSFT"),
    "amazon": ("Amazon", "AMZN"),
    "amzn": ("Amazon", "AMZN"),
    "alphabet": ("Alphabet", "GOOGL"),
    "google": ("Alphabet", "GOOGL"),
    "googl": ("Alphabet", "GOOGL"),
    "goog": ("Alphabet", "GOOG"),
    "meta": ("Meta", "META"),
    "facebook": ("Meta", "META"),
    "netflix": ("Netflix", "NFLX"),
    "nflx": ("Netflix", "NFLX"),
    "boeing": ("Boeing", "BA"),
    "intel": ("Intel", "INTC"),
    "intc": ("Intel", "INTC"),
    "amd": ("AMD", "AMD"),
    "advanced micro devices": ("AMD", "AMD"),
    "disney": ("Disney", "DIS"),
    "costco": ("Costco", "COST"),
    "walmart": ("Walmart", "WMT"),
    "wmt": ("Walmart", "WMT"),
    "jpmorgan": ("JPMorgan", "JPM"),
    "jp morgan": ("JPMorgan", "JPM"),
    "jpm": ("JPMorgan", "JPM"),
    "goldman sachs": ("Goldman Sachs", "GS"),
    "coca-cola": ("Coca-Cola", "KO"),
    "coca cola": ("Coca-Cola", "KO"),
    "starbucks": ("Starbucks", "SBUX"),
    "sbux": ("Starbucks", "SBUX"),
    "uber": ("Uber", "UBER"),
    "airbnb": ("Airbnb", "ABNB"),
    "abnb": ("Airbnb", "ABNB"),
    "palantir": ("Palantir", "PLTR"),
    "pltr": ("Palantir", "PLTR"),
    "broadcom": ("Broadcom", "AVGO"),
    "avgo": ("Broadcom", "AVGO"),
}

KNOWN_TICKERS: set[str] = {ticker for _, ticker in COMPANY_ALIASES.values()}

# Common false-positive uppercase tokens in news titles.
TICKER_STOPWORDS: set[str] = {
    "US",
    "USA",
    "CEO",
    "CFO",
    "IPO",
    "ETF",
    "AI",
    "GDP",
    "FED",
    "SEC",
    "FDA",
    "FAA",
    "EU",
    "UK",
    "NYSE",
    "DOW",
    "S&P",
    "SPX",
    "Q1",
    "Q2",
    "Q3",
    "Q4",
    "YOY",
    "MOM",
    "USD",
    "CNN",
    "CNBC",
    "WSJ",
    "BBC",
    "API",
    "GPU",
}

DOLLAR_TICKER_RE = re.compile(r"\$([A-Z]{1,5})\b")
PAREN_TICKER_RE = re.compile(r"\(([A-Z]{1,5})\)")
BARE_TICKER_RE = re.compile(r"\b([A-Z]{1,5})\b")


@dataclass(frozen=True)
class ExtractResult:
    company: str | None
    ticker: str | None
    confidence: float
    method: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _alias_hits(text: str) -> list[tuple[str, str, str, int]]:
    """Return (alias, company, ticker, start_index) sorted by alias length desc."""
    lower = text.lower()
    hits: list[tuple[str, str, str, int]] = []
    for alias, (company, ticker) in COMPANY_ALIASES.items():
        # Prefer word-ish boundaries for multi-word and short aliases.
        pattern = re.compile(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])")
        match = pattern.search(lower)
        if match:
            hits.append((alias, company, ticker, match.start()))
    hits.sort(key=lambda row: (-len(row[0]), row[3]))
    return hits


def extract_company(headline: str, snippet: str | None = None) -> ExtractResult:
    """Best-effort extract. Prefer explicit tickers, then known company names."""
    text = (headline or "").strip()
    if snippet:
        text = f"{text} {snippet.strip()}"
    if not text:
        return ExtractResult(None, None, 0.0, "empty")

    # 1) $TICKER — strongest explicit signal
    for match in DOLLAR_TICKER_RE.finditer(text):
        ticker = match.group(1).upper()
        if ticker in TICKER_STOPWORDS:
            continue
        company = _company_for_ticker(ticker)
        conf = 0.95 if company else 0.8
        return ExtractResult(company, ticker, conf, "dollar_ticker")

    # 2) (TICKER) parenthetical
    for match in PAREN_TICKER_RE.finditer(text):
        ticker = match.group(1).upper()
        if ticker in TICKER_STOPWORDS:
            continue
        company = _company_for_ticker(ticker)
        if company or ticker in KNOWN_TICKERS:
            return ExtractResult(company, ticker, 0.9, "paren_ticker")

    # 3) Known company / alias names
    hits = _alias_hits(text)
    if hits:
        _alias, company, ticker, _idx = hits[0]
        # Longer aliases (full company names) are more confident than short ticker words.
        conf = 0.88 if len(_alias) >= 4 else 0.75
        return ExtractResult(company, ticker, conf, "company_alias")

    # 4) Bare known ticker tokens (avoid stopwords)
    for match in BARE_TICKER_RE.finditer(text):
        ticker = match.group(1).upper()
        if ticker in TICKER_STOPWORDS or ticker not in KNOWN_TICKERS:
            continue
        company = _company_for_ticker(ticker)
        return ExtractResult(company, ticker, 0.7, "bare_ticker")

    return ExtractResult(None, None, 0.15, "none")


def _company_for_ticker(ticker: str) -> str | None:
    for company, known in COMPANY_ALIASES.values():
        if known == ticker:
            return company
    return None


def extract_many(headlines: Iterable[tuple[str, str | None]]) -> list[ExtractResult]:
    return [extract_company(title, snippet) for title, snippet in headlines]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Episode 3 Box 2: extract US company/ticker from a headline."
    )
    parser.add_argument("headline", nargs="?", help="Headline text to extract from.")
    parser.add_argument("--snippet", default=None, help="Optional snippet/description.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.headline:
        print("Usage: uv run python src/extract_company.py 'Apple shares jump'")
        return 2
    result = extract_company(args.headline, args.snippet)
    print(
        f"company={result.company!s} ticker={result.ticker!s} "
        f"confidence={result.confidence:.2f} method={result.method}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
