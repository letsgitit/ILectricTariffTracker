"""Extracts specific dollar-figure line items from a document's text using
the regex patterns configured per document in tracked_documents.yaml.

This is intentionally simple (regex, not a layout-aware PDF table parser)
because tariff sheets vary enough in formatting that a generic table parser
would be less reliable than a hand-tuned pattern per line item you actually
care about. Add patterns as you find the ones you want to track closely;
everything else is still covered by whole-document hash diffing.
"""
from __future__ import annotations

import re
from typing import Dict, List


def extract_line_items(text: str, patterns: List[dict]) -> Dict[str, str]:
    results: Dict[str, str] = {}
    for p in patterns or []:
        label = p["label"]
        pattern = p["pattern"]
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            results[label] = match.group(1).replace(",", "")
        else:
            results[label] = None  # explicit: pattern didn't match this fetch
    return results
