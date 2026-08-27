#!/usr/bin/env python3
"""
Unit test for OfflineCLOExtractor
Ensures rule-based extraction parses sample_clo_memo.txt accurately without network/LLM dependencies.
"""

import os
from offline_extractor import OfflineCLOExtractor


def test_offline_extraction():
    memo_path = "sample_clo_memo.txt"
    assert os.path.exists(memo_path), f"Test memo file {memo_path} not found."

    with open(memo_path, "r", encoding="utf-8") as f:
        text = f.read()

    extractor = OfflineCLOExtractor()
    data = extractor.extract(text)

    print("--- OFFLINE EXTRACTION TEST RESULTS ---")
    print(f"Fund Name: {data['fund_name']}")
    print(f"Trustee: {data['trustee']}")
    print(f"Portfolio Manager: {data['portfolio_manager']}")
    print(f"Portfolio Size: ${data['current_portfolio_size']}M")
    print(f"Total Loans: {data['total_loans']}")
    print(f"WAC: {data['wac']}%")
    print(f"WAL: {data['wal']} years")
    print(f"Default Rate: {data['cumulative_default_rate']}%")
    print(f"Sectors Extracted: {len(data['sector_breakdown'])}")
    print(f"Class Notes Extracted: {len(data['class_notes'])}")
    print(f"Covenants Extracted: {len(data['covenants'])}")
    print(f"Credit Events Extracted: {len(data['major_credit_events'])}")

    # Assertions
    assert "Apex Senior Loan Fund IV" in data["fund_name"], f"Unexpected fund name: {data['fund_name']}"
    assert "Wilmington Trust" in data["trustee"], f"Unexpected trustee: {data['trustee']}"
    assert data["current_portfolio_size"] == 1187.5, f"Unexpected portfolio size: {data['current_portfolio_size']}"
    assert data["total_loans"] == 147, f"Unexpected loan count: {data['total_loans']}"
    assert data["wac"] == 4.85, f"Unexpected WAC: {data['wac']}"
    assert data["wal"] == 3.2, f"Unexpected WAL: {data['wal']}"
    assert data["cumulative_default_rate"] == 3.58, f"Unexpected default rate: {data['cumulative_default_rate']}"

    print("[OK] All offline extraction assertions PASSED successfully!")


if __name__ == "__main__":
    test_offline_extraction()
