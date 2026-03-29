"""
SP500 Top10 Portfolio Tracker - Data Fetcher
Runs monthly via GitHub Actions.
Fetches market cap rankings, updates exit counters, generates buy/sell signals.
"""

import json
import os
import datetime
from pathlib import Path

try:
    import yfinance as yf
except ImportError:
    yf = None

# ── Strategy Configuration ────────────────────────────────────────────────────
STRATEGY = {
    "exit_months_threshold": 3,     # months outside Top10 before sell trigger
    "sell_pct_per_quarter": 0.33,   # sell 33% of holdings per quarter
    "weight_tier1": 1.5,            # ranks 1-3
    "weight_tier2": 1.0,            # ranks 4-7
    "weight_tier3": 0.7,            # ranks 8-10
}

# Canonical Top10 candidates pool (expanded so ranking fluctuations are tracked)
CANDIDATES = [
    {"ticker": "NVDA",  "name": "NVIDIA"},
    {"ticker": "AAPL",  "name": "Apple"},
    {"ticker": "GOOG",  "name": "Alphabet"},
    {"ticker": "MSFT",  "name": "Microsoft"},
    {"ticker": "AMZN",  "name": "Amazon"},
    {"ticker": "AVGO",  "name": "Broadcom"},
    {"ticker": "TSLA",  "name": "Tesla"},
    {"ticker": "META",  "name": "Meta Platforms"},
    {"ticker": "BRK-B", "name": "Berkshire Hathaway"},
    {"ticker": "WMT",   "name": "Walmart"},
    {"ticker": "LLY",   "name": "Eli Lilly"},
    {"ticker": "JPM",   "name": "JPMorgan Chase"},
    {"ticker": "XOM",   "name": "Exxon Mobil"},
    {"ticker": "V",     "name": "Visa"},
    {"ticker": "ORCL",  "name": "Oracle"},
]

DATA_PATH = Path(__file__).parent.parent / "data"


def load_state() -> dict:
    state_file = DATA_PATH / "state.json"
    if state_file.exists():
        with open(state_file) as f:
            return json.load(f)
    return {
        "exit_counters": {},      # ticker -> consecutive months outside Top10
        "sell_progress": {},      # ticker -> quarters sold so far
        "history": [],            # list of monthly snapshots
        "portfolio": {},          # ticker -> {shares, avg_cost, tier}
        "last_updated": None,
        "monthly_budget_krw": 1000000,
    }


def save_state(state: dict):
    DATA_PATH.mkdir(exist_ok=True)
    with open(DATA_PATH / "state.json", "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, default=str)


def fetch_market_caps() -> list[dict]:
    """Fetch market caps from Yahoo Finance and return ranked list."""
    results = []
    if yf is None:
        print("yfinance not available, using mock data")
        return mock_market_caps()

    for item in CANDIDATES:
        try:
            ticker = yf.Ticker(item["ticker"])
            info = ticker.info
            market_cap = info.get("marketCap", 0)
            price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
            change_pct = info.get("regularMarketChangePercent", 0)
            results.append({
                "ticker": item["ticker"],
                "name": item["name"],
                "market_cap": market_cap,
                "price": price,
                "change_pct": round(change_pct, 2),
            })
            print(f"  {item['ticker']}: ${market_cap/1e12:.2f}T")
        except Exception as e:
            print(f"  Warning: Could not fetch {item['ticker']}: {e}")
            results.append({
                "ticker": item["ticker"],
                "name": item["name"],
                "market_cap": 0,
                "price": 0,
                "change_pct": 0,
            })

    results.sort(key=lambda x: x["market_cap"], reverse=True)
    for i, item in enumerate(results):
        item["rank"] = i + 1
    return results


def mock_market_caps() -> list[dict]:
    """Fallback mock data when API unavailable (for CI testing)."""
    mock = [
        {"ticker": "NVDA",  "name": "NVIDIA",            "market_cap": 4_180_000_000_000, "price": 171.88, "change_pct": -1.33},
        {"ticker": "AAPL",  "name": "Apple",             "market_cap": 4_050_000_000_000, "price": 275.91, "change_pct": -0.21},
        {"ticker": "GOOG",  "name": "Alphabet",          "market_cap": 3_990_000_000_000, "price": 331.33, "change_pct": -0.60},
        {"ticker": "MSFT",  "name": "Microsoft",         "market_cap": 2_920_000_000_000, "price": 393.67, "change_pct": -4.95},
        {"ticker": "AMZN",  "name": "Amazon",            "market_cap": 2_140_000_000_000, "price": 203.26, "change_pct": -1.84},
        {"ticker": "AVGO",  "name": "Broadcom",          "market_cap": 1_420_000_000_000, "price": 180.51, "change_pct": -1.04},
        {"ticker": "TSLA",  "name": "Tesla",             "market_cap": 1_360_000_000_000, "price": 282.73, "change_pct":  4.96},
        {"ticker": "META",  "name": "Meta Platforms",    "market_cap": 1_330_000_000_000, "price": 559.14, "change_pct": -2.22},
        {"ticker": "BRK-B", "name": "Berkshire Hathaway","market_cap": 1_011_000_000_000, "price": 462.14, "change_pct": -0.81},
        {"ticker": "WMT",   "name": "Walmart",           "market_cap":   979_730_000_000, "price":  93.25, "change_pct":  0.54},
        {"ticker": "LLY",   "name": "Eli Lilly",         "market_cap":   784_580_000_000, "price": 882.10, "change_pct": -0.30},
        {"ticker": "JPM",   "name": "JPMorgan Chase",    "market_cap":   762_830_000_000, "price": 263.40, "change_pct":  0.12},
        {"ticker": "XOM",   "name": "Exxon Mobil",       "market_cap":   712_470_000_000, "price": 116.80, "change_pct": -0.45},
        {"ticker": "V",     "name": "Visa",              "market_cap":   568_350_000_000, "price": 344.20, "change_pct":  0.22},
        {"ticker": "ORCL",  "name": "Oracle",            "market_cap":   401_670_000_000, "price": 175.90, "change_pct":  1.10},
    ]
    for i, item in enumerate(mock):
        item["rank"] = i + 1
    return mock


def compute_weights(top10: list[dict], monthly_budget_krw: int) -> list[dict]:
    """Compute per-stock budget allocation using tiered weighting."""
    s = STRATEGY
    total_w = 3 * s["weight_tier1"] + 4 * s["weight_tier2"] + 3 * s["weight_tier3"]
    unit = monthly_budget_krw / total_w

    for stock in top10:
        r = stock["rank"]
        if r <= 3:
            w = s["weight_tier1"]
            tier = 1
        elif r <= 7:
            w = s["weight_tier2"]
            tier = 2
        else:
            w = s["weight_tier3"]
            tier = 3
        stock["tier"] = tier
        stock["weight_factor"] = w
        stock["alloc_krw"] = round(unit * w)
        stock["alloc_pct"] = round(w / total_w * 100, 1)
    return top10


def update_exit_counters(state: dict, ranked: list[dict]) -> dict:
    """Update exit counters and determine actions for this month."""
    top10_tickers = {s["ticker"] for s in ranked if s["rank"] <= 10}
    all_tickers = {s["ticker"] for s in ranked}

    # Tickers we currently hold or are tracking
    tracked = set(state["exit_counters"].keys()) | set(state["portfolio"].keys())

    signals = []

    # Update counters for all tracked tickers
    for ticker in tracked | top10_tickers:
        in_top10 = ticker in top10_tickers
        if in_top10:
            # Reset counter on re-entry
            if state["exit_counters"].get(ticker, 0) > 0:
                signals.append({
                    "ticker": ticker,
                    "action": "REENTRY",
                    "message": f"{ticker} 복귀! 매도 중단 → 다음 달부터 정상 매수 재개",
                    "urgency": "high",
                })
            state["exit_counters"][ticker] = 0
            # Remove from sell progress if re-entered
            state["sell_progress"].pop(ticker, None)
        else:
            # Increment exit counter only for tickers we hold
            if ticker in state["portfolio"] or ticker in state["exit_counters"]:
                prev = state["exit_counters"].get(ticker, 0)
                state["exit_counters"][ticker] = prev + 1
                count = state["exit_counters"][ticker]

                if count == 1:
                    signals.append({
                        "ticker": ticker,
                        "action": "WATCH",
                        "message": f"{ticker} 이탈 1개월째. 아직 매도 없음. 모니터링 중.",
                        "urgency": "low",
                    })
                elif count == 2:
                    signals.append({
                        "ticker": ticker,
                        "action": "WATCH",
                        "message": f"{ticker} 이탈 2개월째. 다음 달도 이탈 시 매도 시작.",
                        "urgency": "medium",
                    })
                elif count >= 3:
                    # Check if this is a quarterly sell month (every 3 months)
                    quarters_sold = state["sell_progress"].get(ticker, 0)
                    state["sell_progress"][ticker] = quarters_sold + 1
                    signals.append({
                        "ticker": ticker,
                        "action": "SELL_33",
                        "message": f"{ticker} 이탈 {count}개월째. 보유 잔량의 33% 매도 실행하세요.",
                        "urgency": "critical",
                        "sell_pct": 33,
                        "quarters_sold": quarters_sold + 1,
                    })

    # New Top10 entries not in portfolio
    for stock in ranked:
        if stock["rank"] <= 10 and stock["ticker"] not in state["portfolio"]:
            if stock["ticker"] not in state.get("new_entries_pending", {}):
                signals.append({
                    "ticker": stock["ticker"],
                    "action": "NEW_BUY",
                    "message": f"{stock['ticker']} 신규 Top10 편입! 이번 달부터 정상 비중으로 매수 시작.",
                    "urgency": "high",
                })

    return state, signals


def is_quarter_end() -> bool:
    """True if current month is a quarter-end (Mar, Jun, Sep, Dec)."""
    return datetime.date.today().month in [3, 6, 9, 12]


def generate_monthly_snapshot(ranked: list[dict], state: dict, signals: list) -> dict:
    now = datetime.datetime.now(datetime.timezone.utc)
    top10 = [s for s in ranked if s["rank"] <= 10]
    return {
        "date": now.isoformat(),
        "month": now.strftime("%Y-%m"),
        "top10": top10,
        "all_ranked": ranked,
        "signals": signals,
        "exit_counters": dict(state["exit_counters"]),
        "sell_progress": dict(state["sell_progress"]),
        "is_quarter_end": is_quarter_end(),
        "monthly_budget_krw": state["monthly_budget_krw"],
        "strategy": STRATEGY,
    }


def main():
    print("=== SP500 Top10 Portfolio Tracker ===")
    print(f"Run time: {datetime.datetime.now(datetime.timezone.utc).isoformat()}")

    state = load_state()
    print("\n[1/4] Fetching market caps...")
    ranked = fetch_market_caps()

    print("\n[2/4] Computing tiered weights...")
    top10 = [s for s in ranked if s["rank"] <= 10]
    top10 = compute_weights(top10, state["monthly_budget_krw"])
    # Merge weights back into ranked
    weight_map = {s["ticker"]: s for s in top10}
    for s in ranked:
        if s["ticker"] in weight_map:
            s.update(weight_map[s["ticker"]])

    print("\n[3/4] Updating exit counters & generating signals...")
    state, signals = update_exit_counters(state, ranked)

    print(f"  Signals generated: {len(signals)}")
    for sig in signals:
        print(f"  [{sig['urgency'].upper()}] {sig['message']}")

    print("\n[4/4] Saving snapshot...")
    snapshot = generate_monthly_snapshot(ranked, state, signals)
    state["history"].append(snapshot)
    state["last_updated"] = snapshot["date"]

    # Keep only last 36 months of history
    if len(state["history"]) > 36:
        state["history"] = state["history"][-36:]

    save_state(state)

    # Save latest snapshot separately for easy frontend access
    DATA_PATH.mkdir(exist_ok=True)
    with open(DATA_PATH / "latest.json", "w") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2, default=str)

    print(f"\nDone. Data saved to {DATA_PATH}")
    print(f"Top10: {[s['ticker'] for s in top10]}")


if __name__ == "__main__":
    main()
