# Web UI Feature (`--ui`)

## Overview
`python run.py --ui` launches a local Flask server and opens a browser with a full portfolio dashboard.

## Backend
- Flask server serving JSON API endpoints (reuse existing analysis/portfolio modules)
- Endpoints: `/api/portfolio`, `/api/history`, `/api/rebalance`, `/api/summary`, `/api/transactions` (POST)
- Price cache in memory while server is running (avoid re-fetching Yahoo Finance on every request)
- POST `/api/transactions` appends a row to the CSV, then recalculates portfolio data
- Recalculation uses cached prices, so updates are instant after first load

## Frontend
- Single HTML page, minimal and clean design
- No frameworks (no React, no Vue) — vanilla HTML/CSS/JS only
- HTML must be semantic, well-structured and lightweight
- CSS: modern, responsive, dark/light friendly, minimal footprint
- JS: AJAX calls to API, no full page reloads

## Dashboard Sections
1. Portfolio overview cards: total value, total P&L, XIRR, cost basis
2. Instruments table: all per-instrument data (shares, cost, market value, returns, tax)
3. Allocation: pie chart (by instrument and by asset class) — use Chart.js (CDN, lightweight)
4. Historical performance table: 1m, 6m, 1y, since start
5. Rebalancing table: current vs target allocation, buy/sell suggestions
6. Add transaction form: type (dropdown), security (dropdown from config), date, shares, quote, fees, taxes — submit appends to CSV and refreshes data

## UX
- After adding a transaction, only the data refreshes (AJAX), page does not reload
- Loading spinner while fetching initial prices
- Form validation: required fields, numeric checks
- Success/error feedback on transaction submit

## Dependencies
- `flask` (add to requirements.txt)
- Chart.js via CDN (no install needed)

## File Structure
```
portfolio/
├── web.py              # Flask app, API routes, server launch
├── templates/
│   └── index.html      # Single page dashboard
├── static/
│   └── style.css       # Styles (optional, can be inline)
```
