#!/usr/bin/env python3
"""
CLO Surveillance Memo Extraction Agent
Extracts structured data from CLO surveillance/refi memos using an LLM API.

Provider: OpenRouter (OpenAI-compatible chat completions).
Default model: stealth/ox-alpha
"""

import json
import os
from datetime import datetime
from openai import OpenAI

# Try to import pandas and openpyxl for Excel output (optional)
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    print("⚠️  pandas not found. JSON output only. Install: pip install pandas openpyxl")


class CLOExtractor:
    def __init__(
        self,
        api_key: str = None,
        model: str = "z-ai/glm-5.3-flash",
        base_url: str = "https://openrouter.ai/api/v1",
    ):
        """Initialize the OpenRouter (OpenAI-compatible) client."""
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "No API key found. Set OPENROUTER_API_KEY or pass api_key=..."
            )
        self.model = model
        self.client = OpenAI(api_key=self.api_key, base_url=base_url)

    def read_memo(self, file_path: str) -> str:
        """Read memo from file (txt, pdf text, etc.)"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    def extract_data(self, memo_text: str) -> dict:
        """
        Use the LLM to extract structured data from memo.
        Returns a dict with all extracted fields.
        """

        extraction_prompt = f"""You are a financial analyst specializing in CLO (Collateralized Loan Obligation) analysis.

Extract ALL the following data from the CLO memo below. Return ONLY valid JSON, no markdown formatting.

REQUIRED FIELDS (extract exactly these):
{{
  "fund_name": "string",
  "trustee": "string",
  "report_date": "YYYY-MM-DD",
  "portfolio_manager": "string",
  "closing_date": "YYYY-MM-DD",
  "current_portfolio_size": "number (in millions)",
  "total_loans": "number",
  "wac": "number (weighted average coupon, %)",
  "wal": "number (weighted average life, years)",
  "weighted_avg_rating": "string",
  "cumulative_default_rate": "number (%)",
  "30_plus_dpd": "number ($ millions)",
  "60_plus_dpd": "number ($ millions)",
  "total_defaulted_loans": "number",
  "amortization_ytd": "number (%)",
  "loans_upgraded_12m": "number",
  "loans_downgraded_12m": "number",
  "sector_breakdown": {{
    "sector_name": "percentage"
  }},
  "credit_quality": {{
    "rating_bucket": "percentage or $ amount"
  }},
  "class_notes": [
    {{
      "class": "string (A-1, A-2, B, C, etc.)",
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
  "refinancing_window": "string or date",
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

            # Try to parse as JSON
            extracted_data = json.loads(response_text)
            return extracted_data

        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse LLM response as JSON: {e}")
            print(f"Raw response:\n{response_text}")
            return None

    def save_json(self, data: dict, output_path: str):
        """Save extracted data to JSON file"""
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"✅ JSON saved: {output_path}")

    def save_excel(self, data: dict, output_path: str):
        """Save extracted data to Excel workbook with multiple sheets"""
        if not HAS_PANDAS:
            print("⚠️  Skipping Excel export (pandas not installed)")
            return

        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:

            # Sheet 1: Summary
            summary_data = {
                'Metric': [
                    'Fund Name', 'Trustee', 'Portfolio Manager', 'Report Date',
                    'Closing Date', 'Portfolio Size ($M)', 'Total Loans', 'WAC (%)',
                    'WAL (years)', 'Weighted Avg Rating', 'Cumulative Default Rate (%)',
                    '30+ DPD ($M)', '60+ DPD ($M)', 'Compliance Status'
                ],
                'Value': [
                    data.get('fund_name', 'N/A'),
                    data.get('trustee', 'N/A'),
                    data.get('portfolio_manager', 'N/A'),
                    data.get('report_date', 'N/A'),
                    data.get('closing_date', 'N/A'),
                    data.get('current_portfolio_size', 'N/A'),
                    data.get('total_loans', 'N/A'),
                    data.get('wac', 'N/A'),
                    data.get('wal', 'N/A'),
                    data.get('weighted_avg_rating', 'N/A'),
                    data.get('cumulative_default_rate', 'N/A'),
                    data.get('30_plus_dpd', 'N/A'),
                    data.get('60_plus_dpd', 'N/A'),
                    data.get('compliance_status', 'N/A')
                ]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)

            # Sheet 2: Sector Breakdown
            if data.get('sector_breakdown'):
                sector_data = pd.DataFrame([
                    {'Sector': k, 'Allocation (%)': v}
                    for k, v in data['sector_breakdown'].items()
                ])
                sector_data.to_excel(writer, sheet_name='Sectors', index=False)

            # Sheet 3: Credit Quality
            if data.get('credit_quality'):
                quality_data = pd.DataFrame([
                    {'Rating': k, 'Amount (%)': v}
                    for k, v in data['credit_quality'].items()
                ])
                quality_data.to_excel(writer, sheet_name='Credit Quality', index=False)

            # Sheet 4: Class Notes
            if data.get('class_notes'):
                classes_df = pd.DataFrame(data['class_notes'])
                classes_df.to_excel(writer, sheet_name='Class Notes', index=False)

            # Sheet 5: Covenants
            if data.get('covenants'):
                covenant_data = pd.DataFrame([
                    {'Covenant': k, 'Status': v}
                    for k, v in data['covenants'].items()
                ])
                covenant_data.to_excel(writer, sheet_name='Covenants', index=False)

            # Sheet 6: Credit Events
            if data.get('major_credit_events'):
                events_data = pd.DataFrame({
                    'Event': data['major_credit_events']
                })
                events_data.to_excel(writer, sheet_name='Credit Events', index=False)

        print(f"✅ Excel saved: {output_path}")

    def process_memo(self, memo_path: str, output_json: str = None, output_excel: str = None):
        """End-to-end: read memo → extract → save outputs"""
        print(f"\n📄 Reading memo: {memo_path}")
        memo_text = self.read_memo(memo_path)

        print(f"🔍 Extracting data with {self.model}...")
        extracted_data = self.extract_data(memo_text)

        if not extracted_data:
            print("❌ Extraction failed")
            return None

        print(f"✨ Extraction successful!")

        if not output_json:
            output_json = "clo_extraction.json"
        if not output_excel:
            output_excel = "clo_extraction.xlsx"

        self.save_json(extracted_data, output_json)
        self.save_excel(extracted_data, output_excel)

        return extracted_data

    def process_text(self, memo_text: str) -> dict:
        """Extract from an in-memory text string (used by the UI)."""
        print(f"🔍 Extracting data with {self.model}...")
        extracted_data = self.extract_data(memo_text)
        return extracted_data


def main():
    """Run the extraction pipeline (CLI)."""
    extractor = CLOExtractor()
    memo_file = "sample_clo_memo.txt"

    if not os.path.exists(memo_file):
        print(f"❌ {memo_file} not found. Create it first.")
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
