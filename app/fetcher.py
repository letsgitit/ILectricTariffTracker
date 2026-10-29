"""Fetches a tracked document and returns its plain-text content.

Two doc_types are supported:
  - "pdf": download the PDF, extract text with pdfplumber
  - "html_index": fetch the HTML page as text (used for index/landing pages
    where we just want to notice the page changed, e.g. a new PDF got linked)

Network errors, non-200 responses, and PDF-parse failures are caught and
returned as a FetchResult with `.error` set rather than raised, so one bad
document never takes down a scheduled run of the other documents.
"""
from __future__ import annotations

import hashlib
import io
import re
import unicodedata
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Optional

import requests

USER_AGENT = (
    "TariffTrackerBot/1.0 (+contact: set TARIFF_TRACKER_CONTACT env var; "
    "fetches publicly posted utility tariff PDFs on a weekly schedule)"
)
TIMEOUT_SECONDS = 30


@dataclass
class FetchResult:
    text: str
    content_hash: str
    http_status: Optional[int]
    error: Optional[str] = None


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


_WS_RE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Canonical form used for hashing, so cosmetic differences between fetches
    (whitespace/line-wrap changes, unicode variants) don't register as changes."""
    return _WS_RE.sub(" ", unicodedata.normalize("NFKC", text)).strip()


class _VisibleHTML(HTMLParser):
    """Keeps visible text and link targets; drops scripts, styles and comments,
    whose content (nonces, cache-busters, timestamps) changes on every load."""

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self.links: set[str] = set()
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1
        elif tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.add(href)

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    parser = _VisibleHTML()
    parser.feed(html)
    # Links are sorted so reordering alone isn't a change; a new/removed link is.
    return "\n".join(parser.parts + sorted(parser.links))


def fetch_document(url: str, doc_type: str = "pdf") -> FetchResult:
    headers = {"User-Agent": USER_AGENT}
    try:
        resp = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS)
    except requests.RequestException as e:
        return FetchResult(text="", content_hash="", http_status=None, error=str(e))

    if resp.status_code != 200:
        return FetchResult(
            text="", content_hash="", http_status=resp.status_code,
            error=f"HTTP {resp.status_code}",
        )

    if doc_type == "pdf":
        try:
            text = _extract_pdf_text(resp.content)
        except Exception as e:  # pdfplumber can raise various parse errors
            return FetchResult(
                text="", content_hash="", http_status=resp.status_code,
                error=f"PDF parse error: {e}",
            )
    else:
        text = html_to_text(resp.text)

    return FetchResult(
        text=text, content_hash=_hash(normalize_text(text)), http_status=resp.status_code, error=None
    )


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    import pdfplumber

    chunks = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            chunks.append(page.extract_text() or "")
    return "\n".join(chunks)
