"""Deterministic scoring and ranking utilities for procurement candidates."""

from __future__ import annotations

from procurement_assistant.models import (
    CompanyContext,
    ProductScoreBreakdown,
    RankedProduct,
    ScrapedProduct,
)


def compute_price_score(price_usd: float | None, budget_max_usd: float, min_price_usd: float) -> float:
    """Score price on a 0-100 scale relative to budget and the cheapest candidate."""
    if price_usd is None or price_usd <= 0:
        return 30.0
    if price_usd > budget_max_usd:
        overage_ratio = (price_usd - budget_max_usd) / max(budget_max_usd, 1.0)
        return round(max(5.0, 45.0 - overage_ratio * 60.0), 2)

    if budget_max_usd <= min_price_usd:
        return 90.0

    # Linearly scale between 100 (cheapest) and 60 (at max budget)
    ratio = (budget_max_usd - price_usd) / (budget_max_usd - min_price_usd)
    return round(60.0 + ratio * 40.0, 2)


def compute_specs_score(product: ScrapedProduct, context: CompanyContext) -> float:
    """Score technical specifications on a 0-100 scale."""
    base = 75.0 if product.meets_required_specs else 35.0
    spec_count_bonus = min(len(product.specs), 6) * 3.0
    highlight_bonus = min(len(product.highlights), 3) * 2.0
    return round(min(100.0, base + spec_count_bonus + highlight_bonus), 2)


def compute_value_score(product: ScrapedProduct, context: CompanyContext) -> float:
    """Score overall value (warranty, preferred vendor, availability) on a 0-100 scale."""
    score = 55.0

    if product.warranty_months is not None:
        if product.warranty_months >= context.warranty_min_months:
            extra_years = (product.warranty_months - context.warranty_min_months) / 12.0
            score += min(25.0, 15.0 + extra_years * 5.0)
        else:
            score -= 15.0

    vendor_lower = f"{product.vendor} {product.website}".lower()
    if any(pref.lower() in vendor_lower for pref in context.preferred_vendors):
        score += 12.0

    if "in stock" in product.availability.lower() or "available" in product.availability.lower():
        score += 8.0

    return round(max(0.0, min(100.0, score)), 2)


def score_and_rank_products(
    products: list[ScrapedProduct],
    context: CompanyContext,
) -> list[RankedProduct]:
    """Score, sort, and rank scraped products against the company context."""
    valid_prices = [p.price_usd for p in products if p.price_usd is not None and p.price_usd > 0]
    min_price = min(valid_prices) if valid_prices else context.budget_max_usd * 0.7

    weights = context.evaluation_weights
    scored: list[RankedProduct] = []

    for product in products:
        p_score = compute_price_score(product.price_usd, context.budget_max_usd, min_price)
        s_score = compute_specs_score(product, context)
        v_score = compute_value_score(product, context)
        total = round(
            p_score * weights.price + s_score * weights.specs + v_score * weights.value,
            2,
        )
        within_budget = product.price_usd is not None and product.price_usd <= context.budget_max_usd

        pros: list[str] = []
        cons: list[str] = []

        if within_budget:
            pros.append(f"Within unit budget (${product.price_usd:,.2f} <= ${context.budget_max_usd:,.2f})")
        elif product.price_usd is not None:
            cons.append(f"Exceeds unit budget (${product.price_usd:,.2f} > ${context.budget_max_usd:,.2f})")
        else:
            cons.append("Unit price not confirmed on page")

        if product.meets_required_specs:
            pros.append("Meets mandatory technical specifications")
        else:
            cons.append("Missing one or more mandatory technical specifications")

        if product.warranty_months and product.warranty_months >= context.warranty_min_months:
            pros.append(f"Includes {product.warranty_months}-month warranty")
        elif product.warranty_months is not None:
            cons.append(f"Warranty ({product.warranty_months} mo) is below {context.warranty_min_months}-mo minimum")

        vendor_lower = f"{product.vendor} {product.website}".lower()
        if any(pref.lower() in vendor_lower for pref in context.preferred_vendors):
            pros.append(f"Preferred vendor ({product.vendor})")

        scored.append(
            RankedProduct(
                rank=1,
                product=product,
                scores=ProductScoreBreakdown(
                    price_score=p_score,
                    specs_score=s_score,
                    value_score=v_score,
                    weighted_total=total,
                ),
                within_budget=within_budget,
                pros=pros,
                cons=cons,
                recommendation_note="",
            )
        )

    scored.sort(key=lambda item: item.scores.weighted_total, reverse=True)
    for idx, item in enumerate(scored, start=1):
        item.rank = idx
        if idx == 1:
            item.recommendation_note = "Top Overall Pick — Best weighted balance of price, specs, and value."
        elif item.within_budget:
            item.recommendation_note = "Strong alternative within budget."
        else:
            item.recommendation_note = "Consider only if budget exception is approved."

    return scored

