"""Wrap-up code taxonomy for classifying customer interactions.

Wrap-up codes let agents (or this module, automatically) tag each interaction
with a standardized reason code so that trending topics can be counted and
turned into actionable recommendations. When an interaction's topic doesn't
match any known code, a new wrap-up code is learned and persisted so the same
topic is recognized consistently going forward.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DYNAMIC_CODES_FILE = DATA_DIR / "dynamic_wrapup_codes.json"

# code -> (display label, keywords used to auto-classify free-text reasons/notes)
WRAPUP_CODE_DEFINITIONS: Dict[str, Dict[str, object]] = {
    "CLAIM_STATUS": {
        "label": "Claim Status Inquiry",
        "keywords": ["claim status", "claim update", "pending claim", "claim review"],
    },
    "SUBMISSION_ISSUE": {
        "label": "Submission / Documentation Issue",
        "keywords": ["submission", "rejected", "document", "missing form", "error code"],
    },
    "PPW_GAP": {
        "label": "Medical PPW / Documentation Gap",
        "keywords": ["ppw", "medical record", "provider record", "medical documentation"],
    },
    "POLICY_GUIDANCE": {
        "label": "Vendor Policy / Procedure Guidance",
        "keywords": ["policy", "procedure", "vendor", "eligibility", "guidance"],
    },
    "ESCALATION": {
        "label": "Escalation Required",
        "keywords": ["escalate", "escalation", "urgent", "complaint", "supervisor"],
    },
    "BILLING_ISSUE": {
        "label": "Billing / Payment Issue",
        "keywords": ["billing", "payment", "invoice", "refund", "charge"],
    },
    "TECHNICAL_ISSUE": {
        "label": "Technical / Portal Issue",
        "keywords": ["portal", "login", "website", "technical", "system error"],
    },
    "GENERAL_INQUIRY": {
        "label": "General Service Inquiry",
        "keywords": [],
    },
}

DEFAULT_WRAPUP_CODE = "GENERAL_INQUIRY"

_STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "for", "to", "on", "in", "is",
    "was", "with", "about", "customer", "asked", "issue", "request",
}


def _load_dynamic_definitions() -> Dict[str, Dict[str, object]]:
    if not DYNAMIC_CODES_FILE.exists():
        return {}
    try:
        with open(DYNAMIC_CODES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_dynamic_definitions(definitions: Dict[str, Dict[str, object]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DYNAMIC_CODES_FILE, "w", encoding="utf-8") as f:
        json.dump(definitions, f, indent=2, sort_keys=True)


def _all_definitions() -> Dict[str, Dict[str, object]]:
    combined = dict(WRAPUP_CODE_DEFINITIONS)
    combined.update(_load_dynamic_definitions())
    return combined


def _slugify_to_code(text: str, existing_codes: List[str]) -> str:
    words = [w for w in re.findall(r"[a-zA-Z0-9]+", text.lower()) if w not in _STOPWORDS]
    words = words[:3] or ["topic"]
    base_code = "_".join(words).upper()

    code = base_code
    suffix = 2
    while code in existing_codes:
        code = f"{base_code}_{suffix}"
        suffix += 1

    return code


def _learn_new_wrapup_code(topic_text: str) -> str:
    """Create and persist a new wrap-up code for a previously unseen topic."""
    dynamic_definitions = _load_dynamic_definitions()
    normalized_topic = topic_text.strip().lower()

    existing_codes = list(WRAPUP_CODE_DEFINITIONS.keys()) + list(dynamic_definitions.keys())
    new_code = _slugify_to_code(normalized_topic, existing_codes)

    dynamic_definitions[new_code] = {
        "label": topic_text.strip().title(),
        "keywords": [normalized_topic],
    }
    _save_dynamic_definitions(dynamic_definitions)

    return new_code


def classify_wrapup_code(call_reason: str = "", notes: str = "", learn_new: bool = True) -> str:
    """Return the wrap-up code that best matches the given reason/notes text.

    If no known code (static or previously learned) matches, a new wrap-up
    code is created and saved from the topic so it is reused for future
    interactions with the same or similar reason.
    """
    call_reason = call_reason or ""
    notes = notes or ""
    text = f"{call_reason} {notes}".lower().strip()

    if not text:
        return DEFAULT_WRAPUP_CODE

    for code, definition in _all_definitions().items():
        keywords: List[str] = definition["keywords"]  # type: ignore[assignment]
        if any(keyword in text for keyword in keywords):
            return code

    if learn_new and call_reason.strip():
        return _learn_new_wrapup_code(call_reason)

    return DEFAULT_WRAPUP_CODE


def get_wrapup_code_label(code: str) -> str:
    return _all_definitions().get(code, {}).get("label", code)  # type: ignore[return-value]


def apply_wrapup_codes(df: pd.DataFrame) -> pd.DataFrame:
    """Fill in a `wrapup_code` column for any rows where it is missing or blank."""
    df = df.copy()
    if "wrapup_code" not in df.columns:
        df["wrapup_code"] = ""

    missing_mask = df["wrapup_code"].astype(str).str.strip() == ""
    if missing_mask.any():
        df.loc[missing_mask, "wrapup_code"] = df.loc[missing_mask].apply(
            lambda row: classify_wrapup_code(row.get("call_reason", ""), row.get("notes", "")),
            axis=1,
        )

    return df
