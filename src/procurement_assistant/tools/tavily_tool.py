"""CrewAI tool wrapper around the Tavily Search API for product discovery."""

from __future__ import annotations

import json
import os
from typing import Any, Type
from urllib.parse import urlparse

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class TavilySearchInput(BaseModel):
    """Input schema for TavilyProductSearchTool."""

    query: str = Field(..., description="Product search query, e.g. 'Lenovo ThinkPad T14 Gen 5 business laptop price specs'")
    max_results: int = Field(default=5, ge=1, le=10, description="Maximum number of search results to return")
    exclude_domains: list[str] = Field(
        default_factory=list,
        description="Optional list of domains to exclude (e.g. ['ebay.com', 'aliexpress.com'])",
    )


class TavilyProductSearchTool(BaseTool):
    """Search the web for vendor product pages, prices, and specifications using Tavily."""

    name: str = "tavily_product_search"
    description: str = (
        "Searches the web using Tavily to find candidate product pages across multiple vendor websites. "
        "Returns titles, URLs, domains, and snippets for further scraping."
    )
    args_schema: Type[BaseModel] = TavilySearchInput

    def _run(
        self,
        query: str,
        max_results: int = 5,
        exclude_domains: list[str] | None = None,
    ) -> str:
        api_key = os.getenv("TAVILY_API_KEY", "").strip()
        if not api_key:
            return json.dumps(
                {
                    "error": "TAVILY_API_KEY environment variable is not set.",
                    "query": query,
                    "results": [],
                }
            )

        try:
            from tavily import TavilyClient

            client = TavilyClient(api_key=api_key)
            search_kwargs: dict[str, Any] = {
                "query": query,
                "max_results": max_results,
                "search_depth": "advanced",
            }
            if exclude_domains:
                search_kwargs["exclude_domains"] = exclude_domains

            response = client.search(**search_kwargs)
            formatted_results = []
            for item in response.get("results", []):
                url = item.get("url", "")
                domain = urlparse(url).netloc.replace("www.", "") if url else ""
                formatted_results.append(
                    {
                        "title": item.get("title", ""),
                        "url": url,
                        "website": domain,
                        "snippet": item.get("content", ""),
                        "query_used": query,
                    }
                )
            return json.dumps({"query": query, "results": formatted_results}, indent=2)
        except Exception as exc:
            return json.dumps({"error": f"Tavily search failed: {exc}", "query": query, "results": []})

