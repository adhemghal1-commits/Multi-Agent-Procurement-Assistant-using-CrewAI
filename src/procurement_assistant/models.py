"""Pydantic data models for company context, search, scraping, and procurement analysis."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator


class EvaluationWeights(BaseModel):
    """Relative weights (summing to 1.0) for scoring candidate products."""

    price: float = Field(default=0.35, ge=0.0, le=1.0)
    specs: float = Field(default=0.40, ge=0.0, le=1.0)
    value: float = Field(default=0.25, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_sum(self) -> "EvaluationWeights":
        total = self.price + self.specs + self.value
        if abs(total - 1.0) > 1e-3:
            raise ValueError(f"Evaluation weights must sum to 1.0, got {total:.3f}")
        return self


class CompanyContext(BaseModel):
    """Company procurement profile injected into all CrewAI agents and tasks."""

    company_name: str = Field(..., description="Name of the procuring organization")
    industry: str = Field(..., description="Industry sector of the company")
    department: str = Field(default="Procurement", description="Requesting department")
    budget_max_usd: float = Field(..., gt=0, description="Maximum unit budget in USD")
    quantity: int = Field(default=1, ge=1, description="Number of units to procure")
    required_specs: list[str] = Field(default_factory=list, description="Mandatory technical requirements")
    preferred_vendors: list[str] = Field(default_factory=list, description="Preferred vendor names or domains")
    excluded_vendors: list[str] = Field(default_factory=list, description="Vendors to exclude from consideration")
    warranty_min_months: int = Field(default=12, ge=0, description="Minimum acceptable warranty in months")
    evaluation_weights: EvaluationWeights = Field(default_factory=EvaluationWeights)
    compliance_notes: str = Field(default="", description="Additional compliance, billing, or delivery notes")

    @classmethod
    def from_json_file(cls, path: str | Path) -> "CompanyContext":
        """Load a CompanyContext from a JSON configuration file."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(**data)

    def to_prompt_block(self) -> str:
        """Render a concise, structured summary for agent system prompts and task descriptions."""
        specs_str = "\n  - ".join(self.required_specs) if self.required_specs else "None specified"
        preferred_str = ", ".join(self.preferred_vendors) if self.preferred_vendors else "Any reputable vendor"
        excluded_str = ", ".join(self.excluded_vendors) if self.excluded_vendors else "None"
        return (
            f"Company: {self.company_name} ({self.industry}, Dept: {self.department})\n"
            f"Quantity: {self.quantity} units | Max Unit Budget: ${self.budget_max_usd:,.2f} USD "
            f"(Total Max: ${self.budget_max_usd * self.quantity:,.2f} USD)\n"
            f"Minimum Warranty: {self.warranty_min_months} months\n"
            f"Preferred Vendors: {preferred_str}\n"
            f"Excluded Vendors: {excluded_str}\n"
            f"Evaluation Weights -> Price: {self.evaluation_weights.price:.0%}, "
            f"Specs: {self.evaluation_weights.specs:.0%}, Value: {self.evaluation_weights.value:.0%}\n"
            f"Required Specs:\n  - {specs_str}\n"
            f"Compliance Notes: {self.compliance_notes or 'Standard commercial terms'}"
        )


class SearchResultItem(BaseModel):
    """Single candidate product page discovered via Tavily Search."""

    title: str
    url: str
    website: str = Field(default="", description="Domain or vendor site name")
    snippet: str = Field(default="", description="Relevant search snippet")
    query_used: str = Field(default="", description="Search query that surfaced this URL")


class SearchResultsOutput(BaseModel):
    """Structured output of the Search Agent."""

    procurement_query: str
    search_queries_executed: list[str]
    candidates: list[SearchResultItem]


class ScrapedProduct(BaseModel):
    """Structured product record extracted from a vendor webpage via ScrapeGraph."""

    product_name: str
    vendor: str
    website: str
    url: str
    price_usd: float | None = Field(default=None, description="Unit price in USD if available")
    original_price_text: str = Field(default="", description="Raw price string from the page")
    availability: str = Field(default="Unknown", description="Stock / shipping availability")
    warranty_months: int | None = Field(default=None, description="Warranty duration in months")
    specs: dict[str, Any] = Field(default_factory=dict, description="Extracted technical specifications")
    highlights: list[str] = Field(default_factory=list, description="Notable features or business perks")
    meets_required_specs: bool = Field(default=True)
    scrape_notes: str = Field(default="")


class ScrapedProductsOutput(BaseModel):
    """Structured output of the Scraper / Data Collector Agent."""

    products: list[ScrapedProduct]
    failed_urls: list[str] = Field(default_factory=list)


class ProductScoreBreakdown(BaseModel):
    """Normalized 0-100 sub-scores for a product."""

    price_score: float = Field(..., ge=0.0, le=100.0)
    specs_score: float = Field(..., ge=0.0, le=100.0)
    value_score: float = Field(..., ge=0.0, le=100.0)
    weighted_total: float = Field(..., ge=0.0, le=100.0)


class RankedProduct(BaseModel):
    """A scraped product enriched with rank, scores, and pros/cons."""

    rank: int = Field(..., ge=1)
    product: ScrapedProduct
    scores: ProductScoreBreakdown
    within_budget: bool
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)
    recommendation_note: str = Field(default="")


class ProcurementAnalysis(BaseModel):
    """Structured output of the Procurement Analyst Agent."""

    procurement_query: str
    company_name: str
    quantity: int
    budget_max_usd: float
    ranked_products: list[RankedProduct]
    recommended_product_name: str
    recommended_vendor: str
    estimated_total_cost_usd: float | None = None
    executive_summary: str
    recommendation_rationale: str
    risks_and_next_steps: list[str] = Field(default_factory=list)

