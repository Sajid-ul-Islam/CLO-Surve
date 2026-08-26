#!/usr/bin/env python3
"""
Unit tests for OfflineCLOExtractor and CLO Committee Studio components.
Tests deterministic parsing of both sample_clo_memo.txt and sample_refi_memo.txt.
"""

import os
from offline_extractor import OfflineCLOExtractor
from committee_memo_generator import CommitteeMemoGenerator


def test_surveillance_memo_extraction():
    memo_path = "sample_clo_memo.txt"
    assert os.path.exists(memo_path), f"Test memo file {memo_path} not found."

    with open(memo_path, "r", encoding="utf-8") as f:
        text = f.read()

    extractor = OfflineCLOExtractor()
    data = extractor.extract(text)

    print("\n--- SURVEILLANCE MEMO EXTRACTION ---")
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

    assert "Apex Senior Loan Fund IV" in data["fund_name"]
    assert "Wilmington Trust" in data["trustee"]
    assert data["current_portfolio_size"] == 1187.5
    assert data["total_loans"] == 147
    assert data["wac"] == 4.85
    assert data["wal"] == 3.2
    assert data["cumulative_default_rate"] == 3.58
    assert len(data["class_notes"]) == 4
    assert len(data["sector_breakdown"]) >= 7
    assert len(data["covenants"]) >= 4

    print("[PASS] Surveillance memo assertions passed.")


def test_refinancing_memo_extraction():
    memo_path = "sample_refi_memo.txt"
    assert os.path.exists(memo_path), f"Test memo file {memo_path} not found."

    with open(memo_path, "r", encoding="utf-8") as f:
        text = f.read()

    extractor = OfflineCLOExtractor()
    data = extractor.extract(text)

    print("\n--- REFINANCING MEMO EXTRACTION ---")
    print(f"Fund Name: {data['fund_name']}")
    print(f"Trustee: {data['trustee']}")
    print(f"Portfolio Manager: {data['portfolio_manager']}")
    print(f"Portfolio Size: ${data['current_portfolio_size']}M")
    print(f"Total Loans: {data['total_loans']}")
    print(f"WAC: {data['wac']}%")
    print(f"WAL: {data['wal']} years")
    print(f"Rating: {data['weighted_avg_rating']}")
    print(f"Default Rate: {data['cumulative_default_rate']}%")
    print(f"Refi Window: {data['refinancing_window']}")
    print(f"Annual Interest Savings: {data['annual_interest_savings']}")
    print(f"Sectors Extracted: {len(data['sector_breakdown'])}")
    print(f"Class Notes Extracted: {len(data['class_notes'])}")
    print(f"Covenants Extracted: {len(data['covenants'])}")

    assert "Horizon Senior Loan Fund II" in data["fund_name"]
    assert "U.S. Bank Trust Company" in data["trustee"]
    assert data["current_portfolio_size"] == 945.0
    assert data["total_loans"] == 124
    assert data["wac"] == 5.15
    assert data["wal"] == 2.8
    assert "BBB-" in data["weighted_avg_rating"]
    assert data["cumulative_default_rate"] == 1.85
    assert "Q4 2026" in data["refinancing_window"] or "Q1 2027" in data["refinancing_window"]
    assert "$4,850,000" in data["annual_interest_savings"]
    assert len(data["class_notes"]) == 4

    print("[PASS] Refinancing memo assertions passed.")


def test_committee_memo_generation():
    memo_path = "sample_refi_memo.txt"
    with open(memo_path, "r", encoding="utf-8") as f:
        text = f.read()

    extractor = OfflineCLOExtractor()
    data = extractor.extract(text)

    gen = CommitteeMemoGenerator(data)
    md = gen.generate_markdown_brief(recommendation="Refinance Portfolio", target_period="Q1 2027")
    txt = gen.generate_text_brief(recommendation="Refinance Portfolio", target_period="Q1 2027")
    html = gen.generate_html_brief(recommendation="Refinance Portfolio", target_period="Q1 2027")

    assert "CLO INVESTMENT & SURVEILLANCE COMMITTEE MEMORANDUM" in md
    assert "Horizon Senior Loan Fund II" in md
    assert "REFINANCE PORTFOLIO" in md.upper()
    assert "CLO COMMITTEE MEMORANDUM" in txt
    assert "<!DOCTYPE html>" in html
    assert "Horizon Senior Loan Fund II" in html


    print("[PASS] Committee memo generator assertions passed.")


if __name__ == "__main__":
    test_surveillance_memo_extraction()
    test_refinancing_memo_extraction()
    test_committee_memo_generation()
    print("\n[ALL TESTS PASSED SUCCESSFULLY!]")

