"""
fetch.py -- pulls current values for a small, editable list of financial
indicators from Finnhub (https://finnhub.io) and writes them out in two
formats:

  report.txt  - a plain-English report, ready to display as-is on your
                Windows and Android widgets. No parsing needed on their end.
  data.json   - the same data in a structured format, in case you want to
                do something fancier later.

WHY FINNHUB INSTEAD OF YAHOO FINANCE
-------------------------------------
The first version of this script pulled data from Yahoo Finance (via the
"yfinance" package), which needs no account at all. In practice, Yahoo
increasingly blocks or silently starves requests coming from shared cloud
servers -- like GitHub Actions runners -- even though the exact same code
often works fine from a home connection. That's why every ticker was
coming back "(unavailable)". Finnhub is an official, documented API: less
convenient (it needs a free API key) but far more reliable for exactly
this kind of scheduled, automated use.

GETTING AN API KEY (free, no credit card)
-------------------------------------------
1. Sign up at https://finnhub.io/register
2. Copy your API key from the dashboard (Settings, or it's shown right
   after signup).
3. In your GitHub repo: Settings -> Secrets and variables -> Actions ->
   New repository secret. Name it exactly FINNHUB_API_KEY and paste your
   key as the value.
The workflow passes that secret in as an environment variable -- your key
is never written into this file or visible anywhere in the repo itself.

HOW TO CUSTOMIZE WHAT'S TRACKED
--------------------------------
Edit the TICKERS list below. Each entry needs:
  - "symbol": the stock market ticker
  - "label":  the friendly name you want shown in the report

Finnhub's free tier covers individual stocks and ETFs, but not raw market
indices -- that's why the three "index" rows below actually track an ETF
that closely follows that index instead. This is a completely standard
substitution: SPY tracks the S&P 500, QQQ tracks the Nasdaq 100, and DIA
tracks the Dow Jones, each closely enough for a glance-at-it dashboard.
Any regular stock ticker works directly, e.g. "NVDA", "TSLA", "GOOGL".
"""

import json
import os
from datetime import datetime, timezone

import requests

TICKERS = [
    {"symbol": "SPY", "label": "S&P 500 (SPY)"},
    {"symbol": "QQQ", "label": "Nasdaq 100 (QQQ)"},
    {"symbol": "DIA", "label": "Dow Jones (DIA)"},
    {"symbol": "AAPL", "label": "Apple"},
    {"symbol": "MSFT", "label": "Microsoft"},
]

API_KEY = os.environ.get("FINNHUB_API_KEY")


def fetch_one(symbol: str) -> dict:
    """Get the latest price and % change for a single ticker from Finnhub."""
    if not API_KEY:
        raise RuntimeError(
            "FINNHUB_API_KEY is not set. Add it as a GitHub repository "
            "secret -- see the instructions in the comment at the top of "
            "this file."
        )

    response = requests.get(
        "https://finnhub.io/api/v1/quote",
        params={"symbol": symbol, "token": API_KEY},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()

    price = data.get("c")  # current price
    prev_close = data.get("pc")  # previous close

    # Finnhub responds with all-zero fields (not an error) for a symbol it
    # doesn't recognize, so treat that the same as "no data available".
    if not price or not prev_close:
        raise ValueError("no price returned -- double check the symbol is correct")

    change_pct = (price - prev_close) / prev_close * 100
    return {"price": price, "change_pct": change_pct}


def format_number(value: float) -> str:
    """4,231.07 style formatting for prices."""
    return f"{value:,.2f}"


def format_change(value: float) -> str:
    """+0.42% / -0.15% style formatting for the daily change."""
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}%"


def main():
    results = []

    for item in TICKERS:
        try:
            data = fetch_one(item["symbol"])
            results.append({**item, **data, "ok": True})
        except Exception as exc:
            # Don't let one bad/renamed ticker (or a transient hiccup) kill
            # the whole run -- record the problem and keep going so the
            # rest of the report still updates normally.
            results.append({**item, "ok": False, "error": str(exc)})

    updated_at = datetime.now(timezone.utc)

    # --- data.json: structured, for later use -----------------------------
    with open("data.json", "w") as f:
        json.dump(
            {
                "updated_at": updated_at.isoformat(),
                "indicators": results,
            },
            f,
            indent=2,
        )

    # --- report.txt: plain text, ready to show on a widget as-is ----------
    lines = ["Market Update"]
    label_width = max(len(item["label"]) for item in TICKERS) + 2

    for r in results:
        if r["ok"]:
            price_str = format_number(r["price"])
            change_str = format_change(r["change_pct"])
            lines.append(f"{r['label']:<{label_width}}{price_str:>12}  {change_str:>8}")
        else:
            lines.append(f"{r['label']:<{label_width}}(unavailable)")

    lines.append("")
    lines.append(f"Updated: {updated_at.strftime('%Y-%m-%d %H:%M UTC')}")

    report = "\n".join(lines)

    with open("report.txt", "w") as f:
        f.write(report)

    print(report)


if __name__ == "__main__":
    main()
