#!/usr/bin/env python3
"""
CLO Deal Tracker & Document Download Automation
Standalone Streamlit page — import from app.py via sidebar radio.
"""

import os, io, json, zipfile
import streamlit as st
import pandas as pd
from datetime import datetime

from deal_registry import (
    load_deals, save_deals, get_analysts, deals_needing_docs,
    add_deal, update_doc_url, update_doc_status,
    DOC_TYPES, STATUS_CHOICES,
)
from doc_downloader import download_deal_docs, list_downloaded, DOWNLOAD_ROOT

# ─────────────────────────────────────────────────────────────────────────────
# Status badge colours
# ─────────────────────────────────────────────────────────────────────────────
STATUS_COLOUR = {
    "Pending Upload": "#FF8F00",
    "Uploaded":       "#2E7D32",
    "Downloading":    "#1565C0",
    "Failed":         "#C62828",
    "Not Required":   "#757575",
}

def status_badge(status: str) -> str:
    colour = STATUS_COLOUR.get(status, "#333")
    return (f'<span style="background:{colour};color:#fff;padding:2px 8px;'
            f'border-radius:4px;font-size:11px;font-weight:600">{status}</span>')


def doc_summary(docs: dict) -> str:
    """Compact summary: ✅3  ⏳2  ❌1  ⬜1"""
    from collections import Counter
    counts = Counter(v["status"] for v in docs.values())
    parts = []
    if counts.get("Uploaded"):        parts.append(f"✅ {counts['Uploaded']}")
    if counts.get("Pending Upload"):  parts.append(f"⏳ {counts['Pending Upload']}")
    if counts.get("Failed"):          parts.append(f"❌ {counts['Failed']}")
    if counts.get("Not Required"):    parts.append(f"⬜ {counts['Not Required']}")
    return "  ".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
def render():
    """Main render function — called from app.py."""

    st.markdown("## 📋 Deal Tracker & Document Automation")
    st.caption("Track document status per deal · Filter by analyst · Auto-download from internal portal")
    st.divider()

    # ── Load registry ────────────────────────────────────────────────────────
    if "deals" not in st.session_state:
        st.session_state["deals"] = load_deals()
    deals = st.session_state["deals"]

    analysts = ["All Analysts"] + get_analysts(deals)

    # ── Sidebar controls (scoped to tracker) ─────────────────────────────────
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔍 Tracker Filters")

    selected_analyst = st.sidebar.selectbox("Filter by Analyst", analysts, index=0)
    show_needs_action = st.sidebar.checkbox("Show only deals needing action", value=False)
    status_filter = st.sidebar.multiselect(
        "Filter by Doc Status",
        STATUS_CHOICES,
        default=[],
        help="Leave empty to show all statuses.",
    )

    # Portal credentials (optional — stored only in session)
    st.sidebar.markdown("### 🔐 Portal Credentials")
    st.sidebar.caption("Used only for authenticated downloads. Not persisted to disk.")
    portal_user = st.sidebar.text_input("Portal Username", key="portal_user")
    portal_pass = st.sidebar.text_input("Portal Password", type="password", key="portal_pass")
    portal_cookie = st.sidebar.text_input("Session Cookie (optional)",
                                          placeholder="name=value", key="portal_cookie")

    extra_headers = {}
    if portal_cookie.strip():
        extra_headers["Cookie"] = portal_cookie.strip()

    # ── Apply filters ─────────────────────────────────────────────────────────
    analyst_arg = None if selected_analyst == "All Analysts" else selected_analyst
    view = deals_needing_docs(deals, analyst_arg) if show_needs_action else (
        [d for d in deals if analyst_arg is None or d["analyst"] == analyst_arg]
    )

    # ── Summary KPIs ──────────────────────────────────────────────────────────
    all_docs = [v for d in deals for v in d["docs"].values()]
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Deals", len(deals))
    k2.metric("Deals Needing Action", len(deals_needing_docs(deals, analyst_arg)))
    k3.metric("Docs Pending / Failed",
              sum(1 for v in all_docs if v["status"] in ("Pending Upload", "Failed")))
    k4.metric("Docs Uploaded", sum(1 for v in all_docs if v["status"] == "Uploaded"))

    st.divider()

    # ── Deal grid ─────────────────────────────────────────────────────────────
    st.markdown(f"### Deals — {selected_analyst}  ({len(view)} shown)")

    if not view:
        st.info("No deals match the current filter.")
    else:
        for deal in view:
            docs = deal["docs"]

            # Apply status filter if set
            if status_filter:
                visible_docs = {k: v for k, v in docs.items() if v["status"] in status_filter}
            else:
                visible_docs = docs

            need_count = sum(1 for v in docs.values() if v["status"] in ("Pending Upload", "Failed"))
            header_colour = "#FFEBEE" if need_count else "#E8F5E9"
            icon = "⚠️" if need_count else "✅"

            with st.expander(
                f"{icon} **{deal['deal_id']}** — {deal['deal_name']}  |  "
                f"Analyst: {deal['analyst']}  |  {doc_summary(docs)}",
                expanded=(need_count > 0),
            ):
                info_cols = st.columns(3)
                info_cols[0].write(f"**Manager:** {deal['manager']}")
                info_cols[1].write(f"**Close Date:** {deal['close_date']}")
                info_cols[2].write(f"**Notes:** {deal.get('notes','—')}")

                st.markdown("#### Document Status & URLs")

                # ── Per-document rows ──────────────────────────────────────
                changed = False
                for doc_type, doc_info in visible_docs.items():
                    row = st.columns([2.5, 2, 4, 1.5])

                    # Status badge
                    row[0].markdown(status_badge(doc_info["status"]), unsafe_allow_html=True)
                    row[0].markdown(f"<small>{doc_type}</small>", unsafe_allow_html=True)

                    # Status selector
                    new_status = row[1].selectbox(
                        "Status", STATUS_CHOICES,
                        index=STATUS_CHOICES.index(doc_info["status"]),
                        key=f"status_{deal['deal_id']}_{doc_type}",
                        label_visibility="collapsed",
                    )
                    if new_status != doc_info["status"]:
                        st.session_state["deals"] = update_doc_status(
                            st.session_state["deals"], deal["deal_id"], doc_type, new_status)
                        changed = True

                    # URL input
                    new_url = row[2].text_input(
                        "Download URL",
                        value=doc_info.get("url", ""),
                        placeholder="https://intranet.example.com/docs/...",
                        key=f"url_{deal['deal_id']}_{doc_type}",
                        label_visibility="collapsed",
                    )
                    if new_url != doc_info.get("url", ""):
                        st.session_state["deals"] = update_doc_url(
                            st.session_state["deals"], deal["deal_id"], doc_type, new_url)
                        changed = True

                    # Local path indicator
                    lp = doc_info.get("local_path", "")
                    if lp and os.path.exists(lp):
                        fsize = round(os.path.getsize(lp) / 1024, 1)
                        row[3].markdown(f"<small>📁 {fsize} KB</small>", unsafe_allow_html=True)
                        with open(lp, "rb") as f:
                            row[3].download_button(
                                "⬇️", f.read(),
                                file_name=os.path.basename(lp),
                                key=f"dl_{deal['deal_id']}_{doc_type}",
                            )
                    else:
                        row[3].write("")

                if changed:
                    st.toast("Registry saved.", icon="💾")

                # ── Download controls ──────────────────────────────────────
                st.markdown("---")
                btn_cols = st.columns([2, 2, 3])

                # Download All (docs that have URLs)
                if btn_cols[0].button(f"⬇️ Download All Docs",
                                      key=f"dl_all_{deal['deal_id']}",
                                      use_container_width=True):
                    doc_urls = {
                        dt: di.get("url", "")
                        for dt, di in docs.items()
                        if di.get("url", "").startswith("http")
                    }
                    if not doc_urls:
                        st.warning("No download URLs configured for this deal. Enter URLs above.")
                    else:
                        progress_box = st.empty()
                        prog_log = []

                        def cb(msg):
                            prog_log.append(msg)
                            progress_box.info("\n".join(prog_log[-4:]))

                        results = download_deal_docs(
                            deal_name=deal["deal_name"],
                            doc_urls=doc_urls,
                            username=portal_user,
                            password=portal_pass,
                            extra_headers=extra_headers,
                            progress_cb=cb,
                        )

                        updated_deals = st.session_state["deals"]
                        for dt, res in results.items():
                            status = "Uploaded" if res["success"] else "Failed"
                            updated_deals = update_doc_status(
                                updated_deals, deal["deal_id"], dt,
                                status, res.get("local_path", "")
                            )
                        st.session_state["deals"] = updated_deals
                        progress_box.empty()

                        ok = sum(1 for r in results.values() if r["success"])
                        fail = len(results) - ok
                        st.success(f"Download complete — {ok} succeeded, {fail} failed.")
                        if any(not r["success"] for r in results.values()):
                            for dt, r in results.items():
                                if not r["success"]:
                                    st.error(f"{dt}: {r['error']}")
                        st.rerun()

                # Download Pending only
                if btn_cols[1].button(f"⏳ Download Pending Only",
                                      key=f"dl_pending_{deal['deal_id']}",
                                      use_container_width=True):
                    doc_urls = {
                        dt: di.get("url", "")
                        for dt, di in docs.items()
                        if di["status"] in ("Pending Upload", "Failed")
                        and di.get("url", "").startswith("http")
                    }
                    if not doc_urls:
                        st.warning("No pending docs with URLs configured.")
                    else:
                        progress_box = st.empty()
                        prog_log = []

                        def cb(msg):
                            prog_log.append(msg)
                            progress_box.info("\n".join(prog_log[-4:]))

                        results = download_deal_docs(
                            deal_name=deal["deal_name"],
                            doc_urls=doc_urls,
                            username=portal_user,
                            password=portal_pass,
                            extra_headers=extra_headers,
                            progress_cb=cb,
                        )
                        updated_deals = st.session_state["deals"]
                        for dt, res in results.items():
                            status = "Uploaded" if res["success"] else "Failed"
                            updated_deals = update_doc_status(
                                updated_deals, deal["deal_id"], dt,
                                status, res.get("local_path", "")
                            )
                        st.session_state["deals"] = updated_deals
                        progress_box.empty()
                        ok = sum(1 for r in results.values() if r["success"])
                        st.success(f"Done — {ok}/{len(results)} downloaded.")
                        st.rerun()

                # Show already-downloaded files
                downloaded = list_downloaded(deal["deal_name"])
                if downloaded:
                    with btn_cols[2].expander(f"📁 {len(downloaded)} file(s) on disk"):
                        for f in downloaded:
                            st.write(f"- `{f['filename']}` ({f['size_kb']} KB)")
                        # Offer a zip of all files
                        zip_buf = io.BytesIO()
                        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                            for f in downloaded:
                                zf.write(f["path"], f["filename"])
                        st.download_button(
                            "⬇️ Download All as ZIP",
                            data=zip_buf.getvalue(),
                            file_name=f"{deal['deal_id']}_docs.zip",
                            mime="application/zip",
                            key=f"zip_{deal['deal_id']}",
                        )

    # ── Add New Deal ──────────────────────────────────────────────────────────
    st.divider()
    with st.expander("➕ Add New Deal to Registry"):
        f = st.columns(2)
        new_id   = f[0].text_input("Deal ID",       placeholder="CLO-005")
        new_name = f[1].text_input("Deal Name",     placeholder="Summit CLO Fund V")
        g = st.columns(3)
        new_analyst = g[0].text_input("Analyst",    placeholder="Sajid")
        new_mgr     = g[1].text_input("Manager",    placeholder="KKR Credit Advisors")
        new_date    = g[2].date_input("Close Date", value=datetime.today())
        new_notes   = st.text_input("Notes",        placeholder="Initial setup — all docs pending")

        if st.button("Add Deal", type="primary"):
            if not new_id.strip() or not new_name.strip() or not new_analyst.strip():
                st.error("Deal ID, Deal Name, and Analyst are required.")
            elif any(d["deal_id"] == new_id.strip() for d in deals):
                st.error(f"Deal ID '{new_id}' already exists.")
            else:
                st.session_state["deals"] = add_deal(
                    st.session_state["deals"],
                    new_id.strip(), new_name.strip(), new_analyst.strip(),
                    new_mgr.strip(), str(new_date), new_notes.strip()
                )
                st.success(f"Deal '{new_name}' added!")
                st.rerun()

    # ── Bulk Download (across all filtered deals) ─────────────────────────────
    st.divider()
    st.markdown("### ⚡ Bulk Auto-Download — All Pending Docs")
    st.caption(
        f"Scans every deal assigned to **{selected_analyst}** and downloads all "
        "docs that have a URL configured but are still Pending or Failed."
    )
    if st.button("🚀 Run Bulk Download Now", type="primary", use_container_width=True):
        targets = deals_needing_docs(deals, analyst_arg)
        total_queued = 0
        bulk_progress = st.progress(0, text="Preparing…")
        bulk_log = st.empty()
        log_lines = []

        def log(msg):
            log_lines.append(msg)
            bulk_log.text("\n".join(log_lines[-6:]))

        updated_deals = st.session_state["deals"]
        for i, deal in enumerate(targets):
            doc_urls = {
                dt: di.get("url", "")
                for dt, di in deal["docs"].items()
                if di["status"] in ("Pending Upload", "Failed")
                and di.get("url", "").startswith("http")
            }
            if not doc_urls:
                log(f"⏭️  {deal['deal_name']} — no URLs configured, skipped.")
                bulk_progress.progress((i + 1) / max(len(targets), 1),
                                       text=f"Skipped {deal['deal_name']}")
                continue

            total_queued += len(doc_urls)
            log(f"⬇️  {deal['deal_name']} — {len(doc_urls)} doc(s)…")
            results = download_deal_docs(
                deal_name=deal["deal_name"],
                doc_urls=doc_urls,
                username=portal_user,
                password=portal_pass,
                extra_headers=extra_headers,
                progress_cb=log,
            )
            for dt, res in results.items():
                status = "Uploaded" if res["success"] else "Failed"
                updated_deals = update_doc_status(
                    updated_deals, deal["deal_id"], dt, status, res.get("local_path", "")
                )
            ok = sum(1 for r in results.values() if r["success"])
            log(f"   ✅ {ok}/{len(results)} downloaded for {deal['deal_name']}")
            bulk_progress.progress((i + 1) / max(len(targets), 1),
                                   text=f"Done: {deal['deal_name']}")

        st.session_state["deals"] = updated_deals
        bulk_progress.empty()
        bulk_log.empty()
        if total_queued == 0:
            st.info("No pending docs with URLs found. Enter download URLs in the deal rows above.")
        else:
            st.success(f"Bulk download complete. Files saved to: `{DOWNLOAD_ROOT}/`")
        st.rerun()

    # ── Export registry ───────────────────────────────────────────────────────
    st.divider()
    exp1, exp2 = st.columns(2)
    exp1.download_button(
        "⬇️ Export Registry as JSON",
        data=json.dumps(st.session_state["deals"], indent=2).encode(),
        file_name="deal_registry_export.json",
        mime="application/json",
        use_container_width=True,
    )

    # Build flat CSV
    rows = []
    for d in st.session_state["deals"]:
        for dt, di in d["docs"].items():
            rows.append({
                "Deal ID": d["deal_id"], "Deal Name": d["deal_name"],
                "Analyst": d["analyst"], "Manager": d["manager"],
                "Close Date": d["close_date"],
                "Doc Type": dt, "Status": di["status"],
                "URL": di.get("url", ""), "Local Path": di.get("local_path", ""),
                "Notes": d.get("notes", ""),
            })
    exp2.download_button(
        "⬇️ Export Registry as CSV",
        data=pd.DataFrame(rows).to_csv(index=False).encode(),
        file_name="deal_registry_export.csv",
        mime="text/csv",
        use_container_width=True,
    )
