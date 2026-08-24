"""
fetch.py -- pulls current values for a small, editable list of financial
indicators and writes them out in two formats:

  report.txt  - a plain-English report, ready to display as-is on your
                Windows and Android widgets. No parsing needed on their end.
  data.json   - the same data in a structured format, in case you want to
                do something fancier later (a real app, a nicer chart, etc).

HOW TO CUSTOMIZE WHAT'S TRACKED
--------------------------------
Just edit the TICKERS list below. Each entry needs:
  - "symbol": the Yahoo Finance ticker for that thing
  - "label":  the friendly name you want shown in the report

A few tips for finding symbols on https://finance.yahoo.com :
  - Market indices use a "^" prefix, e.g. "^GSPC" (S&P 500), "^IXIC"
    (Nasdaq Composite), "^DJI" (Dow Jones), "^VIX" (the volatility index).
  - Regular stocks just use their ticker, e.g. "AAPL" (Apple), "MSFT"
    (Microsoft), "NVDA" (Nvidia).
  - Search any company/index name on Yahoo Finance and the ticker is shown
    right next to the name.

Nothing else in this file needs to change to add or remove an entry --
the report and the widgets both adapt automatically.
"""

import json
from datetime import datetime, timezone

import yfinance as yf

TICKERS = [
    {"symbol": "^GSPC", "label": "S&P 500"},
    {"symbol": "^IXIC", "label": "Nasdaq"},
    {"symbol": "^DJI", "label": "Dow Jones"},
    {"symbol": "AAPL", "label": "Apple"},
    {"symbol": "MSFT", "label": "Microsoft"},
]


def fetch_one(symbol: str) -> dict:
    """Get the latest price and % change for a single ticker."""
    ticker = yf.Ticker(symbol)
    info = ticker.fast_info  # lightweight -- avoids extra network calls
    price = info.get("last_price")
    prev_close = info.get("previous_close")

    change_pct = None
    if price is not None and prev_close:
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
            if data["price"] is None:
                raise ValueError("no price returned")
            results.append({**item, **data, "ok": True})
        except Exception as exc:
            # Don't let one bad/renamed ticker kill the whole run -- record
            # the problem and keep going so the rest of the report still
            # updates normally.
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
