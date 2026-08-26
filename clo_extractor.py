#!/usr/bin/env python3
"""
CLO Surveillance Memo Extraction Agent
Extracts structured data from CLO surveillance/refi memos using an LLM API.

Provider: OpenRouter (OpenAI-compatible chat completions).
Default model: stealth/ox-alpha
"""

import json
import os
import sys
from datetime import datetime
from openai import OpenAI

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from offline_extractor import OfflineCLOExtractor

# Try to import pandas and openpyxl for Excel output (optional)
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    print("[WARNING] pandas not found. JSON output only. Install: pip install pandas openpyxl")


# Provider registry: each entry maps to (env_var, default_model, base_url)
PROVIDERS = {
    "openrouter": {
        "env": "OPENROUTER_API_KEY",
        "default_model": "z-ai/glm-5.3-flash",
        "base_url": "https://openrouter.ai/api/v1",
    },
    "gemini": {
        "env": "GEMINI_API_KEY",
        "default_model": "gemini-2.5-flash",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
    },
    "groq": {
        "env": "GROQ_API_KEY",
        "default_model": "qwen/qwen3.8-27b",
        "base_url": "https://api.groq.com/openai/v1",
    },
    "offline": {
        "env": None,
        "default_model": "rule-based-engine",
        "base_url": None,
    },
}


class CLOExtractor:
    def __init__(
        self,
        api_key: str = None,
        model: str = None,
        provider: str = "openrouter",
        base_url: str = None,
        allow_fallback: bool = True,
    ):
        """
        Initialize extractor client for chosen provider.
        provider: 'openrouter' | 'gemini' | 'groq' | 'offline'
        """
        if provider not in PROVIDERS:
            raise ValueError(
                f"Unknown provider '{provider}'. Choose from: {list(PROVIDERS)}"
            )
        cfg = PROVIDERS[provider]
        self.provider = provider
        self.allow_fallback = allow_fallback
        self.model = model or cfg["default_model"]
        self.base_url = base_url or cfg["base_url"]
        self.client = None

        if provider == "offline":
            self.api_key = "OFFLINE_RULE_BASED"
        else:
            self.api_key = api_key or os.getenv(cfg["env"])
            if not self.api_key:
                if allow_fallback:
                    print(f"[INFO] No API key found for '{provider}'. Falling back to offline rule-based engine.")
                    self.provider = "offline"
                    self.api_key = "OFFLINE_RULE_BASED"
                else:
                    raise ValueError(
                        f"No API key found for provider '{provider}'. "
                        f"Set {cfg['env']} or pass api_key=..."
                    )
            else:
                self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def read_memo(self, file_path: str) -> str:
        """Read memo from file (txt, pdf text, etc.)"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    def extract_data(self, memo_text: str) -> dict:
        """
        Extract structured data from memo using chosen provider or offline fallback.
        Returns a dict with all extracted fields.
        """
        if self.provider == "offline" or not self.client:
            print("[INFO] Running offline rule-based extraction engine...")
            return OfflineCLOExtractor().extract(memo_text)

        extraction_prompt = f"""You are a financial analyst specializing in CLO (Collateralized Loan Obligation) analysis.

Extract ALL the following data from the CLO memo below. Return ONLY valid JSON, no markdown formatting.

REQUIRED FIELDS (extract exactly these):
{{
  "fund_name": "string",
  "trustee": "string",
  "report_date": "YYYY-MM-DD",
  "reporting_period": "string",
  "portfolio_manager": "string",
  "closing_date": "YYYY-MM-DD",
  "initial_collateral_size": "number (in millions)",
  "current_portfolio_size": "number (in millions)",
  "total_loans": "number",
  "wac": "number (weighted average coupon, %)",
  "wal": "number (weighted average life, years)",
  "weighted_avg_rating": "string",
  "cumulative_default_rate": "number (%)",
  "cumulative_loan_defaults_par": "number ($ millions)",
  "30_plus_dpd": "number ($ millions)",
  "60_plus_dpd": "number ($ millions)",
  "total_defaulted_loans": "number",
  "loans_paid_off": "number",
  "amortization_ytd": "number (%)",
  "loans_upgraded_12m": "number",
  "loans_downgraded_12m": "number",
  "rating_actions_net": "string",
  "spread_environment": "string",
  "refinancing_window": "string or date",
  "expected_refi_costs": "string or number",
  "manager_intention": "string",
  "annual_interest_savings": "string or number",
  "sector_breakdown": {{
    "sector_name": "percentage or amount"
  }},
  "credit_quality": {{
    "rating_bucket": "percentage or $ amount"
  }},
  "class_notes": [
    {{
      "class": "string (A-1, A-2, B, C, etc.)",
      "description": "full class title",
      "coupon": "string",
      "balance": "number ($ millions)",
      "rating": "string",
      "status": "string"
    }}
  ],
  "covenants": {{
    "covenant_name": "value with requirement"
  }},
  "major_credit_events": [
    "event description"
  ],
  "compliance_status": "string (all covenants compliant or list any breaches)"
}}

Memo text:
---
{memo_text}
---

Return ONLY the JSON object, no other text."""

        try:
            message = self.client.chat.completions.create(
                model=self.model,
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": extraction_prompt,
                    }
                ],
            )

            # Extract JSON from response
            response_text = message.choices[0].message.content
            if not response_text:
                raise ValueError(
                    "Model returned an empty response (finish_reason="
                    f"{getattr(message.choices[0], 'finish_reason', '?')}). "
                    "Try a smaller memo or a model with a larger output limit."
                )

            # Try to parse as JSON (strip a possible ```json ... ``` fence)
            extracted_data = self._parse_json(response_text)
            if extracted_data and isinstance(extracted_data, dict):
                extracted_data["_metadata"] = {
                    "engine": f"{self.provider}:{self.model}",
                    "extracted_at": datetime.now().isoformat()
                }
            return extracted_data

        except Exception as e:
            print(f"[WARNING] LLM extraction failed ({self.provider}:{self.model}): {e}")
            if self.allow_fallback:
                print("[INFO] Falling back to offline rule-based extraction engine...")
                fallback_data = OfflineCLOExtractor().extract(memo_text)
                fallback_data["_metadata"] = {
                    "engine": "rule_based_fallback",
                    "error": str(e),
                    "extracted_at": datetime.now().isoformat()
                }
                return fallback_data
            return None

    @staticmethod
    def _parse_json(text: str):
        text = text.strip()
        # Strip markdown code fences if present: ```json ... ``` or ``` ... ```
        if text.startswith("```"):
            # remove leading fence
            text = text.split("```", 2)[1]
            if text.lower().startswith("json"):
                text = text[4:]
            text = text.strip()
            if text.endswith("```"):
                text = text[:-3].strip()
        return json.loads(text)

    def save_json(self, data: dict, output_path: str):
        """Save extracted data to JSON file"""
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"[OK] JSON saved: {output_path}")

    def save_excel(self, data: dict, output_path: str):
        """Save extracted data to Excel workbook with multiple sheets"""
        if not HAS_PANDAS:
            print("[WARNING] Skipping Excel export (pandas not installed)")
            return

        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:

            # Sheet 1: Summary
            summary_data = {
                'Metric': [
                    'Fund Name', 'Trustee', 'Portfolio Manager', 'Report Date',
                    'Reporting Period', 'Closing Date', 'Initial Collateral ($M)',
                    'Current Portfolio Size ($M)', 'Total Loans', 'WAC (%)',
                    'WAL (years)', 'Weighted Avg Rating', 'Cumulative Default Rate (%)',
                    'Cumulative Default Par ($M)', '30+ DPD ($M)', '60+ DPD ($M)',
                    'Defaulted Loans Count', 'Loans Paid Off', 'Amortization YTD (%)',
                    '12M Upgrades', '12M Downgrades', 'Compliance Status'
                ],
                'Value': [
                    data.get('fund_name', 'N/A'),
                    data.get('trustee', 'N/A'),
                    data.get('portfolio_manager', 'N/A'),
                    data.get('report_date', 'N/A'),
                    data.get('reporting_period', 'N/A'),
                    data.get('closing_date', 'N/A'),
                    data.get('initial_collateral_size', 'N/A'),
                    data.get('current_portfolio_size', 'N/A'),
                    data.get('total_loans', 'N/A'),
                    data.get('wac', 'N/A'),
                    data.get('wal', 'N/A'),
                    data.get('weighted_avg_rating', 'N/A'),
                    data.get('cumulative_default_rate', 'N/A'),
                    data.get('cumulative_loan_defaults_par', 'N/A'),
                    data.get('30_plus_dpd', 'N/A'),
                    data.get('60_plus_dpd', 'N/A'),
                    data.get('total_defaulted_loans', 'N/A'),
                    data.get('loans_paid_off', 'N/A'),
                    data.get('amortization_ytd', 'N/A'),
                    data.get('loans_upgraded_12m', 'N/A'),
                    data.get('loans_downgraded_12m', 'N/A'),
                    data.get('compliance_status', 'N/A')
                ]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)

            # Sheet 2: Capital Structure
            if data.get('class_notes'):
                classes_df = pd.DataFrame(data['class_notes'])
                classes_df.to_excel(writer, sheet_name='Capital Structure', index=False)

            # Sheet 3: Refinancing & Restructure
            refi_data = {
                'Parameter': [
                    'Refinancing Target Window', 'Expected Refinancing Costs',
                    'Estimated Annual Interest Savings', 'Market Spread Environment',
                    'Manager Intention & Strategy'
                ],
                'Details': [
                    data.get('refinancing_window', 'N/A'),
                    data.get('expected_refi_costs', 'N/A'),
                    data.get('annual_interest_savings', 'N/A'),
                    data.get('spread_environment', 'N/A'),
                    data.get('manager_intention', 'N/A')
                ]
            }
            pd.DataFrame(refi_data).to_excel(writer, sheet_name='Refinancing Analysis', index=False)

            # Sheet 4: Sector Breakdown
            if data.get('sector_breakdown'):
                sector_data = pd.DataFrame([
                    {'Sector': k, 'Allocation': v}
                    for k, v in data['sector_breakdown'].items()
                ])
                sector_data.to_excel(writer, sheet_name='Sectors', index=False)

            # Sheet 5: Credit Quality
            if data.get('credit_quality'):
                quality_data = pd.DataFrame([
                    {'Rating': k, 'Allocation': v}
                    for k, v in data['credit_quality'].items()
                ])
                quality_data.to_excel(writer, sheet_name='Credit Quality', index=False)

            # Sheet 6: Covenants
            if data.get('covenants'):
                covenant_data = pd.DataFrame([
                    {'Covenant': k, 'Status & Requirement': v}
                    for k, v in data['covenants'].items()
                ])
                covenant_data.to_excel(writer, sheet_name='Covenants', index=False)

            # Sheet 7: Credit Events
            if data.get('major_credit_events'):
                events_data = pd.DataFrame({
                    'Event': data['major_credit_events']
                })
                events_data.to_excel(writer, sheet_name='Credit Events', index=False)

        print(f"[OK] Excel saved: {output_path}")

    def process_memo(self, memo_path: str, output_json: str = None, output_excel: str = None):
        """End-to-end: read memo → extract → save outputs"""
        print(f"\n[INFO] Reading memo: {memo_path}")
        memo_text = self.read_memo(memo_path)

        print(f"[INFO] Extracting data with [{self.provider}] {self.model}...")
        extracted_data = self.extract_data(memo_text)

        if not extracted_data:
            print("[ERROR] Extraction failed")
            return None

        print(f"[SUCCESS] Extraction successful!")

        if not output_json:
            output_json = "clo_extraction.json"
        if not output_excel:
            output_excel = "clo_extraction.xlsx"

        self.save_json(extracted_data, output_json)
        self.save_excel(extracted_data, output_excel)

        return extracted_data

    def process_text(self, memo_text: str) -> dict:
        """Extract from an in-memory text string (used by the UI)."""
        print(f"[INFO] Extracting data with [{self.provider}] {self.model}...")
        extracted_data = self.extract_data(memo_text)
        return extracted_data


def main():
    """Run the extraction pipeline (CLI)."""
    extractor = CLOExtractor()
    memo_file = "sample_clo_memo.txt"

    if not os.path.exists(memo_file):
        print(f"[ERROR] {memo_file} not found. Create it first.")
        return

    data = extractor.process_memo(
        memo_file,
        output_json="clo_extraction.json",
        output_excel="clo_extraction.xlsx"
    )

    if data:
        print("\n" + "=" * 60)
        print("EXTRACTED SUMMARY")
        print("=" * 60)
        print(f"Fund: {data.get('fund_name')}")
        print(f"Portfolio Size: ${data.get('current_portfolio_size')}M")
        print(f"Total Loans: {data.get('total_loans')}")
        print(f"Default Rate: {data.get('cumulative_default_rate')}%")
        print(f"Compliance: {data.get('compliance_status')}")
        print("=" * 60)


if __name__ == "__main__":
    main()
