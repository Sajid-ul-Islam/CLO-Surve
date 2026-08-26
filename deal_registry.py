#!/usr/bin/env python3
"""
Deal Registry — persistent JSON-backed store for CLO deals,
analyst assignments, required documents, and upload/download status.
"""

import json, os
from datetime import datetime
from typing import List, Dict, Any

REGISTRY_PATH = os.path.join(os.path.dirname(__file__), "deal_registry.json")

DOC_TYPES = [
    "Indenture",
    "Offering Memorandum",
    "Trustee Report",
    "Surveillance / Quarterly Report",
    "Refinancing Memo",
    "Rating Agency Letter",
]

STATUS_CHOICES = ["Pending Upload", "Uploaded", "Downloading", "Failed", "Not Required"]

# ─── Seed data so the UI is immediately usable ───────────────────────────────
SEED_DATA: List[Dict[str, Any]] = [
    {
        "deal_id": "CLO-001",
        "deal_name": "Apex Senior Loan Fund IV",
        "analyst": "Sajid",
        "manager": "Blackstone Credit",
        "close_date": "2021-03-15",
        "docs": {
            "Indenture":                       {"status": "Pending Upload", "url": "", "local_path": ""},
            "Offering Memorandum":             {"status": "Pending Upload", "url": "", "local_path": ""},
            "Trustee Report":                  {"status": "Uploaded",       "url": "", "local_path": ""},
            "Surveillance / Quarterly Report": {"status": "Pending Upload", "url": "", "local_path": ""},
            "Refinancing Memo":                {"status": "Not Required",   "url": "", "local_path": ""},
            "Rating Agency Letter":            {"status": "Pending Upload", "url": "", "local_path": ""},
        },
        "notes": "Q3 surveillance due. Indenture amendment pending.",
    },
    {
        "deal_id": "CLO-002",
        "deal_name": "Horizon Senior Loan Fund II",
        "analyst": "Sajid",
        "manager": "Carlyle Structured Credit",
        "close_date": "2020-07-22",
        "docs": {
            "Indenture":                       {"status": "Uploaded",       "url": "", "local_path": ""},
            "Offering Memorandum":             {"status": "Uploaded",       "url": "", "local_path": ""},
            "Trustee Report":                  {"status": "Pending Upload", "url": "", "local_path": ""},
            "Surveillance / Quarterly Report": {"status": "Not Required",   "url": "", "local_path": ""},
            "Refinancing Memo":                {"status": "Pending Upload", "url": "", "local_path": ""},
            "Rating Agency Letter":            {"status": "Uploaded",       "url": "", "local_path": ""},
        },
        "notes": "Refinancing memo download required before committee.",
    },
    {
        "deal_id": "CLO-003",
        "deal_name": "Meridian Corporate Loan Trust III",
        "analyst": "Ahmed",
        "manager": "Ares Management",
        "close_date": "2022-01-10",
        "docs": {
            "Indenture":                       {"status": "Uploaded",       "url": "", "local_path": ""},
            "Offering Memorandum":             {"status": "Uploaded",       "url": "", "local_path": ""},
            "Trustee Report":                  {"status": "Uploaded",       "url": "", "local_path": ""},
            "Surveillance / Quarterly Report": {"status": "Uploaded",       "url": "", "local_path": ""},
            "Refinancing Memo":                {"status": "Not Required",   "url": "", "local_path": ""},
            "Rating Agency Letter":            {"status": "Uploaded",       "url": "", "local_path": ""},
        },
        "notes": "All docs current.",
    },
    {
        "deal_id": "CLO-004",
        "deal_name": "Pinnacle Leveraged Loan Fund I",
        "analyst": "Sara",
        "manager": "Apollo Global Management",
        "close_date": "2019-11-05",
        "docs": {
            "Indenture":                       {"status": "Pending Upload", "url": "", "local_path": ""},
            "Offering Memorandum":             {"status": "Failed",         "url": "", "local_path": ""},
            "Trustee Report":                  {"status": "Pending Upload", "url": "", "local_path": ""},
            "Surveillance / Quarterly Report": {"status": "Pending Upload", "url": "", "local_path": ""},
            "Refinancing Memo":                {"status": "Not Required",   "url": "", "local_path": ""},
            "Rating Agency Letter":            {"status": "Not Required",   "url": "", "local_path": ""},
        },
        "notes": "Offering memo download failed — check portal credentials.",
    },
]


def _load() -> List[Dict[str, Any]]:
    if os.path.exists(REGISTRY_PATH):
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    # First run — write seed data
    _save(SEED_DATA)
    return SEED_DATA


def _save(deals: List[Dict[str, Any]]):
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(deals, f, indent=2)


def load_deals() -> List[Dict[str, Any]]:
    return _load()


def save_deals(deals: List[Dict[str, Any]]):
    _save(deals)


def get_analysts(deals: List[Dict[str, Any]]) -> List[str]:
    return sorted({d["analyst"] for d in deals})


def deals_needing_docs(deals: List[Dict[str, Any]], analyst: str = None) -> List[Dict[str, Any]]:
    """Return deals that have at least one doc in Pending/Failed state."""
    NEEDS_ACTION = {"Pending Upload", "Failed"}
    filtered = [d for d in deals if analyst is None or d["analyst"] == analyst]
    return [
        d for d in filtered
        if any(v["status"] in NEEDS_ACTION for v in d["docs"].values())
    ]


def add_deal(deals: List[Dict[str, Any]], deal_id, deal_name, analyst, manager, close_date, notes="") -> List[Dict[str, Any]]:
    new_deal = {
        "deal_id": deal_id,
        "deal_name": deal_name,
        "analyst": analyst,
        "manager": manager,
        "close_date": close_date,
        "docs": {dt: {"status": "Pending Upload", "url": "", "local_path": ""} for dt in DOC_TYPES},
        "notes": notes,
    }
    deals.append(new_deal)
    _save(deals)
    return deals


def update_doc_url(deals: List[Dict[str, Any]], deal_id: str, doc_type: str, url: str) -> List[Dict[str, Any]]:
    for d in deals:
        if d["deal_id"] == deal_id:
            d["docs"][doc_type]["url"] = url
    _save(deals)
    return deals


def update_doc_status(deals: List[Dict[str, Any]], deal_id: str, doc_type: str,
                      status: str, local_path: str = "") -> List[Dict[str, Any]]:
    for d in deals:
        if d["deal_id"] == deal_id:
            d["docs"][doc_type]["status"] = status
            if local_path:
                d["docs"][doc_type]["local_path"] = local_path
    _save(deals)
    return deals
