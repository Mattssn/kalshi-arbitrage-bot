"""Minimal web UI for monitoring and controlling the Kalshi bot.

Run with:
    uvicorn src.web_ui:app --reload --host 0.0.0.0 --port 8000
"""
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from main import KalshiArbitrageBot
from src.market_api import KalshiClient


class SettingsPayload(BaseModel):
    min_liquidity: Optional[int] = None
    min_profit_per_day: Optional[float] = None


client = KalshiClient()
bot = KalshiArbitrageBot()
app = FastAPI(title="Kalshi Arbitrage Bot UI", version="0.1.0")


@app.get("/", response_class=HTMLResponse)
def home():
    return """<!doctype html>
<html lang='en'>
<head>
  <meta charset='UTF-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1.0'>
  <title>Kalshi Arbitrage Bot</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; background: #0b1021; color: #e8edf7; }
    h1 { margin-bottom: 0; }
    .card { background: #151b32; padding: 16px; border-radius: 10px; margin-bottom: 16px; box-shadow: 0 0 8px rgba(0,0,0,0.3); }
    button { padding: 8px 14px; border: none; border-radius: 6px; cursor: pointer; background: #3b82f6; color: white; }
    button.secondary { background: #6b7280; }
    input, select { padding: 6px 8px; border-radius: 6px; border: 1px solid #334155; background: #0f172a; color: #e8edf7; }
    pre { white-space: pre-wrap; background: #0f172a; padding: 10px; border-radius: 8px; overflow: auto; }
    .flex { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
    .stat { font-size: 18px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 12px; }
    a { color: #93c5fd; }
  </style>
</head>
<body>
  <h1>Kalshi Arbitrage Bot</h1>
  <p>Monitor connectivity, inspect wallet stats, and run scans from the browser.</p>

  <div class='grid'>
    <div class='card'>
      <h2>API Status</h2>
      <p id='status-text'>Checking...</p>
      <button onclick='refreshStatus()'>Refresh</button>
    </div>

    <div class='card'>
      <h2>Wallet</h2>
      <div id='wallet'>Loading...</div>
      <button onclick='refreshWallet()'>Refresh Wallet</button>
    </div>

    <div class='card'>
      <h2>Recent Orders</h2>
      <div id='orders'>Loading...</div>
      <button onclick='refreshOrders()'>Refresh Orders</button>
    </div>
  </div>

  <div class='card'>
    <h2>Market Search</h2>
    <div class='flex'>
      <label>Search markets <input type='text' id='search-query' placeholder='Enter market name or ticker...' style='width: 300px;'></label>
      <button onclick='searchMarkets()'>Search</button>
    </div>
    <pre id='search-results'>Enter a search term to find markets...</pre>
  </div>

  <div class='card'>
    <h2>Control Panel</h2>
    <div class='flex'>
      <label>Markets to scan <input type='number' id='limit' value='50' min='1' max='500'></label>
      <label>Auto Execute <select id='auto'><option value='false'>Disabled</option><option value='true'>Enabled</option></select></label>
      <button onclick='runScan()'>Run Scan</button>
    </div>
    <div class='flex' style='margin-top:10px;'>
      <label>Min Liquidity (cents) <input type='number' id='min_liquidity' placeholder='10000'></label>
      <label>Min Profit/Day ($) <input type='number' step='0.01' id='min_profit' placeholder='0.10'></label>
      <button class='secondary' onclick='updateSettings()'>Update Settings</button>
    </div>
    <pre id='scan-output'>Waiting for scan...</pre>
  </div>

  <script>
    async function refreshStatus(){
      const res = await fetch('/api/status');
      const data = await res.json();
      const color = data.connected ? '#22c55e' : '#ef4444';
      document.getElementById('status-text').innerHTML = `<strong style='color:${color}'>${data.connected ? 'Connected' : 'Disconnected'}</strong><br>${JSON.stringify(data.details)}`;
    }

    async function refreshWallet(){
      const res = await fetch('/api/wallet');
      const data = await res.json();
      document.getElementById('wallet').innerHTML = data.error ? data.error : `
        <div class='stat'>Available: $${((data.available_cash ?? 0)/100).toFixed(2)}</div>
        <div class='stat'>Reserved: $${((data.reserved_cash ?? 0)/100).toFixed(2)}</div>
        <div class='stat'>Equity: $${((data.total_equity ?? 0)/100).toFixed(2)}</div>`;
    }

    async function refreshOrders(){
      const res = await fetch('/api/orders');
      const data = await res.json();
      if(!data.length){
        document.getElementById('orders').innerText = 'No recent orders (or unable to fetch).';
        return;
      }
      const rows = data.map(o => `<li><strong>${o.ticker || o.id}</strong> - ${o.state || 'unknown'} @ ${o.price || '?'}¢ (${o.side || ''})</li>`).join('');
      document.getElementById('orders').innerHTML = `<ul>${rows}</ul>`;
    }

    async function runScan(){
      const limit = document.getElementById('limit').value || 50;
      const auto = document.getElementById('auto').value;
      document.getElementById('scan-output').innerText = 'Scanning...';
      const res = await fetch(`/api/scan?limit=${limit}&auto_execute=${auto}`);
      const data = await res.json();
      document.getElementById('scan-output').innerText = JSON.stringify(data, null, 2);
    }

    async function updateSettings(){
      const minLiq = document.getElementById('min_liquidity').value;
      const minProfit = document.getElementById('min_profit').value;
      const payload = {};
      if(minLiq) payload.min_liquidity = parseInt(minLiq);
      if(minProfit) payload.min_profit_per_day = parseFloat(minProfit);
      const res = await fetch('/api/settings', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      document.getElementById('scan-output').innerText = 'Settings updated: ' + JSON.stringify(data, null, 2);
    }

    async function searchMarkets(){
      const query = document.getElementById('search-query').value.trim();
      if(!query){
        document.getElementById('search-results').innerText = 'Please enter a search term.';
        return;
      }
      document.getElementById('search-results').innerText = 'Searching...';
      const res = await fetch(`/api/search?query=${encodeURIComponent(query)}`);
      const data = await res.json();
      if(data.error){
        document.getElementById('search-results').innerText = `Error: ${data.error}`;
      } else if(!data.markets || data.markets.length === 0){
        document.getElementById('search-results').innerText = 'No markets found matching your search.';
      } else {
        const results = data.markets.map(m => {
          const title = m.title || 'Unknown';
          const ticker = m.ticker_name || m.ticker || 'N/A';
          const yes_bid = m.yes_bid ?? 'N/A';
          const yes_ask = m.yes_ask ?? 'N/A';
          const no_bid = m.no_bid ?? 'N/A';
          const no_ask = m.no_ask ?? 'N/A';
          const liquidity = ((m.liquidity ?? 0) / 100).toFixed(2);
          return `
Ticker: ${ticker}
Title: ${title}
YES Bid: ${yes_bid}¢ | YES Ask: ${yes_ask}¢
NO Bid: ${no_bid}¢ | NO Ask: ${no_ask}¢
Liquidity: $${liquidity}
${'─'.repeat(60)}`;
        }).join('\n');
        document.getElementById('search-results').innerText = `Found ${data.markets.length} market(s):\n\n${results}`;
      }
    }

    refreshStatus();
    refreshWallet();
    refreshOrders();
  </script>
</body></html>"""


@app.get("/api/status")
def api_status():
    return client.check_connection()


@app.get("/api/wallet")
def api_wallet():
    return client.get_wallet_summary()


@app.get("/api/orders")
def api_orders(limit: int = 25):
    return client.get_recent_orders(limit=limit)


@app.get("/api/scan")
def api_scan(limit: int = 50, auto_execute: bool = False):
    # Get markets to add debug info
    markets = client.get_markets(limit=limit, status="open")
    filtered_markets = bot.filter_markets_by_liquidity(markets) if markets else []

    arbitrage_opps, trade_opps, executed_count = bot.scan_all_opportunities(
        limit=limit,
        auto_execute=auto_execute
    )
    return {
        "arbitrage_opportunities": [opp.__dict__ for opp in arbitrage_opps],
        "trade_opportunities": [opp.__dict__ for opp in trade_opps],
        "executed": executed_count,
        "debug": {
            "total_markets_fetched": len(markets) if markets else 0,
            "markets_after_liquidity_filter": len(filtered_markets),
            "min_liquidity": bot.min_liquidity,
            "min_profit_per_day": bot.min_profit_per_day,
            "sample_market_fields": list(markets[0].keys()) if markets and len(markets) > 0 else []
        }
    }


@app.post("/api/settings")
def api_settings(payload: SettingsPayload):
    if payload.min_liquidity is not None:
        bot.min_liquidity = payload.min_liquidity
    if payload.min_profit_per_day is not None:
        bot.min_profit_per_day = payload.min_profit_per_day

    return {
        "min_liquidity": bot.min_liquidity,
        "min_profit_per_day": bot.min_profit_per_day
    }


@app.get("/api/search")
def api_search(query: str, limit: int = 100):
    """Search for markets by name or ticker."""
    if not query or len(query.strip()) == 0:
        return {"error": "Query parameter is required", "markets": []}

    try:
        # Get all open markets
        all_markets = client.get_markets(limit=limit, status="open")

        if not all_markets:
            return {"markets": [], "count": 0}

        # Filter markets by search query (case-insensitive)
        query_lower = query.lower().strip()
        matching_markets = []

        for market in all_markets:
            title = market.get("title", "").lower()
            ticker = market.get("ticker_name", market.get("ticker", "")).lower()

            # Match if query appears in title or ticker
            if query_lower in title or query_lower in ticker:
                matching_markets.append(market)

        return {
            "markets": matching_markets,
            "count": len(matching_markets),
            "query": query
        }
    except Exception as e:
        return {"error": str(e), "markets": []}


@app.get("/api/debug/markets")
def api_debug_markets(limit: int = 10):
    """Debug endpoint to see raw market data."""
    try:
        markets = client.get_markets(limit=limit, status="open")

        # Filter by liquidity
        filtered_markets = bot.filter_markets_by_liquidity(markets)

        return {
            "total_markets_fetched": len(markets),
            "markets_after_liquidity_filter": len(filtered_markets),
            "min_liquidity_threshold": bot.min_liquidity,
            "min_profit_per_day": bot.min_profit_per_day,
            "sample_markets": markets[:5] if markets else [],
            "sample_filtered": filtered_markets[:5] if filtered_markets else []
        }
    except Exception as e:
        return {"error": str(e)}

