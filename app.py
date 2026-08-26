#!/usr/bin/env python3
"""
CLO Surveillance & Refinancing Studio
Extracts structured metrics from CLO memos, visualises portfolio analytics,
and generates executive Committee Memorandum packages.

Run: streamlit run app.py
"""

import io, os, json, re
import streamlit as st
import pandas as pd

try:
    import plotly.express as px
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

from clo_extractor import CLOExtractor
from committee_memo_generator import CommitteeMemoGenerator
from offline_extractor import OfflineCLOExtractor

# ─────────────────────────────────────────────────────────────────────────────
# Page config & global CSS
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CLO Surveillance Studio",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.metric-card {
    background:#fff; border:1px solid #e0e0e0; border-radius:10px;
    padding:14px; text-align:center; box-shadow:0 2px 6px rgba(0,0,0,.04);
}
.metric-value { font-size:21px; font-weight:700; color:#0D47A1; margin-top:4px; }
.metric-label { font-size:11px; font-weight:600; color:#616161;
                text-transform:uppercase; letter-spacing:.5px; }
.cov-pass { background:#E8F5E9; border-left:4px solid #2E7D32;
            padding:8px 12px; border-radius:5px; margin-bottom:6px; }
.cov-fail { background:#FFEBEE; border-left:4px solid #C62828;
            padding:8px 12px; border-radius:5px; margin-bottom:6px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────────────

def kpi(col, label: str, value: str):
    """Render a single metric card into a Streamlit column."""
    col.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def parse_pct(v) -> float:
    """Parse a percentage string or number to float, default 0."""
    try:
        return float(re.sub(r"[^\d.]", "", str(v).split("(")[0]))
    except (ValueError, TypeError):
        return 0.0


def chart_dict(data_dict: dict, label_col: str, value_col: str, kind: str = "bar"):
    """Render a bar or pie chart from a dict; fall back to st.bar_chart."""
    if not data_dict:
        return
    names = list(data_dict.keys())
    vals = [parse_pct(v) for v in data_dict.values()]
    if HAS_PLOTLY:
        if kind == "pie":
            fig = px.pie(names=names, values=vals, hole=0.4,
                         color_discrete_sequence=px.colors.sequential.Blues_r)
        else:
            fig = px.bar(x=names, y=vals,
                         labels={"x": label_col, "y": value_col},
                         color=vals, color_continuous_scale="Blues")
        fig.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=280)
        st.plotly_chart(fig, use_container_width=True)
    else:
        df = pd.DataFrame({label_col: names, value_col: vals})
        st.bar_chart(df.set_index(label_col))


def build_excel(data: dict):
    """Build a multi-sheet Excel workbook from extracted CLO data."""
    try:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            fields = [
                ("Fund Name", "fund_name"), ("Trustee", "trustee"),
                ("Portfolio Manager", "portfolio_manager"), ("Report Date", "report_date"),
                ("Reporting Period", "reporting_period"), ("Closing Date", "closing_date"),
                ("Initial Collateral ($M)", "initial_collateral_size"),
                ("Portfolio Size ($M)", "current_portfolio_size"),
                ("Total Loans", "total_loans"), ("WAC (%)", "wac"), ("WAL (yrs)", "wal"),
                ("Avg Rating", "weighted_avg_rating"),
                ("Cumulative Default Rate (%)", "cumulative_default_rate"),
                ("Default Par ($M)", "cumulative_loan_defaults_par"),
                ("30+ DPD ($M)", "30_plus_dpd"), ("60+ DPD ($M)", "60_plus_dpd"),
                ("Defaulted Loans", "total_defaulted_loans"),
                ("Loans Paid Off", "loans_paid_off"),
                ("Amortization YTD (%)", "amortization_ytd"),
                ("12M Upgrades", "loans_upgraded_12m"),
                ("12M Downgrades", "loans_downgraded_12m"),
                ("Compliance", "compliance_status"),
            ]
            pd.DataFrame(
                {"Metric": [f for f, _ in fields],
                 "Value": [data.get(k, "N/A") for _, k in fields]}
            ).to_excel(w, sheet_name="Summary", index=False)

            if data.get("class_notes"):
                pd.DataFrame(data["class_notes"]).to_excel(
                    w, sheet_name="Capital Structure", index=False)

            pd.DataFrame({
                "Parameter": ["Refi Window", "Expected Costs", "Annual Savings",
                               "Spread Env", "Manager Plan"],
                "Details": [data.get(k, "N/A") for k in (
                    "refinancing_window", "expected_refi_costs",
                    "annual_interest_savings", "spread_environment", "manager_intention")],
            }).to_excel(w, sheet_name="Refinancing", index=False)

            for key, sheet, col_a, col_b in [
                ("sector_breakdown", "Sectors",       "Sector",   "Allocation"),
                ("credit_quality",   "Credit Quality", "Rating",   "Allocation"),
                ("covenants",        "Covenants",      "Covenant", "Status"),
            ]:
                if data.get(key):
                    pd.DataFrame(
                        [{col_a: k, col_b: v} for k, v in data[key].items()]
                    ).to_excel(w, sheet_name=sheet, index=False)

            if data.get("major_credit_events"):
                pd.DataFrame({"Event": data["major_credit_events"]}).to_excel(
                    w, sheet_name="Credit Events", index=False)
        return buf
    except Exception as e:
        st.warning(f"Excel export warning: {e}")
        return None


def load_sample(path: str) -> str:
    if os.path.exists(path):
        return open(path, encoding="utf-8").read()
    st.error(f"Sample file not found: {path}")
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar — top-level module selector
# ─────────────────────────────────────────────────────────────────────────────
st.sidebar.title("🏦 CLO Studio")
st.sidebar.caption("v2.0 · Surveillance · Refinancing · Doc Automation")

active_module = st.sidebar.radio(
    "📌 Module",
    ["📊 CLO Surveillance Studio", "📋 Deal Tracker & Doc Automation"],
    index=0,
    help="Switch between the memo extraction/analytics studio and the deal/document tracker.",
)
st.sidebar.divider()

# ── Route to Deal Tracker early so it controls its own sidebar ───────────────
if active_module == "📋 Deal Tracker & Doc Automation":
    from deal_tracker import render as render_tracker
    render_tracker()
    st.stop()  # Don't render CLO Studio content below

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar — CLO Studio extraction engine configuration
# ─────────────────────────────────────────────────────────────────────────────
engine_mode = st.sidebar.radio(
    "Extraction Engine",
    ["⚡ Offline (No API Key)", "🤖 AI LLM Agent"],
    index=0,
    help="Offline: deterministic regex parsing, zero API calls. AI: LLM with auto-fallback.",
)
is_offline = "Offline" in engine_mode

PROVIDERS = {
    "openrouter": ("OPENROUTER_API_KEY", "z-ai/glm-5.3-flash"),
    "gemini":     ("GEMINI_API_KEY",     "gemini-2.5-flash"),
    "groq":       ("GROQ_API_KEY",       "qwen/qwen3.8-27b"),
}

if not is_offline:
    typed_key = st.sidebar.text_input("🔑 API Key", type="password",
                                      placeholder="Paste Gemini / OpenRouter / Groq key…")
    clean_key = typed_key.strip()

    # Auto-detect provider from key prefix
    if clean_key.startswith("AIza"):
        provider = "gemini"
    elif clean_key.startswith("gsk_"):
        provider = "groq"
    else:
        provider = "openrouter"

    env_var, default_model = PROVIDERS[provider]

    def _secret(k):
        try: return st.secrets.get(k)
        except Exception: return None

    api_key = clean_key or _secret(env_var) or os.getenv(env_var, "")
    model = default_model

    with st.sidebar.expander("⚙️ Override model (optional)"):
        override = st.text_input("Model name", placeholder=f"Default: {model}")
        if override.strip():
            model = override.strip()

    allow_fallback = st.sidebar.checkbox("Auto-fallback to Offline on error", value=True)

    if api_key:
        st.sidebar.caption(f"✅ Provider: **{provider.upper()}** — `{model}`")
    else:
        st.sidebar.caption("💡 No key — will use ⚡ Offline engine.")
else:
    provider, api_key, model, allow_fallback = "offline", "OFFLINE_RULE_BASED", "rule-based", True
    st.sidebar.info("⚡ 100% Offline — no API calls required.")

# ─────────────────────────────────────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────────────────────────────────────
ss = st.session_state
ss.setdefault("extracted_data", None)
ss.setdefault("memo_text", "")

# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────
badge = "⚡ Offline Engine" if is_offline else f"🤖 {provider.upper()}"
st.markdown(f"## 🏦 CLO Surveillance & Refinancing Studio &nbsp; `{badge}`")
st.caption("Structured Collateral Extraction · Portfolio Analytics · Committee Memorandum Packages")
st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────────────────────────────────────
tab_upload, tab_dash, tab_editor, tab_committee, tab_compare = st.tabs([
    "📄 Upload & Extract",
    "📈 Dashboard",
    "✍️ Edit Metrics",
    "🏛️ Committee Memo",
    "🔍 Deal Compare",
])

# ═══════════════════════════════════════════════════════════════════════════
# TAB 1 — Upload & Extract
# ═══════════════════════════════════════════════════════════════════════════
with tab_upload:
    st.subheader("Load Memo")

    c1, c2, c3 = st.columns(3)
    if c1.button("📋 Surveillance Sample (Apex Fund IV)", use_container_width=True):
        ss["memo_text"] = load_sample("sample_clo_memo.txt")
        st.rerun()
    if c2.button("🔄 Refinancing Sample (Horizon Fund II)", use_container_width=True):
        ss["memo_text"] = load_sample("sample_refi_memo.txt")
        st.rerun()
    if c3.button("🧹 Clear", use_container_width=True):
        ss["memo_text"] = ""
        ss["extracted_data"] = None
        st.rerun()

    inp_file, inp_paste, inp_url = st.tabs(["📄 Upload File", "✍️ Paste Text", "🔗 URL"])
    input_text = None

    with inp_file:
        up = st.file_uploader("Upload .txt / .md / .pdf", type=["txt", "md", "pdf"])
        if up:
            if up.name.lower().endswith(".pdf"):
                try:
                    import pdfplumber
                    with pdfplumber.open(io.BytesIO(up.read())) as pdf:
                        input_text = "\n".join(p.extract_text() or "" for p in pdf.pages)
                    st.success(f"PDF parsed ({len(pdf.pages)} pages).")
                except ImportError:
                    st.error("pdfplumber not installed. Upload a .txt file instead.")
            else:
                input_text = up.read().decode("utf-8", errors="replace")

    with inp_paste:
        pasted = st.text_area("Paste memo text", value=ss["memo_text"], height=240,
                              placeholder="Paste CLO surveillance or refinancing memo…")
        if pasted.strip():
            input_text = pasted

    with inp_url:
        url = st.text_input("Public URL", placeholder="https://example.com/memo.txt")
        if url and st.button("Fetch"):
            import urllib.request
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    input_text = r.read().decode("utf-8", errors="replace")
                ss["memo_text"] = input_text
                st.success("Fetched successfully.")
            except Exception as e:
                st.error(f"Fetch failed: {e}")

    memo = input_text or ss["memo_text"]
    if memo:
        st.caption(f"Preview — {len(memo.splitlines())} lines, {len(memo):,} chars")
        st.text_area("", memo[:2000], height=160, disabled=True)

    st.divider()
    if st.button("🚀 Extract CLO Data", type="primary", use_container_width=True):
        if not memo.strip():
            st.error("Please load or paste memo content first.")
        else:
            ss["memo_text"] = memo
            with st.spinner(f"Extracting with [{provider}] engine…"):
                extractor = CLOExtractor(
                    api_key=api_key if not is_offline else None,
                    model=model,
                    provider=provider if not is_offline else "offline",
                    allow_fallback=allow_fallback,
                )
                result = extractor.process_text(memo)
            if result:
                ss["extracted_data"] = result
                st.success("✅ Extraction complete! Go to **Dashboard** or **Committee Memo** tab.")
            else:
                st.error("Extraction returned no data.")

# ═══════════════════════════════════════════════════════════════════════════
# TAB 2 — Dashboard
# ═══════════════════════════════════════════════════════════════════════════
with tab_dash:
    data = ss["extracted_data"]
    if not data:
        st.info("Extract a memo first in the **Upload & Extract** tab.")
    else:
        engine = data.get("_metadata", {}).get("engine", provider)
        st.markdown(f"### {data.get('fund_name', 'CLO Portfolio')}")
        st.caption(
            f"Engine: `{engine}` · Date: {data.get('report_date','N/A')} "
            f"· Manager: {data.get('portfolio_manager','N/A')} "
            f"· Trustee: {data.get('trustee','N/A')}"
        )

        # KPI row 1
        cols = st.columns(6)
        kpi(cols[0], "Portfolio Size",    f"${data.get('current_portfolio_size', 0)}M")
        kpi(cols[1], "Total Loans",       str(data.get("total_loans", 0)))
        kpi(cols[2], "WAC",               f"{data.get('wac', 0)}%")
        kpi(cols[3], "WAL",               f"{data.get('wal', 0)} yrs")
        kpi(cols[4], "Avg Rating",        str(data.get("weighted_avg_rating", "N/A")))
        kpi(cols[5], "Default Rate",      f"{data.get('cumulative_default_rate', 0)}%")

        # KPI row 2
        st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)
        cols2 = st.columns(5)
        kpi(cols2[0], "30+ DPD",          f"${data.get('30_plus_dpd', 0)}M")
        kpi(cols2[1], "60+ DPD",          f"${data.get('60_plus_dpd', 0)}M")
        kpi(cols2[2], "Amortization YTD", f"{data.get('amortization_ytd', 0)}%")
        kpi(cols2[3], "12M Net Actions",  str(data.get("rating_actions_net", "+0")))
        kpi(cols2[4], "Initial Par",
            f"${data.get('initial_collateral_size', data.get('current_portfolio_size', 0))}M")

        # Refinancing highlight (only when relevant)
        if data.get("refinancing_window") or data.get("annual_interest_savings"):
            st.info(
                f"🔄 **Refi Window:** {data.get('refinancing_window','N/A')} · "
                f"**Expected Costs:** {data.get('expected_refi_costs','N/A')} · "
                f"**Annual Savings:** {data.get('annual_interest_savings','N/A')} · "
                f"**Spread Env:** {data.get('spread_environment','N/A')}"
            )

        st.divider()

        # Charts
        ch1, ch2 = st.columns(2)
        with ch1:
            st.markdown("#### Industry Sectors")
            chart_dict(data.get("sector_breakdown", {}), "Sector", "Allocation (%)", kind="pie")
        with ch2:
            st.markdown("#### Credit Quality")
            chart_dict(data.get("credit_quality", {}), "Rating", "Allocation (%)", kind="bar")

        st.divider()

        # Tranches
        notes = data.get("class_notes", [])
        if notes:
            st.markdown("#### Tranche Waterfall")
            st.dataframe(pd.DataFrame(notes), use_container_width=True)

        # Covenants + events
        cv, ev = st.columns(2)
        with cv:
            st.markdown("#### Covenant Compliance")
            covs = data.get("covenants", {})
            if covs:
                for k, v in covs.items():
                    cls = "cov-fail" if any(w in str(v).lower() for w in ("breach", "fail")) else "cov-pass"
                    st.markdown(f'<div class="{cls}"><strong>{k}:</strong> {v}</div>',
                                unsafe_allow_html=True)
            else:
                st.write(data.get("compliance_status", "Compliant"))
        with ev:
            st.markdown("#### Credit Events")
            evts = data.get("major_credit_events", [])
            if evts:
                for e in evts:
                    st.write(f"- {e}")
            else:
                st.write("No adverse events reported.")

        # Downloads
        st.divider()
        dl1, dl2 = st.columns(2)
        fund_slug = data.get("fund_name", "deal").replace(" ", "_")
        dl1.download_button("⬇️ JSON", json.dumps(data, indent=2).encode(),
                            f"clo_{fund_slug}.json", "application/json",
                            use_container_width=True)
        buf = build_excel(data)
        if buf:
            dl2.download_button("⬇️ Excel (.xlsx)", buf.getvalue(),
                                f"clo_{fund_slug}.xlsx",
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════
# TAB 3 — Analyst Metric Editor
# ═══════════════════════════════════════════════════════════════════════════
with tab_editor:
    data = ss["extracted_data"]
    if not data:
        st.info("Extract a memo first.")
    else:
        st.subheader("Analyst Override Grid")
        st.caption("Adjust any extracted value before generating committee packages.")

        with st.form("editor"):
            st.markdown("##### Deal Identifiers")
            r1 = st.columns(4)
            fn  = r1[0].text_input("Fund Name",         value=str(data.get("fund_name", "")))
            pm  = r1[1].text_input("Portfolio Manager",  value=str(data.get("portfolio_manager", "")))
            tr  = r1[2].text_input("Trustee",            value=str(data.get("trustee", "")))
            rd  = r1[3].text_input("Report Date",        value=str(data.get("report_date", "")))

            st.markdown("##### Portfolio & Credit Metrics")
            r2 = st.columns(4)
            sz  = r2[0].number_input("Size ($M)",   value=float(data.get("current_portfolio_size", 0)))
            wac = r2[1].number_input("WAC (%)",     value=float(data.get("wac", 0)))
            lc  = r2[2].number_input("Loan Count",  value=int(data.get("total_loans", 0)), step=1)
            wal = r2[3].number_input("WAL (yrs)",   value=float(data.get("wal", 0)))
            r3  = st.columns(4)
            dr  = r3[0].number_input("Default Rate (%)", value=float(data.get("cumulative_default_rate", 0)))
            rat = r3[1].text_input("Avg Rating",    value=str(data.get("weighted_avg_rating", "")))
            d30 = r3[2].number_input("30+ DPD ($M)", value=float(data.get("30_plus_dpd", 0)))
            d60 = r3[3].number_input("60+ DPD ($M)", value=float(data.get("60_plus_dpd", 0)))

            st.markdown("##### Refinancing Parameters")
            r4  = st.columns(3)
            rw  = r4[0].text_input("Refi Window",   value=str(data.get("refinancing_window", "")))
            rc  = r4[1].text_input("Refi Costs",    value=str(data.get("expected_refi_costs", "")))
            sav = r4[2].text_input("Annual Savings", value=str(data.get("annual_interest_savings", "")))
            cs  = st.text_input("Compliance Status", value=str(data.get("compliance_status", "")))

            if st.form_submit_button("💾 Save Overrides", use_container_width=True):
                data.update({
                    "fund_name": fn, "portfolio_manager": pm, "trustee": tr,
                    "report_date": rd, "current_portfolio_size": sz, "wac": wac,
                    "total_loans": lc, "wal": wal, "cumulative_default_rate": dr,
                    "weighted_avg_rating": rat, "30_plus_dpd": d30, "60_plus_dpd": d60,
                    "refinancing_window": rw, "expected_refi_costs": rc,
                    "annual_interest_savings": sav, "compliance_status": cs,
                })
                ss["extracted_data"] = data
                st.success("✅ Overrides saved.")

# ═══════════════════════════════════════════════════════════════════════════
# TAB 4 — Committee Memo
# ═══════════════════════════════════════════════════════════════════════════
with tab_committee:
    data = ss["extracted_data"]
    if not data:
        st.info("Extract a memo first.")
    else:
        st.subheader("CLO Committee Memorandum Builder")

        ca, cb = st.columns(2)
        rec = ca.selectbox("Committee Recommendation", [
            "Refinance Portfolio", "Hold & Monitor", "Reinvest Cashflows",
            "Restructure Tranches", "De-Risk High Betas",
        ])
        period = ca.text_input("Target Timeframe", value=data.get("refinancing_window", "Q1 2027"))
        notes_txt = cb.text_area(
            "Analyst Rationale",
            value=f"Tight spread environment favors refinancing for {data.get('fund_name','this fund')}.",
            height=110,
        )

        st.markdown("##### Action Items")
        a1 = st.text_input("Item 1", "Monitor healthcare & energy obligors for rating migration.", key="a1")
        a2 = st.text_input("Item 2", "Engage dealer desk on refinancing syndicate terms.", key="a2")
        a3 = st.text_input("Item 3", "Review asset coverage test cushion before next distribution.", key="a3")
        actions = [a for a in [a1, a2, a3] if a.strip()]

        if st.button("📝 Generate Memo Package", type="primary", use_container_width=True):
            gen = CommitteeMemoGenerator(data)
            ss["memo_md"]   = gen.generate_markdown_brief(rec, period, notes_txt, actions)
            ss["memo_txt"]  = gen.generate_text_brief(rec, period, notes_txt)
            ss["memo_html"] = gen.generate_html_brief(rec, period, notes_txt, actions)
            st.success("🎉 Memo package generated!")

        if "memo_md" in ss:
            st.divider()
            slug = data.get("fund_name", "Deal").replace(" ", "_")
            d1, d2, d3 = st.columns(3)
            d1.download_button("⬇️ Markdown (.md)",    ss["memo_md"].encode(),
                               f"CLO_Memo_{slug}.md",  "text/markdown", use_container_width=True)
            d2.download_button("⬇️ Plain Text (.txt)",  ss["memo_txt"].encode(),
                               f"CLO_Memo_{slug}.txt", "text/plain",    use_container_width=True)
            d3.download_button("⬇️ HTML (.html)",       ss["memo_html"].encode(),
                               f"CLO_Memo_{slug}.html","text/html",     use_container_width=True)
            st.markdown(ss["memo_md"])

# ═══════════════════════════════════════════════════════════════════════════
# TAB 5 — Deal Compare
# ═══════════════════════════════════════════════════════════════════════════
with tab_compare:
    st.subheader("Side-by-Side Deal Comparison")
    st.caption("Compare Apex Fund IV (surveillance) vs Horizon Fund II (refinancing) key metrics.")

    if st.button("⚡ Run Comparison", type="primary", use_container_width=True):
        if os.path.exists("sample_clo_memo.txt") and os.path.exists("sample_refi_memo.txt"):
            ext = OfflineCLOExtractor()
            d1 = ext.extract(open("sample_clo_memo.txt", encoding="utf-8").read())
            d2 = ext.extract(open("sample_refi_memo.txt", encoding="utf-8").read())

            METRICS = [
                ("Deal Name",           "fund_name"),
                ("Manager",             "portfolio_manager"),
                ("Portfolio Size ($M)", "current_portfolio_size"),
                ("Total Loans",         "total_loans"),
                ("WAC (%)",             "wac"),
                ("WAL (yrs)",           "wal"),
                ("Avg Rating",          "weighted_avg_rating"),
                ("Default Rate (%)",    "cumulative_default_rate"),
                ("Refi Window",         "refinancing_window"),
                ("Annual Savings",      "annual_interest_savings"),
                ("Compliance",          "compliance_status"),
            ]

            rows = []
            for label, key in METRICS:
                v1, v2 = d1.get(key, "N/A"), d2.get(key, "N/A")
                try:
                    delta = f"Δ {round(float(v2) - float(v1), 2)}"
                except (TypeError, ValueError):
                    delta = "—"
                rows.append({
                    "Metric": label,
                    "Deal A (Apex Surveillance)": v1,
                    "Deal B (Horizon Refi)": v2,
                    "Δ Variance": delta,
                })

            st.dataframe(pd.DataFrame(rows), use_container_width=True)
        else:
            st.warning("Sample memo files not found in the working directory.")
