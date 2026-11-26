"""HTML procurement report renderer and sanitizer."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, BaseLoader

from procurement_assistant.models import CompanyContext, ProcurementAnalysis

HTML_REPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Procurement Report — {{ analysis.company_name }}</title>
  <style>
    :root {
      --bg: #f4f6f9;
      --surface: #ffffff;
      --primary: #1d4ed8;
      --primary-dark: #1e3a8a;
      --accent: #059669;
      --accent-bg: #ecfdf5;
      --warn: #d97706;
      --danger: #dc2626;
      --text: #0f172a;
      --muted: #475569;
      --border: #e2e8f0;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.55;
    }
    .container {
      max-width: 1120px;
      margin: 0 auto;
      padding: 32px 20px 64px;
    }
    header.hero {
      background: linear-gradient(135deg, var(--primary-dark), var(--primary));
      color: #ffffff;
      padding: 32px;
      border-radius: 14px;
      box-shadow: 0 10px 25px rgba(30, 58, 138, 0.18);
      margin-bottom: 24px;
    }
    .hero-tag {
      display: inline-block;
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      background: rgba(255, 255, 255, 0.16);
      padding: 4px 10px;
      border-radius: 999px;
      margin-bottom: 10px;
    }
    header.hero h1 {
      margin: 0 0 8px;
      font-size: 28px;
      font-weight: 700;
    }
    header.hero p {
      margin: 0;
      opacity: 0.92;
      font-size: 15px;
    }
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }
    .kpi-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 18px 20px;
    }
    .kpi-label {
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--muted);
      margin-bottom: 6px;
    }
    .kpi-value {
      font-size: 22px;
      font-weight: 700;
      color: var(--text);
    }
    .card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 24px;
      margin-bottom: 24px;
    }
    .card h2 {
      margin-top: 0;
      font-size: 19px;
      border-bottom: 1px solid var(--border);
      padding-bottom: 10px;
      margin-bottom: 16px;
    }
    .recommendation-banner {
      background: var(--accent-bg);
      border: 1px solid #a7f3d0;
      border-left: 5px solid var(--accent);
      border-radius: 12px;
      padding: 20px 24px;
      margin-bottom: 24px;
    }
    .recommendation-banner h2 {
      margin: 0 0 8px;
      color: #065f46;
      font-size: 19px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }
    th, td {
      text-align: left;
      padding: 12px 10px;
      border-bottom: 1px solid var(--border);
      vertical-align: top;
    }
    th {
      background: #f8fafc;
      color: var(--muted);
      font-weight: 600;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    .badge {
      display: inline-block;
      padding: 3px 9px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 600;
    }
    .badge-ok { background: #dcfce7; color: #166534; }
    .badge-warn { background: #fef3c7; color: #92400e; }
    .badge-rank { background: #dbeafe; color: #1e40af; }
    .score-bar-wrap {
      width: 90px;
      background: #e2e8f0;
      height: 8px;
      border-radius: 999px;
      overflow: hidden;
      display: inline-block;
      vertical-align: middle;
      margin-right: 6px;
    }
    .score-bar {
      height: 100%;
      background: var(--primary);
    }
    .product-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 18px;
    }
    .product-card {
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 18px;
      background: #fcfdff;
    }
    .product-card h3 {
      margin: 0 0 6px;
      font-size: 17px;
    }
    .meta-line {
      font-size: 13px;
      color: var(--muted);
      margin-bottom: 12px;
    }
    .specs-list {
      margin: 0 0 12px;
      padding-left: 18px;
      font-size: 13px;
    }
    .pros-cons {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      font-size: 13px;
    }
    .pros-cons ul {
      margin: 4px 0 0;
      padding-left: 16px;
    }
    footer {
      text-align: center;
      font-size: 12px;
      color: var(--muted);
      margin-top: 32px;
    }
    a { color: var(--primary); text-decoration: none; }
    a:hover { text-decoration: underline; }
  </style>
</head>
<body>
  <div class="container">
    <header class="hero">
      <div class="hero-tag">Multi-Agent Procurement Report</div>
      <h1>{{ analysis.procurement_query }}</h1>
      <p>Prepared for <strong>{{ analysis.company_name }}</strong> ({{ context.industry }} &bull; {{ context.department }}) &bull; Generated {{ generated_at }}</p>
    </header>

    <section class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-label">Recommended Vendor</div>
        <div class="kpi-value">{{ analysis.recommended_vendor }}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Order Quantity</div>
        <div class="kpi-value">{{ analysis.quantity }} units</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Max Unit Budget</div>
        <div class="kpi-value">${{ "{:,.2f}".format(analysis.budget_max_usd) }}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Est. Total Spend</div>
        <div class="kpi-value">
          {% if analysis.estimated_total_cost_usd %}
            ${{ "{:,.2f}".format(analysis.estimated_total_cost_usd) }}
          {% else %}
            N/A
          {% endif %}
        </div>
      </div>
    </section>

    <section class="recommendation-banner">
      <h2>Top Recommendation: {{ analysis.recommended_product_name }}</h2>
      <p style="margin: 0 0 8px;">{{ analysis.executive_summary }}</p>
      <p style="margin: 0; font-size: 14px; color: #064e3b;"><strong>Rationale:</strong> {{ analysis.recommendation_rationale }}</p>
    </section>

    <section class="card">
      <h2>Product Comparison &amp; Ranking</h2>
      <table>
        <thead>
          <tr>
            <th>Rank</th>
            <th>Product &amp; Vendor</th>
            <th>Unit Price</th>
            <th>Warranty</th>
            <th>Price / Specs / Value</th>
            <th>Total Score</th>
            <th>Budget</th>
          </tr>
        </thead>
        <tbody>
          {% for item in analysis.ranked_products %}
          <tr>
            <td><span class="badge badge-rank">#{{ item.rank }}</span></td>
            <td>
              <strong>{{ item.product.product_name }}</strong><br />
              <span style="color: var(--muted); font-size: 12px;">
                {{ item.product.vendor }} ({{ item.product.website }}) &bull;
                <a href="{{ item.product.url }}" target="_blank" rel="noopener">Listing</a>
              </span>
            </td>
            <td>
              {% if item.product.price_usd %}
                <strong>${{ "{:,.2f}".format(item.product.price_usd) }}</strong>
              {% else %}
                {{ item.product.original_price_text or "N/A" }}
              {% endif %}
            </td>
            <td>{{ item.product.warranty_months ~ " mo" if item.product.warranty_months else "N/A" }}</td>
            <td>{{ item.scores.price_score|round(1) }} / {{ item.scores.specs_score|round(1) }} / {{ item.scores.value_score|round(1) }}</td>
            <td>
              <div class="score-bar-wrap"><div class="score-bar" style="width: {{ item.scores.weighted_total }}%;"></div></div>
              <strong>{{ item.scores.weighted_total|round(1) }}</strong>
            </td>
            <td>
              {% if item.within_budget %}
                <span class="badge badge-ok">Within Budget</span>
              {% else %}
                <span class="badge badge-warn">Over Budget</span>
              {% endif %}
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </section>

    <section class="card">
      <h2>Detailed Product Evaluations</h2>
      <div class="product-grid">
        {% for item in analysis.ranked_products %}
        <div class="product-card">
          <h3>#{{ item.rank }} {{ item.product.product_name }}</h3>
          <div class="meta-line">
            {{ item.product.vendor }} &bull; {{ item.product.availability }} &bull;
            <a href="{{ item.product.url }}" target="_blank" rel="noopener">View Product</a>
          </div>
          <ul class="specs-list">
            {% for key, val in item.product.specs.items() %}
            <li><strong>{{ key }}:</strong> {{ val }}</li>
            {% endfor %}
          </ul>
          <div class="pros-cons">
            <div>
              <strong style="color: #166534;">Pros</strong>
              <ul>
                {% for pro in item.pros %}<li>{{ pro }}</li>{% endfor %}
              </ul>
            </div>
            <div>
              <strong style="color: #991b1b;">Cons</strong>
              <ul>
                {% for con in item.cons %}<li>{{ con }}</li>{% endfor %}
                {% if not item.cons %}<li>None noted</li>{% endif %}
              </ul>
            </div>
          </div>
        </div>
        {% endfor %}
      </div>
    </section>

    <section class="card">
      <h2>Company Context &amp; Next Steps</h2>
      <p style="font-size: 14px; color: var(--muted); margin-top: 0;">
        <strong>Weights:</strong> Price {{ (context.evaluation_weights.price * 100)|round|int }}% &bull;
        Specs {{ (context.evaluation_weights.specs * 100)|round|int }}% &bull;
        Value {{ (context.evaluation_weights.value * 100)|round|int }}% &bull;
        <strong>Min Warranty:</strong> {{ context.warranty_min_months }} months
      </p>
      {% if context.compliance_notes %}
      <p style="font-size: 14px;"><strong>Compliance Notes:</strong> {{ context.compliance_notes }}</p>
      {% endif %}
      <ul>
        {% for step in analysis.risks_and_next_steps %}
        <li>{{ step }}</li>
        {% endfor %}
      </ul>
    </section>

    <footer>
      Generated by Multi-Agent Procurement Assistant (CrewAI &bull; Tavily Search &bull; ScrapeGraph)
    </footer>
  </div>
</body>
</html>
"""


def strip_markdown_fences(raw_html: str) -> str:
    """Remove surrounding ```html ... ``` fences if an LLM wrapped its HTML output."""
    cleaned = raw_html.strip()
    cleaned = re.sub(r"^```(?:html)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def render_html_report(
    analysis: ProcurementAnalysis,
    context: CompanyContext,
    output_path: str | Path,
) -> Path:
    """Render a standalone HTML procurement report and write it to output_path."""
    env = Environment(loader=BaseLoader(), autoescape=True)
    template = env.from_string(HTML_REPORT_TEMPLATE)
    html_content = template.render(
        analysis=analysis,
        context=context,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html_content, encoding="utf-8")
    return target

