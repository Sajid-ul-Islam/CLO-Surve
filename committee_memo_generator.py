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
        recommendation: str = "Refinance",
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
        closing_date = d.get("closing_date", "N/A")
        size = d.get("current_portfolio_size", 0.0)
        loans = d.get("total_loans", 0)
        wac = d.get("wac", 0.0)
        wal = d.get("wal", 0.0)
        rating = d.get("weighted_avg_rating", "N/A")
        default_rate = d.get("cumulative_default_rate", 0.0)
        dpd_30 = d.get("30_plus_dpd", 0.0)
        dpd_60 = d.get("60_plus_dpd", 0.0)
        compliance = d.get("compliance_status", "Compliant")
        engine_used = d.get("_metadata", {}).get("engine", "AI Agent")

        actions = action_items or [
            "Monitor healthcare & energy sector obligors for rating migration.",
            "Prepare refinancing syndicate documentation ahead of callability date.",
            "Review asset coverage tests quarterly prior to distribution date."
        ]

        md = []
        md.append(f"# 🏛️ CLO INVESTMENT COMMITTEE MEMORANDUM")
        md.append(f"**Date:** {today} | **Prepared For:** CLO Investment & Surveillance Committee")
        md.append(f"**Engine Used:** `{engine_used.upper()}`")
        md.append(f"\n---\n")

        md.append(f"## 1. EXECUTIVE SUMMARY & DEAL PROFILE")
        md.append(f"| Parameter | Details |")
        md.append(f"|---|---|")
        md.append(f"| **Fund / Deal Name** | **{fund_name}** |")
        md.append(f"| **Portfolio Manager** | {manager} |")
        md.append(f"| **Trustee** | {trustee} |")
        md.append(f"| **Closing Date** | {closing_date} |")
        md.append(f"| **Report Date** | {report_date} |")
        md.append(f"| **Current Portfolio Size** | **${size} Million** ({loans} loans) |")
        md.append(f"| **Compliance Status** | `{compliance}` |")
        md.append(f"\n")

        md.append(f"## 2. PORTFOLIO & CREDIT RISK AUDIT")
        md.append(f"- **Weighted Average Coupon (WAC):** {wac}%")
        md.append(f"- **Weighted Average Life (WAL):** {wal} years")
        md.append(f"- **Weighted Average Rating:** {rating}")
        md.append(f"- **Cumulative Default Rate:** {default_rate}%")
        md.append(f"- **30+ Days Past Due:** ${dpd_30}M")
        md.append(f"- **60+ Days Past Due:** ${dpd_60}M")
        md.append(f"\n")

        # Class Notes Summary Table
        notes = d.get("class_notes", [])
        if notes:
            md.append(f"### Debt & Equity Tranche Overview")
            md.append(f"| Class | Balance ($M) | Rating | Coupon / Spread | Status / Coverage |")
            md.append(f"|---|---|---|---|---|")
            for n in notes:
                md.append(f"| **{n.get('class')}** | ${n.get('balance', 0)}M | {n.get('rating', 'N/A')} | {n.get('coupon', 'N/A')} | {n.get('status', 'OK')} |")
            md.append(f"\n")

        # Sector Breakdown
        sectors = d.get("sector_breakdown", {})
        if sectors:
            md.append(f"### Industry Sector Distribution")
            for sector, pct in sectors.items():
                md.append(f"- **{sector}:** {pct}")
            md.append(f"\n")

        # Covenants Compliance
        covenants = d.get("covenants", {})
        if covenants:
            md.append(f"### Covenant Compliance Summary")
            for cov, status in covenants.items():
                md.append(f"- **{cov}:** {status}")
            md.append(f"\n")

        # Major Credit Events
        events = d.get("major_credit_events", [])
        if events:
            md.append(f"### Major Credit & Portfolio Events")
            for evt in events:
                md.append(f"- {evt}")
            md.append(f"\n")

        # Committee Recommendation Section
        md.append(f"## 3. COMMITTEE RECOMMENDATION & ACTION PLAN")
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

        return "\n".join(md)

    def generate_text_brief(
        self,
        recommendation: str = "Refinance",
        target_period: str = "Q1 2027",
        analyst_notes: str = ""
    ) -> str:
        """Generate plain text summary for fast emailing/pasting."""
        d = self.data
        lines = []
        lines.append("==============================================================")
        lines.append(f"CLO COMMITTEE MEMORANDUM — {d.get('fund_name', 'CLO Portfolio')}")
        lines.append("==============================================================")
        lines.append(f"Report Date: {d.get('report_date', 'N/A')}")
        lines.append(f"Manager: {d.get('portfolio_manager', 'N/A')}")
        lines.append(f"Trustee: {d.get('trustee', 'N/A')}")
        lines.append(f"Portfolio Size: ${d.get('current_portfolio_size', 0.0)}M ({d.get('total_loans', 0)} loans)")
        lines.append(f"WAC: {d.get('wac', 0.0)}% | WAL: {d.get('wal', 0.0)} yrs | Rating: {d.get('weighted_avg_rating', 'N/A')}")
        lines.append(f"Default Rate: {d.get('cumulative_default_rate', 0.0)}% | 30+ DPD: ${d.get('30_plus_dpd', 0.0)}M")
        lines.append(f"Compliance Status: {d.get('compliance_status', 'Compliant')}")
        lines.append("--------------------------------------------------------------")
        lines.append(f"RECOMMENDATION: {recommendation.upper()} (Target: {target_period})")
        if analyst_notes:
            lines.append(f"Rationale: {analyst_notes}")
        lines.append("==============================================================")
        return "\n".join(lines)
