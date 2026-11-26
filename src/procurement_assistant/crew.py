"""CrewAI sequential multi-agent procurement workflow."""

from __future__ import annotations

import os
from pathlib import Path

from crewai import Agent, Crew, LLM, Process, Task

from procurement_assistant.models import (
    CompanyContext,
    ProcurementAnalysis,
    ScrapedProductsOutput,
    SearchResultsOutput,
)
from procurement_assistant.report_generator import render_html_report, strip_markdown_fences
from procurement_assistant.tools import ScrapeGraphProductTool, TavilyProductSearchTool


class ProcurementCrew:
    """Orchestrates 4 specialized CrewAI agents sequentially for end-to-end procurement."""

    def __init__(self, context: CompanyContext, model_name: str | None = None) -> None:
        self.context = context
        resolved_model = model_name or os.getenv("CREWAI_MODEL", "gpt-4o-mini")
        self.llm = LLM(model=resolved_model, temperature=0.2)
        self.tavily_tool = TavilyProductSearchTool()
        self.scrapegraph_tool = ScrapeGraphProductTool()

    def build_agents(self) -> tuple[Agent, Agent, Agent, Agent]:
        """Instantiate the 4 procurement agents with company context."""
        ctx_block = self.context.to_prompt_block()

        search_agent = Agent(
            role="Procurement Search Strategist",
            goal=(
                f"Discover verified vendor product listings for {self.context.company_name} "
                "across multiple reputable websites using Tavily Search."
            ),
            backstory=(
                "You are an expert B2B sourcing specialist. You formulate precise search queries, "
                "avoid excluded vendors, prioritize preferred vendors, and return clean candidate URLs.\n\n"
                f"Company Context:\n{ctx_block}"
            ),
            tools=[self.tavily_tool],
            llm=self.llm,
            verbose=True,
            allow_delegation=False,
        )

        scraper_agent = Agent(
            role="Web Scraper & Product Data Collector",
            goal=(
                "Extract accurate pricing, availability, warranty, and technical specifications "
                "from each candidate product URL using ScrapeGraph."
            ),
            backstory=(
                "You are a meticulous data extraction engineer. You scrape product pages with "
                "ScrapeGraph SmartScraper and normalize every product's price, specs, and warranty.\n\n"
                f"Company Context:\n{ctx_block}"
            ),
            tools=[self.scrapegraph_tool],
            llm=self.llm,
            verbose=True,
            allow_delegation=False,
        )

        analyst_agent = Agent(
            role="Procurement Analyst & Product Comparator",
            goal=(
                "Compare and rank all scraped products on price, technical specifications, and overall "
                "value according to the company's evaluation weights and budget."
            ),
            backstory=(
                "You are a senior procurement analyst. You evaluate total cost of ownership, "
                "compliance with mandatory specs, warranty coverage, and vendor reliability to "
                "produce an objective, ranked recommendation.\n\n"
                f"Company Context:\n{ctx_block}"
            ),
            llm=self.llm,
            verbose=True,
            allow_delegation=False,
        )

        report_agent = Agent(
            role="Procurement Report Generator",
            goal=(
                "Generate a polished, executive-ready standalone HTML procurement report "
                "summarizing the comparison, rankings, and final purchasing recommendation."
            ),
            backstory=(
                "You are an executive communications and procurement reporting specialist. "
                "You transform structured procurement analysis into a clean, self-contained HTML5 "
                "document with clear tables, pros/cons, and actionable next steps.\n\n"
                f"Company Context:\n{ctx_block}"
            ),
            llm=self.llm,
            verbose=True,
            allow_delegation=False,
        )

        return search_agent, scraper_agent, analyst_agent, report_agent

    def build_tasks(
        self,
        procurement_query: str,
        agents: tuple[Agent, Agent, Agent, Agent],
    ) -> list[Task]:
        """Define the 4 sequential tasks with explicit context chaining."""
        search_agent, scraper_agent, analyst_agent, report_agent = agents
        ctx_block = self.context.to_prompt_block()

        search_task = Task(
            description=(
                f"Search for products matching the procurement request: '{procurement_query}'.\n"
                f"Execute 2-3 targeted Tavily searches to find 4-6 distinct product pages across "
                f"different vendor websites. Exclude domains from: {self.context.excluded_vendors}.\n\n"
                f"Company Context:\n{ctx_block}"
            ),
            expected_output=(
                "A structured list of candidate product URLs with title, website, snippet, and query_used."
            ),
            agent=search_agent,
            output_pydantic=SearchResultsOutput,
        )

        scrape_task = Task(
            description=(
                "Using the candidate URLs from the search results, scrape each product page using "
                "`scrapegraph_product_scraper`. Extract product name, vendor, website, unit price in USD, "
                "availability, warranty months, and technical specs (CPU, RAM, storage, display, etc.). "
                "Evaluate whether each product meets the company's required specs."
            ),
            expected_output=(
                "Structured JSON containing all scraped products and any URLs that failed to scrape."
            ),
            agent=scraper_agent,
            context=[search_task],
            output_pydantic=ScrapedProductsOutput,
        )

        analysis_task = Task(
            description=(
                f"Compare and rank the scraped products for '{procurement_query}' using the company's "
                f"weights (Price: {self.context.evaluation_weights.price:.0%}, "
                f"Specs: {self.context.evaluation_weights.specs:.0%}, "
                f"Value: {self.context.evaluation_weights.value:.0%}) and max unit budget of "
                f"${self.context.budget_max_usd:,.2f} USD for {self.context.quantity} units.\n"
                "Compute 0-100 sub-scores (price_score, specs_score, value_score, weighted_total), "
                "rank products from #1 downward, list pros/cons, and provide an executive summary, "
                "recommendation rationale, and next steps."
            ),
            expected_output=(
                "Complete ProcurementAnalysis JSON with ranked_products, recommended product/vendor, "
                "estimated total cost, executive summary, rationale, and risks/next steps."
            ),
            agent=analyst_agent,
            context=[scrape_task],
            output_pydantic=ProcurementAnalysis,
        )

        report_task = Task(
            description=(
                "Using the ProcurementAnalysis from the previous task, produce a complete, "
                "self-contained HTML5 procurement report (with embedded CSS, KPI summary, "
                "top recommendation callout, comparison table, pros/cons, and next steps). "
                "Return ONLY raw HTML starting with <!DOCTYPE html>."
            ),
            expected_output="A complete, valid standalone HTML5 document.",
            agent=report_agent,
            context=[analysis_task],
        )

        return [search_task, scrape_task, analysis_task, report_task]

    def run(self, procurement_query: str, output_path: str | Path = "output/procurement_report.html") -> Path:
        """Run the sequential CrewAI pipeline and save the final HTML report."""
        agents = self.build_agents()
        tasks = self.build_tasks(procurement_query, agents)

        crew = Crew(
            agents=list(agents),
            tasks=tasks,
            process=Process.sequential,
            verbose=True,
        )
        result = crew.kickoff()

        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        # Prefer deterministic Jinja2 rendering if structured ProcurementAnalysis is available
        analysis_task = tasks[2]
        if analysis_task.output and getattr(analysis_task.output, "pydantic", None):
            analysis = analysis_task.output.pydantic
            if isinstance(analysis, ProcurementAnalysis):
                return render_html_report(analysis, self.context, target)

        # Fallback: write the Report Agent's cleaned HTML output directly
        raw_html = strip_markdown_fences(str(result.raw if hasattr(result, "raw") else result))
        target.write_text(raw_html, encoding="utf-8")
        return target

