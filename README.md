# 📊 DOOH Campaign Intelligence

> Upload any messy DOOH (Digital Out-of-Home) campaign export — CSV or Excel, any column naming — and get a fully built, filterable analytics dashboard in seconds. No manual column mapping. No manual charting.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Backend-000000?logo=flask&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-Database-4479A1?logo=mysql&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-Vanilla-F7DF1E?logo=javascript&logoColor=black)
![Chart.js](https://img.shields.io/badge/Chart.js-Visualization-FF6384?logo=chart.js&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-Data%20Cleaning-150458?logo=pandas&logoColor=white)


---

## 📌 Overview

Ad-ops teams pull campaign performance exports from different DSPs and screen vendors — and every one of them names columns differently (`revenue` vs `rev_val` vs `income`, `city` vs `geo_loc`, etc.). Instead of forcing a fixed template, this dashboard **detects what each column means automatically**, cleans the data, stores it, and renders a complete performance dashboard — all from one file upload.

**One-sentence pitch:** *Upload any campaign export, get a clean dashboard — no manual column mapping, no manual charting.*

---

## ✨ Key Features

**Smart data ingestion**
- Fuzzy column detection — three-tier matching (exact → prefix → substring) maps arbitrary column names to the fields the dashboard needs
- Six-step cleaning pipeline: empty-row removal, deduplication, type coercion, date normalization, derived-metric calculation, zero-signal row removal
- Every cleaning decision is logged and shown to the user (detected columns, rows fixed, warnings) — so the automation stays transparent, not a black box
- Handles messy currency symbols, percentage signs, and six different date formats out of the box

**Analytics & visualization**
- Auto-computed KPIs: Revenue, Impressions, Clicks, Ad Spend, ROI %, CTR, CPC, CPM
- 5 interactive Chart.js visualizations: revenue & impressions over time, revenue by industry/city, top-10 campaigns by ROI
- Auto-generated, plain-English insights (top city, top industry, best/worst ROI campaign, best CTR)
- Top 5 / Bottom 5 campaign tables by ROI

**Screen-level intelligence** *(auto-enabled when the data supports it)*
- Per-screen performance table with occupancy rate (booked hours vs. available hours)
- Delivery discrepancy detection — flags screens under-delivering against committed hours by ≥10%
- Anomaly detection — flags any screen-day where impressions drop below 50% of that screen's own historical average

**Live filtering & currency**
- Client-side filtering by city, industry, campaign, and date range — instant, no server round-trip
- Multi-currency display (INR/USD/EUR/GBP/AED) via live exchange rates, applied across every KPI, chart, and table
- Week-over-week and month-over-month period comparison cards, anchored to the dataset's own latest date
- Dashboard state persists across page reloads via `localStorage`
- One-click PDF export of the full report

---

## 🏗️ Architecture

```
Browser (Index.html + Style.css + Script.js + Dashboard.js)
        │  fetch('/api/upload')  or  fetch('/api/load_from_db')
        ▼
Flask backend (app.py)
        │
        ├─► clean_data.py      → column detection, validation, normalization
        ├─► dashboard_data.py  → KPI/chart/table/insight aggregation
        └─► db_config.py       → MySQL persistence
```

The frontend receives one full dashboard payload on upload, but also keeps the full row-level dataset in memory — every filter change is recomputed client-side instantly, with no additional server calls.

---

## 📁 Project Structure

```
.
├── app.py                 # Flask routes — thin HTTP layer only
├── clean_data.py           # Column detection + data cleaning pipeline
├── dashboard_data.py       # KPI/chart/table/insight aggregation
├── db_config.py             # MySQL connection + insert/fetch logic
├── load_dummy_data.py      # CLI script to seed the DB from a CSV
├── dummy_dataset.csv       # Sample dataset for testing
├── index.html               # App shell (upload screen + dashboard screen)
├── style.css                # Styling
├── script.js                 # Upload orchestration + localStorage persistence
└── dashboard.js              # Rendering engine — KPIs, charts, tables, filters
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- MySQL Server (running locally or remotely)

### 1. Clone the repo
```bash
git clone https://github.com/prathmesh0work/DOOH-Campaign-Intelligence.git
cd DOOH-Campaign-Intelligence
```

### 2. Set up a virtual environment
```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install flask flask-cors pandas mysql-connector-python python-dotenv openpyxl
```

### 4. Configure the database
Create a `.env` file in the project root:
```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=your_mysql_user
DB_PASSWORD=your_mysql_password
DB_NAME=dooh_dashboard
```
Then create the `campaigns` table (schema matches the fields read/written in `db_config.py`):
```sql
CREATE TABLE campaigns (
    id INT AUTO_INCREMENT PRIMARY KEY,
    campaign_name VARCHAR(255),
    city VARCHAR(100),
    industry VARCHAR(100),
    screen_id VARCHAR(100),
    campaign_date DATE,
    revenue DECIMAL(12,2),
    ad_spend DECIMAL(12,2),
    impressions INT,
    clicks INT,
    hours_booked DECIMAL(8,2),
    hours_committed DECIMAL(8,2)
);
```

### 5. Run it
```bash
python app.py
```
Open `http://localhost:5000` and upload `dummy_dataset.csv` to try it immediately.

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Serves the app shell |
| `POST` | `/api/upload` | Accepts a CSV/XLS/XLSX file, cleans it, saves to DB, returns the full dashboard payload |
| `GET` | `/api/load_from_db` | Rebuilds the dashboard from existing database records |
| `GET` | `/api/health` | Health check |

---

## 🧠 How Column Detection Works

Rather than requiring a fixed template, `clean_data.py` matches incoming columns against a dictionary of known aliases per field, in three passes of decreasing confidence:

1. **Exact match** — `"revenue" == "revenue"`
2. **Prefix match** — `"revenue_usd".startswith("revenue")`
3. **Substring match** — `"total_revenue"` contains `"revenue"`

Once a column is claimed by one field, it can't be reused for another — preventing ambiguous double-mapping. Anything that can't be matched defaults safely to `0`/`"Unknown"` and is logged as a warning, rather than crashing the upload.

---

## ⚠️ Known Limitations

- Aggregation logic exists in both Python (initial dashboard) and JavaScript (live filtering) — a deliberate trade-off for instant client-side filtering, at the cost of two implementations to keep in sync
- No streaming/chunked file reading — large files (near the 25MB cap) are read fully into memory
- No authentication on any endpoint — suitable for internal/single-user use, not multi-tenant deployment
- Column matching is heuristic — unusual naming could silently map to the wrong field; always check the "Detected Columns" panel after upload
- Currency exchange rates are fetched once per session and not refreshed automatically

---

## 🗺️ Roadmap

- [ ] User-facing column-mapping confirmation step before processing
- [ ] Chunked/streaming upload for large files
- [ ] Basic authentication
- [ ] Move client-side aggregation to a shared `/api/aggregate` endpoint to remove logic duplication

---

## 📄 License

This project is licensed under the MIT License — see the `LICENSE` file for details.

## 👤 Author

**Prathmesh** — [GitHub](https://github.com/prathmesh0work)
