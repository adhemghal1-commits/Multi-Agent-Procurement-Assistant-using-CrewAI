# Multi-Agent Procurement Assistant (CrewAI)

A sequential multi-agent AI procurement system built with **CrewAI**, **Tavily Search**, and **ScrapeGraph** that searches multiple vendor websites, scrapes structured product specifications and pricing, compares and ranks candidates against a company's procurement profile, and generates a standalone **HTML procurement report**.

## Architecture

1. **Company Context (`config/company_profile.json`)**: Defines organization details, unit budget, quantity, mandatory technical specs, preferred/excluded vendors, minimum warranty, and evaluation weights (`price`, `specs`, `value`).
2. **Agent 1 — Procurement Search Strategist**: Uses `TavilyProductSearchTool` to discover candidate product listings across multiple websites.
3. **Agent 2 — Web Scraper & Product Data Collector**: Uses `ScrapeGraphProductTool` (`SmartScraper`) to extract structured pricing, availability, warranty, and technical specs from each URL.
4. **Agent 3 — Procurement Analyst & Product Comparator**: Normalizes, scores, and ranks products on price, specs, and value (`ProcurementAnalysis`).
5. **Agent 4 — Procurement Report Generator**: Produces a responsive, executive-ready HTML5 report (`output/procurement_report.html`).

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` with your API keys (`OPENAI_API_KEY` or `GEMINI_API_KEY`, `TAVILY_API_KEY`, `SCRAPEGRAPH_API_KEY`).

## Usage

Run the live sequential CrewAI pipeline:

```powershell
.\.venv\Scripts\python.exe main.py --query "14-inch enterprise business laptops with 16GB+ RAM" --output output/procurement_report.html
```

Run offline demo mode (no API keys required) to test scoring, ranking, and HTML report generation:

```powershell
.\.venv\Scripts\python.exe main.py --demo
```

Run tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

