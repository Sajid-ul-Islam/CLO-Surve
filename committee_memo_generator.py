#!/usr/bin/env python3
"""
CLO Committee Memo & Brief Generator
Converts extracted CLO deal data into executive committee memos, refinancing briefs,
and analyst recommendation packages.
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional, List


class CommitteeMemoGenerator:
    """Generates executive CLO committee memo briefs from extracted CLO data."""

    def __init__(self, data: Dict[str, Any]):
        self.data = data

    def generate_markdown_brief(
        self,
        recommendation: str = "Refinance Portfolio",
        target_period: str = "Q1 2027",
        analyst_notes: str = "",
        action_items: Optional[List[str]] = None
    ) -> str:
        """Generate a structured Markdown Committee Executive Brief."""
        d = self.data
        today = datetime.now().strftime("%B %d, %Y")
        
        fund_name = d.get("fund_name", "CLO Portfolio")
        trustee = d.get("trustee", "N/A")
        manager = d.get("portfolio_manager", "N/A")
        report_date = d.get("report_date", "N/A")
        reporting_period = d.get("reporting_period", "N/A")
        closing_date = d.get("closing_date", "N/A")
        init_size = d.get("initial_collateral_size", "N/A")
        size = d.get("current_portfolio_size", 0.0)
        loans = d.get("total_loans", 0)
        wac = d.get("wac", 0.0)
        wal = d.get("wal", 0.0)
        rating = d.get("weighted_avg_rating", "N/A")
        default_rate = d.get("cumulative_default_rate", 0.0)
        default_par = d.get("cumulative_loan_defaults_par", 0.0)
        dpd_30 = d.get("30_plus_dpd", 0.0)
        dpd_60 = d.get("60_plus_dpd", 0.0)
        amort_ytd = d.get("amortization_ytd", 0.0)
        upgrades = d.get("loans_upgraded_12m", 0)
        downgrades = d.get("loans_downgraded_12m", 0)
        net_actions = d.get("rating_actions_net", "N/A")
        compliance = d.get("compliance_status", "Compliant")
        engine_used = d.get("_metadata", {}).get("engine", "AI Agent")

        # Refinancing specifics
        spread_env = d.get("spread_environment", "N/A")
        refi_win = d.get("refinancing_window", target_period)
        refi_cost = d.get("expected_refi_costs", "N/A")
        manager_plan = d.get("manager_intention", "N/A")
        annual_sav = d.get("annual_interest_savings", "N/A")

        actions = action_items or [
            "Monitor healthcare & energy sector obligors for rating migration.",
            "Prepare refinancing syndicate documentation ahead of callability date.",
            "Review asset coverage tests quarterly prior to distribution date."
        ]

        md = []
        md.append(f"# 🏛️ CLO INVESTMENT & SURVEILLANCE COMMITTEE MEMORANDUM")
        md.append(f"**Date:** {today} | **Prepared For:** CLO Investment & Surveillance Committee")
        md.append(f"**Engine Used:** `{str(engine_used).upper()}` | **Report Date:** {report_date}")
        md.append(f"\n---\n")

        md.append(f"## 1. EXECUTIVE SUMMARY & DEAL PROFILE")
        md.append(f"| Parameter | Details | Parameter | Details |")
        md.append(f"|---|---|---|---|")
        md.append(f"| **Fund / Deal Name** | **{fund_name}** | **Portfolio Manager** | {manager} |")
        md.append(f"| **Trustee** | {trustee} | **Closing Date** | {closing_date} |")
        md.append(f"| **Initial Collateral** | ${init_size}M | **Current Portfolio Size** | **${size} Million** |")
        md.append(f"| **Total Obligors / Loans** | {loans} loans | **Compliance Status** | `{compliance}` |")
        md.append(f"\n")

        md.append(f"## 2. PORTFOLIO CREDIT METRICS & RATINGS MIGRATION")
        md.append(f"| Collateral Metric | Value | Risk / Migration Metric | Value |")
        md.append(f"|---|---|---|---|")
        md.append(f"| **Weighted Average Coupon (WAC)** | {wac}% | **Weighted Average Rating** | **{rating}** |")
        md.append(f"| **Weighted Average Life (WAL)** | {wal} years | **Cumulative Default Rate** | {default_rate}% (${default_par}M) |")
        md.append(f"| **30+ Days Past Due** | ${dpd_30}M | **60+ Days Past Due** | ${dpd_60}M |")
        md.append(f"| **Amortization (YTD)** | {amort_ytd}% | **12M Ratings Migration** | +{upgrades} Up / -{downgrades} Down ({net_actions}) |")
        md.append(f"\n")

        # Refinancing Analysis
        md.append(f"## 3. REFINANCING & RESTRUCTURE ASSESSMENT")
        md.append(f"- **Target Refinancing Window:** {refi_win}")
        md.append(f"- **Market Spread Environment:** {spread_env}")
        md.append(f"- **Expected Refinancing Costs:** {refi_cost}")
        md.append(f"- **Estimated Annual Interest Savings:** {annual_sav}")
        md.append(f"- **Manager Strategy & Intention:** {manager_plan}")
        md.append(f"\n")

        # Class Notes Summary Table
        notes = d.get("class_notes", [])
        if notes:
            md.append(f"## 4. CAPITAL STRUCTURE & TRANCHE WATERFALL")
            md.append(f"| Tranche Class | Balance ($M) | Rating | Coupon / Spread | Status / Coverage |")
            md.append(f"|---|---|---|---|---|")
            for n in notes:
                md.append(f"| **Class {n.get('class')}** | ${n.get('balance', 0)}M | {n.get('rating', 'N/A')} | {n.get('coupon', 'N/A')} | {n.get('status', 'OK')} |")
            md.append(f"\n")

        # Sector Breakdown
        sectors = d.get("sector_breakdown", {})
        if sectors:
            md.append(f"## 5. INDUSTRY SECTOR ALLOCATIONS")
            for sector, pct in sectors.items():
                md.append(f"- **{sector}:** {pct}")
            md.append(f"\n")

        # Credit Quality
        cq = d.get("credit_quality", {})
        if cq:
            md.append(f"## 6. CREDIT QUALITY DISTRIBUTION")
            for rk, rv in cq.items():
                md.append(f"- **{rk}:** {rv}")
            md.append(f"\n")

        # Covenants Compliance
        covenants = d.get("covenants", {})
        if covenants:
            md.append(f"## 7. COVENANT COMPLIANCE MATRIX")
            for cov, status in covenants.items():
                md.append(f"- **{cov}:** `{status}`")
            md.append(f"\n")

        # Major Credit Events
        events = d.get("major_credit_events", [])
        if events:
            md.append(f"## 8. MAJOR CREDIT EVENTS & WATCHLIST")
            for evt in events:
                md.append(f"- {evt}")
            md.append(f"\n")

        # Committee Recommendation Section
        md.append(f"## 9. COMMITTEE RECOMMENDATION & ACTION PLAN")
        md.append(f"> [!IMPORTANT]")
        md.append(f"> **Analyst Recommendation:** **{recommendation.upper()}**")
        md.append(f"> **Target Execution Window:** {target_period}")
        if analyst_notes.strip():
            md.append(f">\n> **Analyst Rationale:** {analyst_notes.strip()}")
        md.append(f"\n")

        md.append(f"### Immediate Action Items:")
        for idx, item in enumerate(actions, 1):
            md.append(f"{idx}. {item}")
        md.append(f"\n")

        md.append(f"### Approvals & Signatures:")
        md.append(f"| Role | Name | Signature | Date |")
        md.append(f"|---|---|---|---|")
        md.append(f"| **Lead Credit Analyst** | ____________________ | ____________________ | ________ |")
        md.append(f"| **Head of CLO Surveillance** | ____________________ | ____________________ | ________ |")
        md.append(f"| **Committee Chair** | ____________________ | ____________________ | ________ |")
        md.append(f"\n")

        return "\n".join(md)

    def generate_text_brief(
        self,
        recommendation: str = "Refinance Portfolio",
        target_period: str = "Q1 2027",
        analyst_notes: str = ""
    ) -> str:
        """Generate plain text summary for fast emailing/pasting."""
        d = self.data
        lines = []
        lines.append("==============================================================")
        lines.append(f"CLO COMMITTEE MEMORANDUM — {d.get('fund_name', 'CLO Portfolio')}")
        lines.append("==============================================================")
        lines.append(f"Report Date: {d.get('report_date', 'N/A')} | Manager: {d.get('portfolio_manager', 'N/A')}")
        lines.append(f"Trustee: {d.get('trustee', 'N/A')} | Closing Date: {d.get('closing_date', 'N/A')}")
        lines.append(f"Portfolio Size: ${d.get('current_portfolio_size', 0.0)}M ({d.get('total_loans', 0)} loans)")
        lines.append(f"WAC: {d.get('wac', 0.0)}% | WAL: {d.get('wal', 0.0)} yrs | WAR: {d.get('weighted_avg_rating', 'N/A')}")
        lines.append(f"Default Rate: {d.get('cumulative_default_rate', 0.0)}% | 30+ DPD: ${d.get('30_plus_dpd', 0.0)}M")
        lines.append(f"Compliance: {d.get('compliance_status', 'Compliant')}")
        lines.append("--------------------------------------------------------------")
        lines.append("REFINANCING & RESTRUCTURE ASSESSMENT:")
        lines.append(f"Refi Window: {d.get('refinancing_window', target_period)}")
        lines.append(f"Expected Refi Costs: {d.get('expected_refi_costs', 'N/A')}")
        lines.append(f"Estimated Annual Savings: {d.get('annual_interest_savings', 'N/A')}")
        lines.append(f"Manager Plan: {d.get('manager_intention', 'N/A')}")
        lines.append("--------------------------------------------------------------")
        lines.append(f"ANALYST RECOMMENDATION: {recommendation.upper()} (Target: {target_period})")
        if analyst_notes:
            lines.append(f"Rationale: {analyst_notes}")
        lines.append("==============================================================")
        return "\n".join(lines)

    def generate_html_brief(
        self,
        recommendation: str = "Refinance Portfolio",
        target_period: str = "Q1 2027",
        analyst_notes: str = "",
        action_items: Optional[List[str]] = None
    ) -> str:
        """Generate styled HTML Printable Brief document."""
        d = self.data
        today = datetime.now().strftime("%B %d, %Y")
        actions = action_items or ["Review portfolio sector concentrations", "Prepare refinancing syndicate terms"]

        actions_html = "".join([f"<li>{act}</li>" for act in actions])
        
        notes_rows = ""
        for n in d.get("class_notes", []):
            notes_rows += f"""<tr>
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">Class {n.get('class')}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">${n.get('balance', 0)}M</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{n.get('rating', 'N/A')}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{n.get('coupon', 'N/A')}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{n.get('status', 'OK')}</td>
            </tr>"""

        covs_html = ""
        for cov, status in d.get("covenants", {}).items():
            covs_html += f"<li><strong>{cov}:</strong> {status}</li>"

        events_html = ""
        for evt in d.get("major_credit_events", []):
            events_html += f"<li>{evt}</li>"

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"/>
    <title>CLO Committee Brief - {d.get('fund_name', 'CLO')}</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #1a1a1a; margin: 30px; }}
        .header {{ border-bottom: 3px solid #1E88E5; padding-bottom: 10px; margin-bottom: 20px; }}
        .title {{ font-size: 24px; color: #0D47A1; margin: 0; }}
        .subtitle {{ font-size: 14px; color: #666; margin-top: 5px; }}
        .badge {{ background: #E3F2FD; color: #1565C0; padding: 4px 12px; border-radius: 4px; font-weight: bold; font-size: 12px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th {{ background: #F5F5F5; text-align: left; padding: 8px; border: 1px solid #ddd; font-weight: 600; }}
        td {{ padding: 8px; border: 1px solid #ddd; }}
        .rec-box {{ background: #F1F8E9; border-left: 5px solid #4CAF50; padding: 15px; margin: 20px 0; }}
        .refi-box {{ background: #E8EAF6; border-left: 5px solid #3F51B5; padding: 15px; margin: 20px 0; }}
        @media print {{
            body {{ margin: 15mm; }}
            .no-print {{ display: none; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1 class="title">🏛️ CLO INVESTMENT & SURVEILLANCE COMMITTEE MEMORANDUM</h1>
        <div class="subtitle">Date: {today} | Deal: <strong>{d.get('fund_name', 'CLO Deal')}</strong> | Report Date: {d.get('report_date', 'N/A')}</div>
    </div>

    <h2>1. Executive Summary & Deal Profile</h2>
    <table>
        <tr><th>Manager</th><td>{d.get('portfolio_manager', 'N/A')}</td><th>Trustee</th><td>{d.get('trustee', 'N/A')}</td></tr>
        <tr><th>Portfolio Size</th><td>${d.get('current_portfolio_size', 0)}M</td><th>Loans Count</th><td>{d.get('total_loans', 0)}</td></tr>
        <tr><th>WAC</th><td>{d.get('wac', 0)}%</td><th>WAL</th><td>{d.get('wal', 0)} years</td></tr>
        <tr><th>Weighted Avg Rating</th><td><strong>{d.get('weighted_avg_rating', 'N/A')}</strong></td><th>Default Rate</th><td>{d.get('cumulative_default_rate', 0)}%</td></tr>
        <tr><th>30+ DPD</th><td>${d.get('30_plus_dpd', 0)}M</td><th>Compliance</th><td><span class="badge">{d.get('compliance_status', 'OK')}</span></td></tr>
    </table>

    <div class="refi-box">
        <h3 style="margin-top:0; color:#1A237E;">Refinancing & Restructuring Assessment</h3>
        <p><strong>Refinancing Window:</strong> {d.get('refinancing_window', target_period)}</p>
        <p><strong>Expected Refi Costs:</strong> {d.get('expected_refi_costs', 'N/A')} | <strong>Annual Savings:</strong> {d.get('annual_interest_savings', 'N/A')}</p>
        <p><strong>Spread Environment:</strong> {d.get('spread_environment', 'N/A')}</p>
        <p><strong>Manager Plan:</strong> {d.get('manager_intention', 'N/A')}</p>
    </div>

    <h2>2. Capital Structure & Tranche Waterfall</h2>
    <table>
        <tr><th>Tranche</th><th>Balance</th><th>Rating</th><th>Coupon / Spread</th><th>Status / Coverage</th></tr>
        {notes_rows}
    </table>

    <h2>3. Covenant Compliance Matrix</h2>
    <ul>{covs_html}</ul>

    <h2>4. Major Credit Events & Watchlist</h2>
    <ul>{events_html}</ul>

    <div class="rec-box">
        <h3 style="margin-top:0; color:#2E7D32;">ANALYST RECOMMENDATION: {recommendation.upper()}</h3>
        <p><strong>Target Execution Window:</strong> {target_period}</p>
        <p><strong>Analyst Rationale:</strong> {analyst_notes}</p>
    </div>

    <h2>5. Action Items Checklist</h2>
    <ul>{actions_html}</ul>

    <br/>
    <h2>6. Committee Approvals</h2>
    <table>
        <tr><th>Role</th><th>Name</th><th>Signature</th><th>Date</th></tr>
        <tr><td>Lead Credit Analyst</td><td>_______________________</td><td>_______________________</td><td>________</td></tr>
        <tr><td>Head of CLO Surveillance</td><td>_______________________</td><td>_______________________</td><td>________</td></tr>
        <tr><td>Committee Chair</td><td>_______________________</td><td>_______________________</td><td>________</td></tr>
    </table>
</body>
</html>"""
        return html

