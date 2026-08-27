#!/usr/bin/env python3
"""
CLO Surveillance Memo Extraction — Streamlit UI
Upload a memo file, paste text, or paste a link; extract structured CLO data
and download JSON / Excel results.

Run locally:  streamlit run app.py
Hosted (e.g. Streamlit Cloud): set OPENROUTER_API_KEY in the app's secrets.
"""

import io
import os

import streamlit as st

from clo_extractor import CLOExtractor

st.set_page_config(
    page_title="CLO Memo Extractor",
    page_icon="🏦",
    layout="wide",
)

# ----------------------------------------------------------------------------
# Sidebar: configuration
# ----------------------------------------------------------------------------
st.sidebar.title("🏦 CLO Memo Extractor")
st.sidebar.caption("Extract structured data from CLO surveillance memos.")

provider = st.sidebar.selectbox(
    "Provider",
    ["openrouter", "gemini", "groq"],
    index=0,
    help="OpenRouter (many models), Gemini (Google), Groq (fast open models).",
)

# Per-provider key env mapping
ENV_FOR = {"openrouter": "OPENROUTER_API_KEY", "gemini": "GEMINI_API_KEY", "groq": "GROQ_API_KEY"}
DEFAULT_MODEL = {
    "openrouter": "z-ai/glm-5.3-flash",
    "gemini": "gemini-2.5-flash",
    "groq": "qwen/qwen3.8-27b",
}

# Resolve the key from Streamlit secrets / env WITHOUT ever showing it in the UI.
# The sidebar field is left blank; the user only types a key here to override.
def _get_secret(key: str):
    # Streamlit Cloud / local .streamlit/secrets.toml
    try:
        return st.secrets.get(key)
    except Exception:
        return None

stored_key = _get_secret(ENV_FOR[provider]) or os.getenv(ENV_FOR[provider], "")

typed_key = st.sidebar.text_input(
    f"{provider} API Key (optional override)",
    value="",
    type="password",
    help=(
        f"Leave blank to use the key from {ENV_FOR[provider]} "
        f"(Streamlit secrets or env var). Type here only to override it. "
        f"Key is never displayed."
    ),
)
# Use the typed key if provided, otherwise fall back to the stored secret.
api_key = typed_key or stored_key
model = st.sidebar.text_input(
    "Model",
    value=os.getenv("CLO_MODEL", DEFAULT_MODEL[provider]),
    help=f"Default for {provider}: {DEFAULT_MODEL[provider]}",
)

# ----------------------------------------------------------------------------
# Main UI
# ----------------------------------------------------------------------------
st.title("CLO Surveillance Memo Extraction")
st.write(
    "Upload a memo file, paste memo text, or paste a public link to a text/PDF. "
    "The extractor returns structured CLO data you can download as JSON or Excel."
)

tab_file, tab_text, tab_link = st.tabs(["📄 Upload file", "✍️ Paste text", "🔗 Paste link"])

memo_text = None

with tab_file:
    uploaded = st.file_uploader(
        "Choose a memo file (.txt, .md, or .pdf)",
        type=["txt", "md", "pdf"],
    )
    if uploaded is not None:
        if uploaded.type == "application/pdf":
            try:
                import pdfplumber
                with pdfplumber.open(io.BytesIO(uploaded.read())) as pdf:
                    memo_text = "\n".join(
                        (page.extract_text() or "") for page in pdf.pages
                    )
                st.success(f"Parsed PDF ({len(pdf.pages)} pages).")
            except ImportError:
                st.error(
                    "pdfplumber is not installed. Add it to requirements.txt "
                    "or upload a .txt/.md file."
                )
        else:
            memo_text = uploaded.read().decode("utf-8", errors="replace")
        if memo_text:
            st.text_area("Preview", memo_text[:2000], height=200, disabled=True)

with tab_text:
    memo_text = st.text_area(
        "Paste memo text here",
        height=300,
        placeholder="Paste the full CLO memo content...",
    )

with tab_link:
    link = st.text_input(
        "Memo URL",
        placeholder="https://example.com/memo.txt",
    )
    if link:
        if st.button("Fetch link"):
            import urllib.request

            try:
                req = urllib.request.Request(link, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    raw = resp.read()
                # Try decode as text; PDFs get a warning
                if link.lower().endswith(".pdf") or raw[:4] == b"%PDF":
                    st.warning(
                        "Link appears to be a PDF. PDF parsing from a URL needs "
                        "pdfplumber + a download step; try uploading the PDF directly."
                    )
                else:
                    memo_text = raw.decode("utf-8", errors="replace")
                    st.text_area("Fetched content", memo_text[:2000], height=200, disabled=True)
            except Exception as e:
                st.error(f"Failed to fetch link: {e}")

# ----------------------------------------------------------------------------
# Run extraction
# ----------------------------------------------------------------------------
if st.button("🚀 Extract data", type="primary"):
    if not api_key:
        st.error("Please provide your OpenRouter API key in the sidebar.")
    elif not memo_text or not memo_text.strip():
        st.error("Please upload, paste, or fetch some memo content first.")
    else:
        try:
            extractor = CLOExtractor(api_key=api_key, model=model, provider=provider)
            with st.spinner(f"Extracting with {model}..."):
                data = extractor.process_text(memo_text)
            if data:
                st.success("Extraction complete!")

                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Summary")
                    st.json({
                        k: data.get(k) for k in (
                            "fund_name", "trustee", "portfolio_manager",
                            "report_date", "current_portfolio_size", "total_loans",
                            "wac", "wal", "cumulative_default_rate",
                            "compliance_status",
                        )
                    })
                with col2:
                    st.subheader("Full JSON")
                    st.json(data)

                # Download buttons
                import json

                json_bytes = json.dumps(data, indent=2).encode("utf-8")
                st.download_button(
                    "⬇️ Download JSON",
                    data=json_bytes,
                    file_name="clo_extraction.json",
                    mime="application/json",
                )

                # Excel (needs pandas)
                if extractor.__class__ and _has_pandas():
                    excel_buf = _build_excel(data)
                    if excel_buf:
                        st.download_button(
                            "⬇️ Download Excel",
                            data=excel_buf.getvalue(),
                            file_name="clo_extraction.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        )
            else:
                st.error("Extraction returned no data. Check the model response / prompt.")
        except Exception as e:
            st.exception(e)


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def _has_pandas() -> bool:
    try:
        import pandas  # noqa: F401
        return True
    except ImportError:
        return False


def _build_excel(data: dict):
    try:
        import io as _io
        import pandas as pd
        from clo_extractor import CLOExtractor as _CE  # noqa: F401
        buf = _io.BytesIO()
        # Reuse the save_excel logic via a temporary extractor instance writing to buf
        extractor = CLOExtractor.__new__(CLOExtractor)
        # Build workbook manually to write into buffer
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
        st.warning(f"Excel build skipped: {e}")
        return None
