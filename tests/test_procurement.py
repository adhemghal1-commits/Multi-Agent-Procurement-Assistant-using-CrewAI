"""Unit and integration tests for the Multi-Agent Procurement Assistant."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from procurement_assistant.crew import ProcurementCrew
from procurement_assistant.demo import run_demo_pipeline
from procurement_assistant.models import CompanyContext, EvaluationWeights, ScrapedProduct
from procurement_assistant.report_generator import strip_markdown_fences
from procurement_assistant.scoring import score_and_rank_products
from procurement_assistant.tools import ScrapeGraphProductTool, TavilyProductSearchTool


@pytest.fixture
def sample_context() -> CompanyContext:
    return CompanyContext.from_json_file(
        Path(__file__).resolve().parents[1] / "config" / "company_profile.json"
    )


def test_company_context_loads_and_validates_weights(sample_context: CompanyContext) -> None:
    assert sample_context.company_name == "Apex Horizon Technologies"
    assert sample_context.quantity == 15
    assert "Company: Apex Horizon Technologies" in sample_context.to_prompt_block()

    with pytest.raises(ValueError, match="must sum to 1.0"):
        EvaluationWeights(price=0.5, specs=0.5, value=0.5)


def test_scoring_ranks_within_budget_preferred_product_higher(sample_context: CompanyContext) -> None:
    products = [
        ScrapedProduct(
            product_name="Expensive Laptop",
            vendor="Unknown Store",
            website="unknown.example.com",
            url="https://unknown.example.com/p1",
            price_usd=2400.0,
            availability="Out of stock",
            warranty_months=12,
            specs={"RAM": "16GB", "SSD": "512GB"},
            meets_required_specs=True,
        ),
        ScrapedProduct(
            product_name="Lenovo ThinkPad T14",
            vendor="Lenovo",
            website="lenovo.com",
            url="https://lenovo.com/t14",
            price_usd=1500.0,
            availability="In Stock",
            warranty_months=36,
            specs={"CPU": "Core Ultra 7", "RAM": "32GB", "SSD": "1TB", "Display": "14-inch"},
            highlights=["On-site support"],
            meets_required_specs=True,
        ),
    ]

    ranked = score_and_rank_products(products, sample_context)
    assert len(ranked) == 2
    assert ranked[0].rank == 1
    assert ranked[0].product.product_name == "Lenovo ThinkPad T14"
    assert ranked[0].within_budget is True
    assert ranked[1].within_budget is False


def test_tavily_tool_handles_missing_key_and_mocked_client(monkeypatch: pytest.MonkeyPatch) -> None:
    tool = TavilyProductSearchTool()
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    res_missing = json.loads(tool._run(query="ThinkPad T14"))
    assert "TAVILY_API_KEY" in res_missing["error"]

    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    mock_client = MagicMock()
    mock_client.search.return_value = {
        "results": [
            {
                "title": "ThinkPad T14 Gen 5",
                "url": "https://www.lenovo.com/thinkpad-t14",
                "content": "Business laptop with 32GB RAM",
            }
        ]
    }
    with patch("tavily.TavilyClient", return_value=mock_client):
        res = json.loads(tool._run(query="ThinkPad T14", max_results=3))
    assert len(res["results"]) == 1
    assert res["results"][0]["website"] == "lenovo.com"


def test_scrapegraph_tool_handles_missing_key_and_mocked_client(monkeypatch: pytest.MonkeyPatch) -> None:
    tool = ScrapeGraphProductTool()
    monkeypatch.delenv("SCRAPEGRAPH_API_KEY", raising=False)
    res_missing = json.loads(tool._run(url="https://www.lenovo.com/t14"))
    assert "SCRAPEGRAPH_API_KEY" in res_missing["error"]

    monkeypatch.setenv("SCRAPEGRAPH_API_KEY", "test-sg-key")
    mock_client = MagicMock()
    mock_client.smartscraper.return_value = {"product_name": "ThinkPad T14", "price_usd": 1549.0}
    with patch("scrapegraph_py.Client", return_value=mock_client):
        res = json.loads(tool._run(url="https://www.lenovo.com/t14"))
    assert res["data"]["product_name"] == "ThinkPad T14"


def test_crew_builds_four_sequential_agents_and_tasks(
    sample_context: CompanyContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy-key")
    crew = ProcurementCrew(context=sample_context, model_name="gpt-4o-mini")
    agents = crew.build_agents()
    tasks = crew.build_tasks("Enterprise laptops", agents)

    assert len(agents) == 4
    assert len(tasks) == 4
    assert tasks[1].context == [tasks[0]]
    assert tasks[2].context == [tasks[1]]
    assert tasks[3].context == [tasks[2]]


def test_demo_pipeline_generates_html_report(sample_context: CompanyContext, tmp_path: Path) -> None:
    report_file = tmp_path / "report.html"
    analysis, path = run_demo_pipeline("Enterprise 14-inch laptops", sample_context, report_file)

    assert path.exists()
    html = path.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html
    assert analysis.company_name in html
    assert analysis.recommended_product_name in html


def test_strip_markdown_fences() -> None:
    raw = "```html\n<!DOCTYPE html><html><body>Hi</body></html>\n```"
    assert strip_markdown_fences(raw) == "<!DOCTYPE html><html><body>Hi</body></html>"

