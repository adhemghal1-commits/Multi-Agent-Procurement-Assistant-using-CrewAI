"""CrewAI tool wrapper around ScrapeGraph (scrapegraph-py) for structured product extraction."""

from __future__ import annotations

import json
import os
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class ScrapeGraphInput(BaseModel):
    """Input schema for ScrapeGraphProductTool."""

    url: str = Field(..., description="The full product webpage URL to scrape")
    extraction_prompt: str = Field(
        default=(
            "Extract the product name, vendor/seller name, unit price in USD (numeric and raw text), "
            "stock availability, warranty duration in months, and key technical specifications "
            "(CPU, RAM, storage, display, connectivity, weight) as JSON."
        ),
        description="Natural-language instruction describing what product fields to extract",
    )


class ScrapeGraphProductTool(BaseTool):
    """Extract structured product details, pricing, and specs from a webpage using ScrapeGraph."""

    name: str = "scrapegraph_product_scraper"
    description: str = (
        "Scrapes a target product webpage using ScrapeGraph SmartScraper and returns structured JSON "
        "containing product name, vendor, price, availability, warranty, and technical specifications."
    )
    args_schema: Type[BaseModel] = ScrapeGraphInput

    def _run(self, url: str, extraction_prompt: str = "") -> str:
        api_key = os.getenv("SCRAPEGRAPH_API_KEY", "").strip()
        if not api_key:
            return json.dumps(
                {
                    "error": "SCRAPEGRAPH_API_KEY environment variable is not set.",
                    "url": url,
                    "data": None,
                }
            )

        prompt = extraction_prompt or ScrapeGraphInput.model_fields["extraction_prompt"].default
        try:
            from scrapegraph_py import Client

            client = Client(api_key=api_key)
            response = client.smartscraper(
                website_url=url,
                user_prompt=prompt,
            )
            return json.dumps({"url": url, "data": response}, indent=2, default=str)
        except Exception as exc:
            return json.dumps({"error": f"ScrapeGraph extraction failed: {exc}", "url": url, "data": None})

