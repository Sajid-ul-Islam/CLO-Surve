#!/usr/bin/env python3
"""
Offline Rule-Based CLO Memo Extractor
Parses surveillance & refinancing memos using regex, layout heuristics, and rule-based logic.
Operates 100% offline without requiring LLM API calls or internet connectivity.
"""

import re
from datetime import datetime
from typing import Dict, Any, List, Optional


class OfflineCLOExtractor:
    """Deterministic rule-based extractor for CLO surveillance & refinancing memos."""

    def __init__(self):
        pass

    def extract(self, memo_text: str) -> Dict[str, Any]:
        """Extract structured data dictionary from raw text memo."""
        text = memo_text.strip()

        # Deal Overview & Metadata
        fund_name = self._extract_regex(
            text, [r"Fund\s+Name:\s*(.+)", r"Deal\s+Name:\s*(.+)", r"Issuer:\s*(.+)"], "Unknown Fund"
        )
        trustee = self._extract_regex(
            text, [r"Trustee:\s*(.+)", r"Issuer\s+Trustee:\s*(.+)"], "Unknown Trustee"
        )
        report_date = self._extract_regex(
            text, [r"Report\s+Date:\s*(.+)", r"As\s+of\s+Date:\s*(.+)", r"Date:\s*(.+)"], "N/A"
        )
        reporting_period = self._extract_regex(
            text, [r"Reporting\s+Period:\s*(.+)", r"Period:\s*(.+)"], "N/A"
        )
        portfolio_manager = self._extract_regex(
            text, [r"Portfolio\s+Manager:\s*(.+)", r"Collateral\s+Manager:\s*(.+)", r"Manager:\s*(.+)"], "N/A"
        )
        closing_date = self._extract_regex(
            text, [r"Closing\s+Date:\s*(.+)", r"Inception\s+Date:\s*(.+)"], "N/A"
        )
        initial_collateral_size = self._extract_currency_millions(
            text, [r"Initial\s+Collateral\s+Size:\s*\$?([\d,]+(?:\.\d+)?)", r"Initial\s+Par:\s*\$?([\d,]+(?:\.\d+)?)"]
        )
        current_portfolio_size = self._extract_currency_millions(
            text, [
                r"Current\s+Portfolio\s+Size:\s*\$?([\d,]+(?:\.\d+)?)",
                r"Total\s+Par\s+Outstanding:\s*\$?([\d,]+(?:\.\d+)?)",
                r"Collateral\s+Balance:\s*\$?([\d,]+(?:\.\d+)?)"
            ]
        )
        total_loans = self._extract_int(
            text, [r"Total\s+Number\s+of\s+Loans:\s*(\d+)", r"Loan\s+Count:\s*(\d+)", r"Number\s+of\s+Obligors:\s*(\d+)"]
        )
        wac = self._extract_float(
            text, [r"Weighted\s+Average\s+Coupon\s*\(WAC\):\s*([\d\.]+)%?", r"WAC:\s*([\d\.]+)%?"]
        )
        wal = self._extract_float(
            text, [r"Weighted\s+Average\s+Life\s*\(WAL\):\s*([\d\.]+)", r"WAL:\s*([\d\.]+)\s*years?"]
        )
        weighted_avg_rating = self._extract_rating(
            text, [r"Weighted\s+Average\s+Rating:\s*([A-Za-z0-9\+\-]+)", r"WARF\s+Equivalent:\s*([A-Za-z0-9\+\-]+)"]
        )

        # Performance & Delinquency Metrics
        cumulative_default_rate = self._extract_float(
            text, [
                r"Cumulative\s+Default\s+Rate:\s*([\d\.]+)%?",
                r"Cumulative\s+Loan\s+Defaults.*?\(([\d\.]+)%\)"
            ]
        )
        cumulative_loan_defaults_par = self._extract_currency_millions(
            text, [r"Cumulative\s+Loan\s+Defaults\s*\(Par\):\s*\$?([\d,]+(?:\.\d+)?)", r"Defaulted\s+Par:\s*\$?([\d,]+(?:\.\d+)?)"]
        )
        dpd_30 = self._extract_currency_millions(
            text, [r"30\+\s+Days\s+Past\s+Due:\s*\$?([\d,]+(?:\.\d+)?)", r"30\+\s+DPD:\s*\$?([\d,]+(?:\.\d+)?)"]
        )
        dpd_60 = self._extract_currency_millions(
            text, [r"60\+\s+Days\s+Past\s+Due:\s*\$?([\d,]+(?:\.\d+)?)", r"60\+\s+DPD:\s*\$?([\d,]+(?:\.\d+)?)"]
        )
        total_defaulted_loans = self._extract_int(
            text, [r"Total\s+Defaulted\s+Loans:\s*(\d+)", r"Defaulted\s+Obligors:\s*(\d+)"]
        )
        loans_paid_off = self._extract_int(
            text, [r"Total\s+Loans\s+Paid\s+Off:\s*(\d+)", r"Loans\s+Paid\s+Off:\s*(\d+)", r"Prepaid\s+Loans:\s*(\d+)"]
        )
        amortization_ytd = self._extract_float(
            text, [r"Scheduled\s+Amortization:\s*([\d\.]+)%?\s*YTD", r"Amortization\s+YTD:\s*([\d\.]+)%?", r"Scheduled\s+Amortization:\s*([\d\.]+)%?"]
        )

        # Ratings Migration
        loans_upgraded_12m = self._extract_int(
            text, [r"Loans\s+Upgraded:\s*(\d+)", r"Upgrades\s*\(12M\):\s*(\d+)"]
        )
        loans_downgraded_12m = self._extract_int(
            text, [r"Loans\s+Downgraded:\s*(\d+)", r"Downgrades\s*\(12M\):\s*(\d+)"]
        )
        rating_actions_net = self._extract_regex(
            text, [r"Rating\s+Actions\s+Net:\s*(.+)", r"Net\s+Rating\s+Migration:\s*(.+)"], "N/A"
        )

        # Refinancing Specific Metrics
        spread_environment = self._extract_regex(
            text, [r"Current\s+Spread\s+Environment:\s*(.+)", r"Spread\s+Environment:\s*(.+)"], "N/A"
        )
        refinancing_window = self._extract_regex(
            text, [r"Refinancing\s+Window:\s*(.+)", r"Refi\s+Target\s+Date:\s*(.+)", r"Refinancing\s+Target:\s*(.+)"], "N/A"
        )
        expected_refi_costs = self._extract_regex(
            text, [r"Expected\s+Refi\s+Costs:\s*(.+)", r"Refinancing\s+Costs:\s*(.+)"], "N/A"
        )
        manager_intention = self._extract_regex(
            text, [r"Manager\s+Intention:\s*(.+)", r"Refinancing\s+Plan:\s*(.+)"], "N/A"
        )
        annual_interest_savings = self._extract_regex(
            text, [r"Estimated\s+Annual\s+Interest\s+Savings:\s*(.+)", r"Annual\s+Savings:\s*(.+)"], "N/A"
        )

        # Structured Sub-Tables
        sector_breakdown = self._parse_sector_breakdown(text)
        credit_quality = self._parse_credit_quality(text)
        class_notes = self._parse_class_notes(text)
        covenants = self._parse_covenants(text)
        major_credit_events = self._parse_credit_events(text)
        compliance_status = self._extract_compliance_status(text)

        result = {
            "fund_name": fund_name,
            "trustee": trustee,
            "report_date": report_date,
            "reporting_period": reporting_period,
            "portfolio_manager": portfolio_manager,
            "closing_date": closing_date,
            "initial_collateral_size": initial_collateral_size,
            "current_portfolio_size": current_portfolio_size,
            "total_loans": total_loans,
            "wac": wac,
            "wal": wal,
            "weighted_avg_rating": weighted_avg_rating,
            "cumulative_default_rate": cumulative_default_rate,
            "cumulative_loan_defaults_par": cumulative_loan_defaults_par,
            "30_plus_dpd": dpd_30,
            "60_plus_dpd": dpd_60,
            "total_defaulted_loans": total_defaulted_loans,
            "loans_paid_off": loans_paid_off,
            "amortization_ytd": amortization_ytd,
            "loans_upgraded_12m": loans_upgraded_12m,
            "loans_downgraded_12m": loans_downgraded_12m,
            "rating_actions_net": rating_actions_net,
            "spread_environment": spread_environment,
            "refinancing_window": refinancing_window,
            "expected_refi_costs": expected_refi_costs,
            "manager_intention": manager_intention,
            "annual_interest_savings": annual_interest_savings,
            "sector_breakdown": sector_breakdown,
            "credit_quality": credit_quality,
            "class_notes": class_notes,
            "covenants": covenants,
            "major_credit_events": major_credit_events,
            "compliance_status": compliance_status,
            "_metadata": {
                "engine": "offline_rule_based",
                "extracted_at": datetime.now().isoformat()
            }
        }
        return result

    def _extract_regex(self, text: str, patterns: List[str], default: Any = None) -> Any:
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                val = match.group(1).strip()
                # Strip multi-hyphens/equals from headers or section dividers, but preserve single hyphens in names
                val = re.sub(r"[\=\-]{2,}$", "", val).strip()
                val = re.sub(r"\s+[\=\-]+$", "", val).strip()
                if val:
                    return val
        return default

    def _extract_rating(self, text: str, patterns: List[str], default: str = "N/A") -> str:
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                val = match.group(1).strip()
                # Clean up any trailing dividers without stripping minus sign from BBB- or BB-
                val = re.sub(r"[\=\-]{2,}$", "", val).strip()
                if val:
                    return val
        return default

    def _extract_int(self, text: str, patterns: List[str], default: int = 0) -> int:
        res = self._extract_regex(text, patterns)
        if res:
            try:
                cleaned = re.sub(r"[^\d]", "", str(res))
                return int(cleaned) if cleaned else default
            except ValueError:
                pass
        return default

    def _extract_float(self, text: str, patterns: List[str], default: float = 0.0) -> float:
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1).replace(",", ""))
                except ValueError:
                    pass
        return default

    def _extract_currency_millions(self, text: str, patterns: List[str]) -> float:
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                raw_str = match.group(1).replace(",", "")
                try:
                    val = float(raw_str)
                    if val > 100000:
                        val = round(val / 1000000.0, 2)
                    return val
                except ValueError:
                    pass
        return 0.0

    def _parse_sector_breakdown(self, text: str) -> Dict[str, str]:
        sectors = {}
        sec_match = re.search(r"SECTOR\s+BREAKDOWN:?(.*?)(?=\n\n|\n[A-Z0-9\s]{4,}=+|\n[A-Z\s]{4,}:|$)", text, re.DOTALL | re.IGNORECASE)
        target_text = sec_match.group(1) if sec_match else text

        matches = re.findall(r"[-•\*]?\s*([A-Za-z0-9\s/&]+):\s*([\d\.]+%?(?:\s*\(\$[\d\.]+[MB]\))?)", target_text)
        for name, pct in matches:
            clean_name = name.strip()
            if len(clean_name) > 2 and not clean_name.lower().startswith("section") and not clean_name.lower().startswith("loan in"):
                sectors[clean_name] = pct.strip()

        return sectors

    def _parse_credit_quality(self, text: str) -> Dict[str, str]:
        cq = {}
        cq_match = re.search(r"CREDIT\s+QUALITY\s+DISTRIBUTION:?(.*?)(?=\n\n|\n[A-Z0-9\s]{4,}=+|\n[A-Z\s]{4,}:|$)", text, re.DOTALL | re.IGNORECASE)
        target_text = cq_match.group(1) if cq_match else text

        # Match lines like "AAA: 2.1% ($25M)" or "- CCC and below: 1.7% ($20M)"
        matches = re.findall(r"[-•\*]?\s*(CCC\s+and\s+below|AAA|AA|A|BBB|BB|B|CCC|CC|C|D):\s*([\d\.]+%?(?:\s*\(\$[\d\.]+[MB]\))?)", target_text, re.IGNORECASE)
        for rating, pct in matches:
            clean_rating = rating.strip()
            if clean_rating not in cq:
                cq[clean_rating] = pct.strip()

        return cq

    def _parse_class_notes(self, text: str) -> List[Dict[str, Any]]:
        notes = []
        # Target the CLASS NOTES section specifically
        section_match = re.search(
            r"CLASS\s+NOTES(?:\s+SUMMARY)?[^\n]*\n(?:[=\-\s]+\n)?(.*?)(?=\n\s*[A-Z0-9\s]{4,}\s*\n\s*[=\-]{3,}|\n\s*(?:COVENANT|MARKET|NOTABLE|RECOMMENDATION|NEXT\s+STEPS)\b|$)",
            text,
            re.DOTALL | re.IGNORECASE
        )
        target_text = section_match.group(1) if section_match else text

        # Match blocks that start with "Class <X>" at the start of a line
        raw_blocks = re.split(r"(?=(?:^|\n)\s*Class\s+[A-Z0-9\-]+)", target_text, flags=re.IGNORECASE)

        for block in raw_blocks:
            block = block.strip()
            if not block or not block.lower().startswith("class"):
                continue

            lines = [l.strip() for l in block.splitlines() if l.strip()]
            if not lines:
                continue

            header = lines[0]
            # Match class identifier (e.g. Class A-1, Class A-2, Class B, Class C)
            cls_name_match = re.search(r"Class\s+([A-Z0-9\-]+(?:\s+[A-Za-z0-9\s]+)?)", header, re.IGNORECASE)
            full_header_name = cls_name_match.group(1) if cls_name_match else header

            # Clean short class code (e.g. A-1, A-2, B, C)
            short_code_match = re.search(r"([A-Z0-9\-]+)", full_header_name)
            cls_code = short_code_match.group(1) if short_code_match else full_header_name

            coupon = self._extract_regex(
                block, [r"Coupon:\s*(.+)", r"Spread:\s*(.+)", r"Current\s+Yield[^\:]*:\s*(.+)", r"Yield:\s*(.+)"], "Equity" if "equity" in header.lower() else "N/A"
            )
            rating = self._extract_rating(block, [r"Rating:\s*([A-Za-z0-9+\-]+)"], "NR" if "equity" in header.lower() else "N/A")
            balance = self._extract_currency_millions(block, [r"Balance\s+(?:Outstanding)?:\s*\$?([\d,]+(?:\.\d+)?)"])
            
            # Status / Coverage
            status = "Performing"
            ic_match = re.search(r"Interest\s+Coverage:\s*([\d\.]+x?)", block, re.IGNORECASE)
            val_match = re.search(r"Value:\s*(.+)", block, re.IGNORECASE)
            yield_match = re.search(r"Current\s+Yield[^\:]*:\s*(.+)", block, re.IGNORECASE)

            if ic_match:
                status = f"Compliant (IC: {ic_match.group(1)})"
            elif yield_match:
                status = f"Yield: {yield_match.group(1)}"
            elif val_match:
                status = f"Value: {val_match.group(1)}"

            notes.append({
                "class": cls_code,
                "description": header,
                "coupon": coupon,
                "balance": balance,
                "rating": rating,
                "status": status
            })

        return notes

    def _parse_covenants(self, text: str) -> Dict[str, str]:
        covenants = {}
        cov_match = re.search(r"COVENANT\s+COMPLIANCE:?(.*?)(?=\n\n|\n[A-Z0-9\s]{4,}=+|\n[A-Z\s]{4,}:|$)", text, re.DOTALL | re.IGNORECASE)
        target_text = cov_match.group(1) if cov_match else text

        matches = re.findall(r"([A-Za-z0-9\s\-\(\)]+):\s*([\d\.]+%?|\d\.\d+x)\s*\((Required:[^\)]+)\)", target_text)
        for cov_name, val, req in matches:
            clean_name = cov_name.strip()
            if len(clean_name) > 3:
                covenants[clean_name] = f"{val} ({req})"

        return covenants

    def _parse_credit_events(self, text: str) -> List[str]:
        events = []
        evt_match = re.search(
            r"(?:NOTABLE\s+CREDIT\s+EVENTS|MAJOR\s+CREDIT\s+EVENTS|CREDIT\s+EVENTS):?(.*?)(?=\n[A-Z0-9\s]{4,}=+|\nNEXT\s+STEPS|\nRECOMMENDATION|$)",
            text,
            re.DOTALL | re.IGNORECASE
        )
        target_text = evt_match.group(1) if evt_match else text

        matches = re.findall(r"[-•\*]\s*(.+)", target_text)
        for m in matches:
            clean_event = m.strip()
            if clean_event and len(clean_event) > 4:
                events.append(clean_event)

        return events

    def _extract_compliance_status(self, text: str) -> str:
        if re.search(r"All\s+covenants\s+(?:remain\s+in|in\s+full)\s+compliance", text, re.IGNORECASE):
            return "All covenants in compliance. No trigger events."
        if re.search(r"covenant\s+breach", text, re.IGNORECASE):
            return "Covenant Breach Detected - Review Details"
        return "Compliant - Standard Surveillance"

