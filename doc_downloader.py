#!/usr/bin/env python3
"""
Document Downloader — downloads indenture/memo docs from an internal
web portal into  downloads/{deal_name}/{doc_type}.{ext}
Supports: basic auth, session cookies, custom headers, retry logic.
"""

import os, re, time, mimetypes
from urllib.parse import urlparse
from typing import Optional, Callable
import urllib.request
import urllib.error

DOWNLOAD_ROOT = os.path.join(os.path.dirname(__file__), "downloads")


def _safe_name(name: str) -> str:
    """Sanitise a string for use as a file/folder name."""
    return re.sub(r"[^\w\-.]", "_", name).strip("_")


def _resolve_ext(url: str, content_type: str = "") -> str:
    """Guess file extension from URL path or Content-Type header."""
    path = urlparse(url).path
    _, ext = os.path.splitext(path)
    if ext and len(ext) <= 5:
        return ext.lower()
    # Fallback via content-type
    if "pdf" in content_type:
        return ".pdf"
    if "word" in content_type or "docx" in content_type:
        return ".docx"
    if "excel" in content_type or "xlsx" in content_type:
        return ".xlsx"
    return ".pdf"  # safe default for financial docs


def _build_request(url: str, username: str = "", password: str = "",
                   extra_headers: dict = None) -> urllib.request.Request:
    headers = {"User-Agent": "CLO-Studio-DocFetcher/1.0"}
    if extra_headers:
        headers.update(extra_headers)

    req = urllib.request.Request(url, headers=headers)

    if username and password:
        import base64
        token = base64.b64encode(f"{username}:{password}".encode()).decode()
        req.add_header("Authorization", f"Basic {token}")

    return req


def download_document(
    url: str,
    deal_name: str,
    doc_type: str,
    username: str = "",
    password: str = "",
    extra_headers: dict = None,
    max_retries: int = 3,
    timeout: int = 60,
    progress_cb: Optional[Callable[[str], None]] = None,
) -> dict:
    """
    Download a single document.

    Returns:
        {
          "success": bool,
          "local_path": str,   # absolute path to saved file (or "")
          "error": str,        # error message (or "")
          "size_bytes": int,
        }
    """
    deal_folder = os.path.join(DOWNLOAD_ROOT, _safe_name(deal_name))
    os.makedirs(deal_folder, exist_ok=True)

    last_error = ""
    for attempt in range(1, max_retries + 1):
        if progress_cb:
            progress_cb(f"Attempt {attempt}/{max_retries} — {doc_type}…")
        try:
            req = _build_request(url, username, password, extra_headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                content_type = resp.headers.get("Content-Type", "")
                ext = _resolve_ext(url, content_type)
                filename = f"{_safe_name(doc_type)}{ext}"
                local_path = os.path.join(deal_folder, filename)

                data = resp.read()
                with open(local_path, "wb") as f:
                    f.write(data)

                return {
                    "success": True,
                    "local_path": local_path,
                    "error": "",
                    "size_bytes": len(data),
                }

        except urllib.error.HTTPError as e:
            last_error = f"HTTP {e.code}: {e.reason}"
            if e.code in (401, 403, 404):
                break  # don't retry auth/not-found errors
        except urllib.error.URLError as e:
            last_error = f"Network error: {e.reason}"
        except Exception as e:
            last_error = str(e)

        if attempt < max_retries:
            time.sleep(2 ** attempt)  # exponential back-off

    return {"success": False, "local_path": "", "error": last_error, "size_bytes": 0}


def download_deal_docs(
    deal_name: str,
    doc_urls: dict,          # {doc_type: url}
    username: str = "",
    password: str = "",
    extra_headers: dict = None,
    progress_cb: Optional[Callable[[str], None]] = None,
) -> dict:
    """
    Download all docs for one deal.

    Returns:
        { doc_type: download_result_dict, … }
    """
    results = {}
    for doc_type, url in doc_urls.items():
        if not url or not url.strip().startswith("http"):
            results[doc_type] = {
                "success": False,
                "local_path": "",
                "error": "No URL configured",
                "size_bytes": 0,
            }
            continue
        if progress_cb:
            progress_cb(f"⬇️  Downloading {doc_type} for {deal_name}…")
        results[doc_type] = download_document(
            url=url,
            deal_name=deal_name,
            doc_type=doc_type,
            username=username,
            password=password,
            extra_headers=extra_headers,
            progress_cb=progress_cb,
        )
    return results


def list_downloaded(deal_name: str) -> list:
    """List files already downloaded for a deal."""
    folder = os.path.join(DOWNLOAD_ROOT, _safe_name(deal_name))
    if not os.path.isdir(folder):
        return []
    return [
        {"filename": f, "path": os.path.join(folder, f),
         "size_kb": round(os.path.getsize(os.path.join(folder, f)) / 1024, 1)}
        for f in sorted(os.listdir(folder))
    ]
