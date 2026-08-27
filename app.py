#!/usr/bin/env python3
"""
CLO Surveillance & Refinancing Memo Extraction — Streamlit UI
Extracts structured financial metrics from CLO memos and generates executive
CLO Committee Memorandum packages using AI LLM agents or Standalone Offline Engines.

Run locally: streamlit run app.py
"""

import io
import os
import json
import streamlit as st

from clo_extractor import CLOExtractor
from committee_memo_generator import CommitteeMemoGenerator

st.set_page_config(
    page_title="CLO Memo Extractor & Committee Studio",
    page_icon="🏦",
    layout="wide",
)

# ----------------------------------------------------------------------------
# Sidebar Configuration
# ----------------------------------------------------------------------------
st.sidebar.title("🏦 CLO Memo Studio")
st.sidebar.caption("Automated CLO Surveillance & Committee Prep Engine")

engine_mode = st.sidebar.radio(
    "Extraction Engine",
    ["🤖 AI LLM Agent", "⚡ Standalone Offline Engine (No API Key)"],
    index=0 if os.getenv("OPENROUTER_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GROQ_API_KEY") else 1,
    help="Select AI LLM for semantic extraction or Standalone Offline Engine for 100% offline rule-based parsing."
)

is_offline = "Offline" in engine_mode

if not is_offline:
    provider = st.sidebar.selectbox(
        "AI Provider",
        ["openrouter", "gemini", "groq"],
        index=0,
        help="OpenRouter (many models), Gemini (Google), Groq (fast open models)."
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
        help=f"Leave blank to use {ENV_FOR[provider]} env var or secrets.toml"
    )
    api_key = typed_key or stored_key

    model = st.sidebar.text_input(
        "Model",
        value=os.getenv("CLO_MODEL", DEFAULT_MODEL[provider]),
        help=f"Default for {provider}: {DEFAULT_MODEL[provider]}"
    )

    allow_fallback = st.sidebar.checkbox(
        "Auto Fallback to Offline Engine on API Error",
        value=True,
        help="If LLM call fails or key is missing, automatically fallback to offline rule-based engine."
    )
else:
    provider = "offline"
    api_key = "OFFLINE_RULE_BASED"
    model = "rule-based-engine"
    allow_fallback = True
    st.sidebar.info("⚡ Operating in 100% Offline Rule-Based Mode. No API key required!")

# ----------------------------------------------------------------------------
# Session State Initialization
# ----------------------------------------------------------------------------
if "extracted_data" not in st.session_state:
    st.session_state["extracted_data"] = None
if "memo_text" not in st.session_state:
    st.session_state["memo_text"] = ""

# ----------------------------------------------------------------------------
# Main Title & Subtitle
# ----------------------------------------------------------------------------
st.title("🏦 CLO Surveillance Memo Extraction & Committee Studio")
st.write(
    "Extract structured deal analytics from CLO surveillance and refinancing memos. "
    "Analysts can review extracted metrics and instantly generate executive **CLO Committee Packages**."
)

main_tabs = st.tabs(["📄 Upload & Extract Memo", "📊 Extracted Metrics & Excel", "🏛️ CLO Committee Studio"])

# ----------------------------------------------------------------------------
# Tab 1: Upload & Extract Memo
# ----------------------------------------------------------------------------
with main_tabs[0]:
    input_subtabs = st.tabs(["📄 Upload File", "✍️ Paste Text", "🔗 Fetch URL"])
    input_text = None

    with input_subtabs[0]:
        uploaded = st.file_uploader(
            "Choose a memo file (.txt, .md, or .pdf)",
            type=["txt", "md", "pdf"],
            key="file_uploader"
        )
        if uploaded is not None:
            if uploaded.type == "application/pdf":
                try:
                    import pdfplumber
                    with pdfplumber.open(io.BytesIO(uploaded.read())) as pdf:
                        input_text = "\n".join((page.extract_text() or "") for page in pdf.pages)
                    st.success(f"Parsed PDF ({len(pdf.pages)} pages).")
                except ImportError:
                    st.error("pdfplumber is not installed. Upload a .txt/.md file or install pdfplumber.")
            else:
                input_text = uploaded.read().decode("utf-8", errors="replace")

            if input_text:
                st.text_area("Memo Text Preview", input_text[:2000], height=200, disabled=True)

    with input_subtabs[1]:
        pasted_text = st.text_area(
            "Paste memo text here",
            height=250,
            placeholder="Paste the full CLO memo content...",
            key="pasted_text_input"
        )
        if pasted_text and pasted_text.strip():
            input_text = pasted_text

    with input_subtabs[2]:
        link = st.text_input("Memo URL", placeholder="https://example.com/memo.txt", key="url_input")
        if link and st.button("Fetch URL Content"):
            import urllib.request
            try:
                req = urllib.request.Request(link, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    raw = resp.read()
                if link.lower().endswith(".pdf") or raw[:4] == b"%PDF":
                    st.warning("URL appears to be a PDF. Please download and upload directly.")
                else:
                    input_text = raw.decode("utf-8", errors="replace")
                    st.text_area("Fetched Content Preview", input_text[:2000], height=200, disabled=True)
            except Exception as e:
                st.error(f"Failed to fetch link: {e}")

    st.markdown("---")

    # Load Sample Memo Button for fast testing
    col_run, col_sample = st.columns([3, 1])
    with col_sample:
        if st.button("📋 Load Sample Memo"):
            if os.path.exists("sample_clo_memo.txt"):
                with open("sample_clo_memo.txt", "r", encoding="utf-8") as f:
                    sample_txt = f.read()
                st.session_state["memo_text"] = sample_txt
                st.success("Loaded sample_clo_memo.txt!")
                st.rerun()

    with col_run:
        if st.button("🚀 Extract CLO Data", type="primary", use_container_width=True):
            memo_to_process = input_text or st.session_state.get("memo_text")
            if not memo_to_process or not memo_to_process.strip():
                st.error("Please upload, paste, or load memo content first.")
            else:
                st.session_state["memo_text"] = memo_to_process
                try:
                    with st.spinner(f"Processing memo with provider [{provider}]..."):
                        extractor = CLOExtractor(
                            api_key=api_key if not is_offline else None,
                            model=model,
                            provider=provider if not is_offline else "offline",
                            allow_fallback=allow_fallback
                        )
                        data = extractor.process_text(memo_to_process)

                    if data:
                        st.session_state["extracted_data"] = data
                        st.success("Extraction complete! View results under 'Extracted Metrics & Excel' or 'CLO Committee Studio'.")
                    else:
                        st.error("Extraction returned no data. Check input memo format.")
                except Exception as e:
                    st.exception(e)

# ----------------------------------------------------------------------------
# Tab 2: Extracted Metrics & Excel
# ----------------------------------------------------------------------------
with main_tabs[1]:
    data = st.session_state.get("extracted_data")
    if not data:
        st.info("💡 No data extracted yet. Go to 'Upload & Extract Memo' tab to process a CLO memo.")
    else:
        engine_info = data.get("_metadata", {}).get("engine", provider)
        if "offline" in engine_info.lower() or "fallback" in engine_info.lower() or "rule_based" in engine_info.lower():
            st.info(f"⚡ Extracted via Standalone Rule-Based Engine (`{engine_info}`)")
        else:
            st.success(f"🤖 Extracted via AI LLM Agent (`{engine_info}`)")

        # Metric Cards Header
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Portfolio Size", f"${data.get('current_portfolio_size', 'N/A')}M")
        c2.metric("Total Loans", f"{data.get('total_loans', 'N/A')}")
        c3.metric("WAC", f"{data.get('wac', 'N/A')}%")
        c4.metric("WAL", f"{data.get('wal', 'N/A')} yrs")
        c5.metric("Default Rate", f"{data.get('cumulative_default_rate', 'N/A')}%")

        st.markdown("---")

        sub_detail_tabs = st.tabs([
            "📌 Summary", "📝 Class Notes", "🏢 Sector Breakdown", "📊 Credit Quality", "⚖️ Covenants", "⚠️ Credit Events", "🔍 JSON Data"
        ])

        with sub_detail_tabs[0]:
            st.json({
                "Fund Name": data.get("fund_name"),
                "Trustee": data.get("trustee"),
                "Portfolio Manager": data.get("portfolio_manager"),
                "Report Date": data.get("report_date"),
                "Closing Date": data.get("closing_date"),
                "Weighted Avg Rating": data.get("weighted_avg_rating"),
                "30+ Days Past Due ($M)": data.get("30_plus_dpd"),
                "60+ Days Past Due ($M)": data.get("60_plus_dpd"),
                "Refinancing Window": data.get("refinancing_window"),
                "Compliance Status": data.get("compliance_status")
            })

        with sub_detail_tabs[1]:
            notes = data.get("class_notes", [])
            if notes:
                st.table(notes)
            else:
                st.write("No class notes details found.")

        with sub_detail_tabs[2]:
            sectors = data.get("sector_breakdown", {})
            if sectors:
                st.json(sectors)

        with sub_detail_tabs[3]:
            cq = data.get("credit_quality", {})
            if cq:
                st.json(cq)

        with sub_detail_tabs[4]:
            covs = data.get("covenants", {})
            if covs:
                st.json(covs)

        with sub_detail_tabs[5]:
            evts = data.get("major_credit_events", [])
            if evts:
                for e in evts:
                    st.write(f"- {e}")

        with sub_detail_tabs[6]:
            st.json(data)

        # Downloads
        st.markdown("---")
        col_dl_json, col_dl_xlsx = st.columns(2)
        with col_dl_json:
            json_bytes = json.dumps(data, indent=2).encode("utf-8")
            st.download_button(
                "⬇️ Download JSON Data",
                data=json_bytes,
                file_name="clo_extraction.json",
                mime="application/json",
                use_container_width=True
            )

        with col_dl_xlsx:
            excel_buf = _build_excel_buffer(data)
            if excel_buf:
                st.download_button(
                    "⬇️ Download Excel Workbook (.xlsx)",
                    data=excel_buf.getvalue(),
                    file_name="clo_extraction.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

# ----------------------------------------------------------------------------
# Tab 3: CLO Committee Prep Studio
# ----------------------------------------------------------------------------
with main_tabs[2]:
    data = st.session_state.get("extracted_data")
    if not data:
        st.info("💡 Please extract a memo first in the 'Upload & Extract Memo' tab to generate a Committee Brief.")
    else:
        st.subheader("🏛️ CLO Investment & Surveillance Committee Studio")
        st.write("Review extracted details, add analyst recommendations, and generate committee packages.")

        col_cfg1, col_cfg2 = st.columns(2)
        with col_cfg1:
            rec_option = st.selectbox(
                "Committee Action Recommendation",
                ["Refinance Portfolio", "Hold & Monitor", "Reinvest Cashflows", "Restructure Tranches", "De-Risk High Betas"],
                index=0
            )
            target_window = st.text_input(
                "Target Execution Window",
                value=data.get("refinancing_window", "Q1 2027")
            )

        with col_cfg2:
            analyst_notes = st.text_area(
                "Analyst Commentary & Rationale",
                value="Spread environment remains favorable for refinancing. Asset coverage tests remain compliant with sound cushion.",
                height=110
            )

        st.markdown("#### Action Items Checklist")
        action_1 = st.text_input("Action Item 1", value="Monitor healthcare and energy sector obligors for potential credit migration.")
        action_2 = st.text_input("Action Item 2", value="Prepare refinancing syndicate terms and review manager fee agreements.")
        action_3 = st.text_input("Action Item 3", value="Verify quarterly interest coverage test cushion prior to next payment date.")

        action_list = [a for a in [action_1, action_2, action_3] if a.strip()]

        if st.button("📝 Generate CLO Committee Package", type="primary"):
            generator = CommitteeMemoGenerator(data)
            md_brief = generator.generate_markdown_brief(
                recommendation=rec_option,
                target_period=target_window,
                analyst_notes=analyst_notes,
                action_items=action_list
            )
            txt_brief = generator.generate_text_brief(
                recommendation=rec_option,
                target_period=target_window,
                analyst_notes=analyst_notes
            )
            st.session_state["committee_md"] = md_brief
            st.session_state["committee_txt"] = txt_brief
            st.success("Committee Memorandum Package generated successfully!")

        if "committee_md" in st.session_state:
            st.markdown("---")
            st.subheader("📋 CLO Committee Memorandum Preview")

            col_mb_dl1, col_mb_dl2 = st.columns(2)
            with col_mb_dl1:
                st.download_button(
                    "⬇️ Download Committee Memo (.md)",
                    data=st.session_state["committee_md"].encode("utf-8"),
                    file_name=f"CLO_Committee_Memo_{data.get('fund_name', 'Deal').replace(' ', '_')}.md",
                    mime="text/markdown",
                    use_container_width=True
                )
            with col_mb_dl2:
                st.download_button(
                    "⬇️ Download Plain Text Brief (.txt)",
                    data=st.session_state["committee_txt"].encode("utf-8"),
                    file_name=f"CLO_Committee_Memo_{data.get('fund_name', 'Deal').replace(' ', '_')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )

            st.markdown(st.session_state["committee_md"])


# ----------------------------------------------------------------------------
# Helper: Excel Builder
# ----------------------------------------------------------------------------
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
