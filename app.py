#!/usr/bin/env python3
"""
CLO Surveillance & Refinancing Studio — Complete Application
Extracts structured financial metrics from CLO surveillance and refinancing memos,
visualizes portfolio analytics, provides interactive metric editing, and generates
executive CLO Committee Memorandum packages using AI LLMs or Standalone Offline Engines.

Run locally: streamlit run app.py
"""

import io
import os
import json
import streamlit as st
from datetime import datetime

# Try to import Plotly for rich interactive financial charts
try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

from clo_extractor import CLOExtractor
from committee_memo_generator import CommitteeMemoGenerator

st.set_page_config(
    page_title="CLO Surveillance & Committee Studio",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------------------------------------------------------------------
# Custom CSS Styling Injection for Enterprise Financial UI
# ----------------------------------------------------------------------------
st.markdown("""
<style>
    /* Main Theme Overrides */
    .main {
        background-color: #F8F9FA;
    }
    /* Hero Banner */
    .hero-banner {
        background: linear-gradient(135deg, #0F2027 0%, #203A43 50%, #2C5364 100%);
        padding: 24px 32px;
        border-radius: 12px;
        color: #FFFFFF;
        margin-bottom: 24px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .hero-title {
        font-size: 28px;
        font-weight: 700;
        margin: 0;
        color: #FFFFFF;
    }
    .hero-subtitle {
        font-size: 14px;
        color: #B0BEC5;
        margin-top: 6px;
    }
    /* Metric Cards */
    .metric-card {
        background: #FFFFFF;
        border: 1px solid #E0E0E0;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 2px 6px rgba(0,0,0,0.04);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.08);
    }
    .metric-value {
        font-size: 24px;
        font-weight: 700;
        color: #0D47A1;
        margin-top: 4px;
    }
    .metric-label {
        font-size: 12px;
        font-weight: 600;
        color: #616161;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    /* Badges */
    .badge-ai {
        background-color: #E8F5E9;
        color: #2E7D32;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 12px;
    }
    .badge-offline {
        background-color: #FFF3E0;
        color: #E65100;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 12px;
    }
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# Sidebar Configuration
# ----------------------------------------------------------------------------
st.sidebar.title("🏦 CLO Studio Engine")
st.sidebar.caption("Automated CLO Analytics & Committee Prep System")

engine_mode = st.sidebar.radio(
    "Extraction Engine Mode",
    ["🤖 AI LLM Agent", "⚡ Standalone Offline Engine (No API Key)"],
    index=0 if os.getenv("OPENROUTER_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GROQ_API_KEY") else 1,
    help="AI LLM provides semantic extraction; Standalone Offline Engine uses rule-based parsing with 0 API dependencies."
)

is_offline = "Offline" in engine_mode

if not is_offline:
    provider = st.sidebar.selectbox(
        "AI Provider",
        ["openrouter", "gemini", "groq"],
        index=0,
        help="OpenRouter (broad model selection), Gemini (Google), Groq (ultra fast inference)."
    )
    ENV_FOR = {"openrouter": "OPENROUTER_API_KEY", "gemini": "GEMINI_API_KEY", "groq": "GROQ_API_KEY"}
    DEFAULT_MODEL = {
        "openrouter": "z-ai/glm-5.3-flash",
        "gemini": "gemini-2.5-flash",
        "groq": "qwen/qwen3.8-27b",
    }

    def _get_secret(key: str):
        try:
            return st.secrets.get(key)
        except Exception:
            return None

    stored_key = _get_secret(ENV_FOR[provider]) or os.getenv(ENV_FOR[provider], "")
    typed_key = st.sidebar.text_input(
        f"{provider} API Key (optional override)",
        value="",
        type="password",
        help=f"Leave blank to use key from {ENV_FOR[provider]} (secrets/env)"
    )
    api_key = typed_key or stored_key
    model = st.sidebar.text_input("Model", value=os.getenv("CLO_MODEL", DEFAULT_MODEL[provider]))
    allow_fallback = st.sidebar.checkbox("Auto Fallback to Offline Engine on API Error", value=True)
else:
    provider = "offline"
    api_key = "OFFLINE_RULE_BASED"
    model = "rule-based-engine"
    allow_fallback = True
    st.sidebar.info("⚡ Running in 100% Offline Rule-Based Mode. Zero API calls or keys required.")

# ----------------------------------------------------------------------------
# Session State Initialization & Helper Functions
# ----------------------------------------------------------------------------
if "extracted_data" not in st.session_state:
    st.session_state["extracted_data"] = None
if "memo_text" not in st.session_state:
    st.session_state["memo_text"] = ""


def _build_excel_buffer(data: dict):
    try:
        import pandas as pd
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            summary = pd.DataFrame({
                'Metric': ['Fund Name', 'Trustee', 'Portfolio Manager', 'Report Date',
                           'Closing Date', 'Portfolio Size ($M)', 'Total Loans', 'WAC (%)',
                           'WAL (years)', 'Weighted Avg Rating', 'Cumulative Default Rate (%)',
                           '30+ DPD ($M)', '60+ DPD ($M)', 'Compliance Status'],
                'Value': [data.get('fund_name', 'N/A'), data.get('trustee', 'N/A'),
                          data.get('portfolio_manager', 'N/A'), data.get('report_date', 'N/A'),
                          data.get('closing_date', 'N/A'), data.get('current_portfolio_size', 'N/A'),
                          data.get('total_loans', 'N/A'), data.get('wac', 'N/A'),
                          data.get('wal', 'N/A'), data.get('weighted_avg_rating', 'N/A'),
                          data.get('cumulative_default_rate', 'N/A'), data.get('30_plus_dpd', 'N/A'),
                          data.get('60_plus_dpd', 'N/A'), data.get('compliance_status', 'N/A')],
            })
            summary.to_excel(writer, sheet_name='Summary', index=False)
            if data.get('sector_breakdown'):
                pd.DataFrame([{'Sector': k, 'Allocation (%)': v}
                              for k, v in data['sector_breakdown'].items()]
                             ).to_excel(writer, sheet_name='Sectors', index=False)
            if data.get('credit_quality'):
                pd.DataFrame([{'Rating': k, 'Amount (%)': v}
                              for k, v in data['credit_quality'].items()]
                             ).to_excel(writer, sheet_name='Credit Quality', index=False)
            if data.get('class_notes'):
                pd.DataFrame(data['class_notes']).to_excel(writer, sheet_name='Class Notes', index=False)
            if data.get('covenants'):
                pd.DataFrame([{'Covenant': k, 'Status': v}
                              for k, v in data['covenants'].items()]
                             ).to_excel(writer, sheet_name='Covenants', index=False)
            if data.get('major_credit_events'):
                pd.DataFrame({'Event': data['major_credit_events']}
                             ).to_excel(writer, sheet_name='Credit Events', index=False)
        return buf
    except Exception as e:
        st.warning(f"Excel build warning: {e}")
        return None

# ----------------------------------------------------------------------------
# Hero Banner Header
# ----------------------------------------------------------------------------
engine_badge = '<span class="badge-offline">⚡ Standalone Offline Engine</span>' if is_offline else '<span class="badge-ai">🤖 AI LLM Engine</span>'

st.markdown(f"""
<div class="hero-banner">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h1 class="hero-title">🏦 CLO Surveillance & Refinancing Studio</h1>
            <div class="hero-subtitle">Structured Collateral Extraction • Portfolio Analytics • Committee Memo Generation</div>
        </div>
        <div>
            {engine_badge}
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# Main Navigation Workspaces (Tabs)
# ----------------------------------------------------------------------------
main_tabs = st.tabs([
    "📄 Upload & Preset Hub",
    "📈 Executive Dashboard",
    "✍️ Analyst Metric Editor",
    "🏛️ CLO Committee Studio",
    "🔍 Batch & Deal Compare"
])

# ----------------------------------------------------------------------------
# Tab 1: Upload & Preset Hub
# ----------------------------------------------------------------------------
with main_tabs[0]:
    st.subheader("📄 Memo Input & Preset Switcher")
    st.write("Load a sample CLO memo preset or upload your fund's surveillance/refinancing report.")

    # Preset Loader Buttons
    col_p1, col_p2, col_clear = st.columns([1, 1, 1])
    with col_p1:
        if st.button("📋 Load Surveillance Memo Sample", use_container_width=True):
            if os.path.exists("sample_clo_memo.txt"):
                with open("sample_clo_memo.txt", "r", encoding="utf-8") as f:
                    st.session_state["memo_text"] = f.read()
                st.success("Loaded sample_clo_memo.txt (Apex Senior Loan Fund IV)!")
                st.rerun()
    with col_p2:
        if st.button("🔄 Load Refinancing Memo Sample", use_container_width=True):
            if os.path.exists("sample_refi_memo.txt"):
                with open("sample_refi_memo.txt", "r", encoding="utf-8") as f:
                    st.session_state["memo_text"] = f.read()
                st.success("Loaded sample_refi_memo.txt (Horizon Senior Loan Fund II)!")
                st.rerun()
    with col_clear:
        if st.button("🧹 Clear Workspace", use_container_width=True):
            st.session_state["memo_text"] = ""
            st.session_state["extracted_data"] = None
            st.rerun()

    input_subtabs = st.tabs(["📄 Upload File", "✍️ Paste Text", "🔗 Fetch URL"])
    input_text = None

    with input_subtabs[0]:
        uploaded = st.file_uploader(
            "Choose a memo file (.txt, .md, or .pdf)",
            type=["txt", "md", "pdf"],
            key="file_uploader_input"
        )
        if uploaded is not None:
            if uploaded.type == "application/pdf":
                try:
                    import pdfplumber
                    with pdfplumber.open(io.BytesIO(uploaded.read())) as pdf:
                        input_text = "\n".join((page.extract_text() or "") for page in pdf.pages)
                    st.success(f"Parsed PDF ({len(pdf.pages)} pages).")
                except ImportError:
                    st.error("pdfplumber is not installed. Add it to requirements.txt or upload a .txt/.md file.")
            else:
                input_text = uploaded.read().decode("utf-8", errors="replace")

    with input_subtabs[1]:
        pasted_text = st.text_area(
            "Paste memo text content here",
            value=st.session_state.get("memo_text", ""),
            height=250,
            placeholder="Paste CLO surveillance or refinancing memo text...",
            key="pasted_text_area"
        )
        if pasted_text and pasted_text.strip():
            input_text = pasted_text

    with input_subtabs[2]:
        link = st.text_input("Public Memo URL", placeholder="https://example.com/memo.txt", key="url_memo_input")
        if link and st.button("Fetch Memo Content"):
            import urllib.request
            try:
                req = urllib.request.Request(link, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    raw = resp.read()
                input_text = raw.decode("utf-8", errors="replace")
                st.session_state["memo_text"] = input_text
                st.success("Fetched URL content successfully!")
            except Exception as e:
                st.error(f"Failed to fetch link: {e}")

    memo_to_run = input_text or st.session_state.get("memo_text", "")

    if memo_to_run:
        st.markdown("##### Current Memo Preview")
        st.text_area("Preview", memo_to_run[:2000], height=180, disabled=True)

    st.markdown("---")
    if st.button("🚀 Process & Extract CLO Data", type="primary", use_container_width=True):
        if not memo_to_run or not memo_to_run.strip():
            st.error("Please select a preset or upload memo content first.")
        else:
            st.session_state["memo_text"] = memo_to_run
            try:
                with st.spinner(f"Extracting CLO metrics using [{provider}] engine..."):
                    extractor = CLOExtractor(
                        api_key=api_key if not is_offline else None,
                        model=model,
                        provider=provider if not is_offline else "offline",
                        allow_fallback=allow_fallback
                    )
                    data = extractor.process_text(memo_to_run)

                if data:
                    st.session_state["extracted_data"] = data
                    st.success("✨ Extraction complete! Head over to 'Executive Dashboard' or 'CLO Committee Studio'.")
                else:
                    st.error("Extraction failed to return structured data.")
            except Exception as e:
                st.exception(e)

# ----------------------------------------------------------------------------
# Tab 2: Executive Dashboard
# ----------------------------------------------------------------------------
with main_tabs[1]:
    data = st.session_state.get("extracted_data")
    if not data:
        st.info("💡 No data processed yet. Please load a preset or extract a memo in 'Upload & Preset Hub'.")
    else:
        engine_used = data.get("_metadata", {}).get("engine", provider)
        st.markdown(f"### 📊 Portfolio Dashboard — **{data.get('fund_name', 'CLO Portfolio')}**")
        st.caption(f"Extraction Engine: `{engine_used}` | Report Date: {data.get('report_date', 'N/A')} | Manager: {data.get('portfolio_manager', 'N/A')}")

        # Top Metric Cards
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.markdown(f'<div class="metric-card"><div class="metric-label">Portfolio Size</div><div class="metric-value">${data.get("current_portfolio_size", 0)}M</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="metric-card"><div class="metric-label">Total Loans</div><div class="metric-value">{data.get("total_loans", 0)}</div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="metric-card"><div class="metric-label">WAC</div><div class="metric-value">{data.get("wac", 0)}%</div></div>', unsafe_allow_html=True)
        c4.markdown(f'<div class="metric-card"><div class="metric-label">WAL</div><div class="metric-value">{data.get("wal", 0)}y</div></div>', unsafe_allow_html=True)
        c5.markdown(f'<div class="metric-card"><div class="metric-label">Default Rate</div><div class="metric-value">{data.get("cumulative_default_rate", 0)}%</div></div>', unsafe_allow_html=True)
        c6.markdown(f'<div class="metric-card"><div class="metric-label">30+ DPD</div><div class="metric-value">${data.get("30_plus_dpd", 0)}M</div></div>', unsafe_allow_html=True)

        st.markdown("---")

        # Interactive Visualizations
        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            st.markdown("#### 🏢 Industry Sector Breakdown")
            sectors = data.get("sector_breakdown", {})
            if sectors and HAS_PLOTLY:
                # Clean up sector percentages for donut chart
                sector_names = list(sectors.keys())
                sector_vals = []
                for v in sectors.values():
                    try:
                        clean_v = float(str(v).replace("%", "").split("(")[0].strip())
                    except ValueError:
                        clean_v = 10.0
                    sector_vals.append(clean_v)

                fig_sec = px.pie(
                    names=sector_names,
                    values=sector_vals,
                    hole=0.4,
                    color_discrete_sequence=px.colors.sequential.Blues_r
                )
                fig_sec.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=300)
                st.plotly_chart(fig_sec, use_container_width=True)
            elif sectors:
                st.json(sectors)

        with col_chart2:
            st.markdown("#### 📊 Credit Quality Distribution")
            cq = data.get("credit_quality", {})
            if cq and HAS_PLOTLY:
                cq_names = list(cq.keys())
                cq_vals = []
                for v in cq.values():
                    try:
                        clean_v = float(str(v).replace("%", "").split("(")[0].strip())
                    except ValueError:
                        clean_v = 5.0
                    cq_vals.append(clean_v)

                fig_cq = px.bar(
                    x=cq_names,
                    y=cq_vals,
                    labels={"x": "Rating Bucket", "y": "Allocation (%)"},
                    color=cq_vals,
                    color_continuous_scale="Blues"
                )
                fig_cq.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=300)
                st.plotly_chart(fig_cq, use_container_width=True)
            elif cq:
                st.json(cq)

        st.markdown("---")

        # Capital Structure & Class Notes Table
        st.markdown("#### 📑 Debt & Equity Tranche Waterfall")
        notes = data.get("class_notes", [])
        if notes:
            st.dataframe(notes, use_container_width=True)

        col_cov, col_evt = st.columns(2)
        with col_cov:
            st.markdown("#### ⚖️ Covenant Compliance")
            covs = data.get("covenants", {})
            for k, v in covs.items():
                st.markdown(f"- **{k}:** `{v}`")
        with col_evt:
            st.markdown("#### ⚠️ Major Credit Events")
            evts = data.get("major_credit_events", [])
            for e in evts:
                st.write(f"- {e}")

        # Download Actions
        st.markdown("---")
        c_dl1, c_dl2 = st.columns(2)
        with c_dl1:
            json_bytes = json.dumps(data, indent=2).encode("utf-8")
            st.download_button(
                "⬇️ Download Structured JSON Data",
                data=json_bytes,
                file_name="clo_extraction.json",
                mime="application/json",
                use_container_width=True
            )
        with c_dl2:
            excel_buf = _build_excel_buffer(data)
            if excel_buf:
                st.download_button(
                    "⬇️ Download Multi-Sheet Excel Workbook (.xlsx)",
                    data=excel_buf.getvalue(),
                    file_name="clo_extraction.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

# ----------------------------------------------------------------------------
# Tab 3: Analyst Metric Editor
# ----------------------------------------------------------------------------
with main_tabs[2]:
    data = st.session_state.get("extracted_data")
    if not data:
        st.info("💡 Please extract a memo first in 'Upload & Preset Hub' to edit metrics.")
    else:
        st.subheader("✍️ Analyst Data Audit & Override Grid")
        st.write("Audit and adjust extracted parameters before generating final committee reports.")

        with st.form("metric_editor_form"):
            col_e1, col_e2, col_e3 = st.columns(3)
            with col_e1:
                fund_name_edit = st.text_input("Fund Name", value=str(data.get("fund_name", "")))
                manager_edit = st.text_input("Portfolio Manager", value=str(data.get("portfolio_manager", "")))
                trustee_edit = st.text_input("Trustee", value=str(data.get("trustee", "")))
                report_date_edit = st.text_input("Report Date", value=str(data.get("report_date", "")))

            with col_e2:
                size_edit = st.number_input("Portfolio Size ($M)", value=float(data.get("current_portfolio_size", 0.0)))
                loans_edit = st.number_input("Total Loans Count", value=int(data.get("total_loans", 0)))
                wac_edit = st.number_input("WAC (%)", value=float(data.get("wac", 0.0)))
                wal_edit = st.number_input("WAL (years)", value=float(data.get("wal", 0.0)))

            with col_e3:
                def_rate_edit = st.number_input("Cumulative Default Rate (%)", value=float(data.get("cumulative_default_rate", 0.0)))
                dpd30_edit = st.number_input("30+ DPD ($M)", value=float(data.get("30_plus_dpd", 0.0)))
                rating_edit = st.text_input("Weighted Avg Rating", value=str(data.get("weighted_avg_rating", "")))
                refi_window_edit = st.text_input("Refinancing Window", value=str(data.get("refinancing_window", "")))

            comp_status_edit = st.text_input("Compliance Status", value=str(data.get("compliance_status", "")))

            save_submitted = st.form_submit_button("💾 Save & Apply Overrides", use_container_width=True)

            if save_submitted:
                data["fund_name"] = fund_name_edit
                data["portfolio_manager"] = manager_edit
                data["trustee"] = trustee_edit
                data["report_date"] = report_date_edit
                data["current_portfolio_size"] = size_edit
                data["total_loans"] = loans_edit
                data["wac"] = wac_edit
                data["wal"] = wal_edit
                data["cumulative_default_rate"] = def_rate_edit
                data["30_plus_dpd"] = dpd30_edit
                data["weighted_avg_rating"] = rating_edit
                data["refinancing_window"] = refi_window_edit
                data["compliance_status"] = comp_status_edit

                st.session_state["extracted_data"] = data
                st.success("✅ Overrides saved successfully! Updated values will reflect in Executive Dashboard and Committee Package.")

# ----------------------------------------------------------------------------
# Tab 4: CLO Committee Studio
# ----------------------------------------------------------------------------
with main_tabs[3]:
    data = st.session_state.get("extracted_data")
    if not data:
        st.info("💡 Please extract a memo first in 'Upload & Preset Hub' to use Committee Studio.")
    else:
        st.subheader("🏛️ CLO Investment & Surveillance Committee Studio")
        st.write("Format executive committee briefs, refinancing proposals, and action item lists.")

        col_st1, col_st2 = st.columns(2)
        with col_st1:
            rec_action = st.selectbox(
                "Committee Action Recommendation",
                ["Refinance Portfolio", "Hold & Monitor", "Reinvest Cashflows", "Restructure Tranches", "De-Risk High Betas"],
                index=0
            )
            target_period_in = st.text_input(
                "Target Execution Timeframe",
                value=data.get("refinancing_window", "Q1 2027")
            )
        with col_st2:
            analyst_rationale = st.text_area(
                "Analyst Commentary & Rationale",
                value=f"The current market environment offers tight spreads for {data.get('fund_name')}. Asset coverage cushions remain healthy.",
                height=110
            )

        st.markdown("#### Action Items Checklist Builder")
        act_1 = st.text_input("Action Item 1", value="Monitor healthcare & energy obligors for rating migration.", key="act1_in")
        act_2 = st.text_input("Action Item 2", value="Prepare refinancing syndicate terms and engage dealer desk.", key="act2_in")
        act_3 = st.text_input("Action Item 3", value="Review asset coverage test cushion prior to next distribution.", key="act3_in")

        action_items_list = [a for a in [act_1, act_2, act_3] if a.strip()]

        if st.button("📝 Generate CLO Committee Memorandum Package", type="primary", use_container_width=True):
            gen = CommitteeMemoGenerator(data)
            md_memo = gen.generate_markdown_brief(
                recommendation=rec_action,
                target_period=target_period_in,
                analyst_notes=analyst_rationale,
                action_items=action_items_list
            )
            txt_memo = gen.generate_text_brief(
                recommendation=rec_action,
                target_period=target_period_in,
                analyst_notes=analyst_rationale
            )
            html_memo = gen.generate_html_brief(
                recommendation=rec_action,
                target_period=target_period_in,
                analyst_notes=analyst_rationale,
                action_items=action_items_list
            )
            st.session_state["committee_md_out"] = md_memo
            st.session_state["committee_txt_out"] = txt_memo
            st.session_state["committee_html_out"] = html_memo
            st.success("🎉 Committee Memorandum Package generated successfully!")

        if "committee_md_out" in st.session_state:
            st.markdown("---")
            st.subheader("📋 Executive Committee Memorandum Preview")

            c_exp1, c_exp2, c_exp3 = st.columns(3)
            with c_exp1:
                st.download_button(
                    "⬇️ Download Markdown Brief (.md)",
                    data=st.session_state["committee_md_out"].encode("utf-8"),
                    file_name=f"CLO_Committee_Memo_{data.get('fund_name', 'Deal').replace(' ', '_')}.md",
                    mime="text/markdown",
                    use_container_width=True
                )
            with c_exp2:
                st.download_button(
                    "⬇️ Download Plain Text Memo (.txt)",
                    data=st.session_state["committee_txt_out"].encode("utf-8"),
                    file_name=f"CLO_Committee_Memo_{data.get('fund_name', 'Deal').replace(' ', '_')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            with c_exp3:
                st.download_button(
                    "⬇️ Download Printable HTML Report (.html)",
                    data=st.session_state["committee_html_out"].encode("utf-8"),
                    file_name=f"CLO_Committee_Memo_{data.get('fund_name', 'Deal').replace(' ', '_')}.html",
                    mime="text/html",
                    use_container_width=True
                )

            st.markdown(st.session_state["committee_md_out"])

# ----------------------------------------------------------------------------
# Tab 5: Batch & Deal Compare
# ----------------------------------------------------------------------------
with main_tabs[4]:
    st.subheader("🔍 Portfolio Deal Comparison Workspace")
    st.write("Compare metrics between sample surveillance and refinancing reports side by side.")

    if st.button("⚡ Run Preset Side-by-Side Comparison"):
        if os.path.exists("sample_clo_memo.txt") and os.path.exists("sample_refi_memo.txt"):
            from offline_extractor import OfflineCLOExtractor
            ext = OfflineCLOExtractor()

            with open("sample_clo_memo.txt", "r", encoding="utf-8") as f:
                d1 = ext.extract(f.read())
            with open("sample_refi_memo.txt", "r", encoding="utf-8") as f:
                d2 = ext.extract(f.read())

            col_deal1, col_deal2 = st.columns(2)

            with col_deal1:
                st.markdown(f"#### 📄 {d1.get('fund_name')}")
                st.json({
                    "Portfolio Size ($M)": d1.get("current_portfolio_size"),
                    "Total Loans": d1.get("total_loans"),
                    "WAC": f"{d1.get('wac')}%",
                    "WAL": f"{d1.get('wal')} yrs",
                    "Default Rate": f"{d1.get('cumulative_default_rate')}%",
                    "Compliance": d1.get("compliance_status")
                })

            with col_deal2:
                st.markdown(f"#### 📄 {d2.get('fund_name')}")
                st.json({
                    "Portfolio Size ($M)": d2.get("current_portfolio_size"),
                    "Total Loans": d2.get("total_loans"),
                    "WAC": f"{d2.get('wac')}%",
                    "WAL": f"{d2.get('wal')} yrs",
                    "Default Rate": f"{d2.get('cumulative_default_rate')}%",
                    "Compliance": d2.get("compliance_status")
                })
        else:
            st.warning("Sample memo files not found.")
