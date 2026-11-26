"""CLI entry point for the Multi-Agent Procurement Assistant."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

# Ensure src/ is importable when running `python main.py` directly
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from procurement_assistant.demo import run_demo_pipeline
from procurement_assistant.models import CompanyContext


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Multi-Agent Procurement Assistant using CrewAI, Tavily Search, and ScrapeGraph"
    )
    parser.add_argument(
        "--query",
        type=str,
        default="14-inch enterprise business laptops with 16GB+ RAM and 512GB+ SSD",
        help="Product procurement request to research and compare",
    )
    parser.add_argument(
        "--company-config",
        type=str,
        default="config/company_profile.json",
        help="Path to the company context JSON file",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="output/procurement_report.html",
        help="Output path for the generated HTML procurement report",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="LLM model override for CrewAI agents (e.g. gpt-4o-mini, gemini/gemini-2.5-flash)",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run in offline demo mode using sample multi-vendor data (no API keys required)",
    )
    return parser.parse_args()


def main() -> int:
    load_dotenv()
    args = parse_args()
    context = CompanyContext.from_json_file(args.company_config)

    if args.demo:
        analysis, report_path = run_demo_pipeline(
            procurement_query=args.query,
            context=context,
            output_path=args.output,
        )
        print(f"[DEMO] Recommended: {analysis.recommended_product_name} ({analysis.recommended_vendor})")
        print(f"[DEMO] HTML report generated at: {report_path.resolve()}")
        return 0

    from procurement_assistant.crew import ProcurementCrew

    crew = ProcurementCrew(context=context, model_name=args.model)
    report_path = crew.run(procurement_query=args.query, output_path=args.output)
    print(f"Procurement HTML report generated at: {report_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

