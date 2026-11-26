"""Offline demo pipeline simulating the 4-agent sequential workflow without live API keys."""

from __future__ import annotations

from pathlib import Path

from procurement_assistant.models import (
    CompanyContext,
    ProcurementAnalysis,
    ScrapedProduct,
)
from procurement_assistant.report_generator import render_html_report
from procurement_assistant.scoring import score_and_rank_products


def run_demo_pipeline(
    procurement_query: str,
    context: CompanyContext,
    output_path: str | Path = "output/procurement_report.html",
) -> tuple[ProcurementAnalysis, Path]:
    """Simulate multi-website scraping, scoring, ranking, and HTML report generation."""
    sample_products = [
        ScrapedProduct(
            product_name="Lenovo ThinkPad T14 Gen 5 (Intel Core Ultra 7)",
            vendor="Lenovo",
            website="lenovo.com",
            url="https://www.lenovo.com/us/en/p/laptops/thinkpad/thinkpadt/thinkpad-t14-gen-5-14-inch-intel/len101t0089",
            price_usd=1549.00,
            original_price_text="$1,549.00",
            availability="In Stock - Ships in 2 business days",
            warranty_months=36,
            specs={
                "Processor": "Intel Core Ultra 7 155U",
                "RAM": "32GB DDR5-5600",
                "Storage": "1TB PCIe Gen4 NVMe SSD",
                "Display": '14" WUXGA (1920x1200) Anti-Glare IPS 400 nits',
                "Connectivity": "Wi-Fi 6E, Thunderbolt 4, RJ-45 Ethernet",
                "Weight": "1.31 kg (2.89 lbs)",
            },
            highlights=["3-year Premier On-Site Support", "MIL-STD-810H tested", "User-upgradeable RAM"],
            meets_required_specs=True,
        ),
        ScrapedProduct(
            product_name="Dell Latitude 5450 Business Laptop",
            vendor="Dell",
            website="dell.com",
            url="https://www.dell.com/en-us/shop/dell-laptops/latitude-5450-laptop/spd/latitude-14-5450-laptop",
            price_usd=1429.00,
            original_price_text="$1,429.00",
            availability="In Stock - Next-day business shipping",
            warranty_months=36,
            specs={
                "Processor": "Intel Core Ultra 5 135U vPro",
                "RAM": "16GB DDR5-5600",
                "Storage": "512GB M.2 PCIe NVMe SSD",
                "Display": '14" FHD (1920x1080) Anti-Glare 250 nits',
                "Connectivity": "Wi-Fi 6E, Dual Thunderbolt 4, HDMI 2.1",
                "Weight": "1.40 kg (3.09 lbs)",
            },
            highlights=["3-year ProSupport Next Business Day", "vPro Enterprise manageability"],
            meets_required_specs=True,
        ),
        ScrapedProduct(
            product_name="HP EliteBook 840 G11 (via CDW)",
            vendor="CDW",
            website="cdw.com",
            url="https://www.cdw.com/product/hp-elitebook-840-g11-14-core-ultra-7/7891234",
            price_usd=1765.00,
            original_price_text="$1,765.00",
            availability="In Stock at CDW Warehouse",
            warranty_months=24,
            specs={
                "Processor": "Intel Core Ultra 7 155H",
                "RAM": "16GB DDR5-5600",
                "Storage": "512GB PCIe NVMe SSD",
                "Display": '14" WUXGA Anti-Glare 300 nits',
                "Connectivity": "Wi-Fi 6E, 2x Thunderbolt 4",
                "Weight": "1.41 kg (3.11 lbs)",
            },
            highlights=["CDW dedicated account billing", "HP Wolf Security Pro"],
            meets_required_specs=True,
        ),
        ScrapedProduct(
            product_name="Apple MacBook Pro 14 (M3 Pro, 18GB/512GB)",
            vendor="B&H Photo",
            website="bhphotovideo.com",
            url="https://www.bhphotovideo.com/c/product/1793624-REG/apple_mrx33ll_a_14_macbook_pro_m3.html",
            price_usd=1949.00,
            original_price_text="$1,949.00",
            availability="In Stock",
            warranty_months=12,
            specs={
                "Processor": "Apple M3 Pro (11-core CPU / 14-core GPU)",
                "RAM": "18GB Unified Memory",
                "Storage": "512GB SSD",
                "Display": '14.2" Liquid Retina XDR',
                "Connectivity": "Wi-Fi 6E, 3x Thunderbolt 4, MagSafe 3",
                "Weight": "1.61 kg (3.5 lbs)",
            },
            highlights=["Exceptional battery life", "High-resolution XDR display"],
            meets_required_specs=True,
        ),
    ]

    ranked = score_and_rank_products(sample_products, context)
    top = ranked[0]
    total_cost = (top.product.price_usd * context.quantity) if top.product.price_usd else None

    analysis = ProcurementAnalysis(
        procurement_query=procurement_query,
        company_name=context.company_name,
        quantity=context.quantity,
        budget_max_usd=context.budget_max_usd,
        ranked_products=ranked,
        recommended_product_name=top.product.product_name,
        recommended_vendor=top.product.vendor,
        estimated_total_cost_usd=total_cost,
        executive_summary=(
            f"Across 4 vendor websites evaluated for {context.company_name}, "
            f"{top.product.product_name} from {top.product.vendor} ranked #1 with a weighted "
            f"score of {top.scores.weighted_total:.1f}/100 at ${top.product.price_usd:,.2f} per unit."
        ),
        recommendation_rationale=(
            f"{top.product.product_name} delivers 32GB RAM and a 1TB NVMe SSD—double the baseline "
            f"requirement—while remaining ${context.budget_max_usd - (top.product.price_usd or 0):,.2f} "
            f"under the ${context.budget_max_usd:,.2f} unit budget and including a 36-month warranty."
        ),
        risks_and_next_steps=[
            f"Request a formal volume quote from {top.product.vendor} for {context.quantity} units to lock in potential 5-8% fleet discount.",
            "Confirm VAT/tax invoice formatting and US/EU power cord SKUs prior to PO issuance.",
            "Verify 36-month on-site warranty serial registration upon delivery.",
        ],
    )

    report_path = render_html_report(analysis, context, output_path)
    return analysis, report_path

