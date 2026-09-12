import json

import pandas as pd
import pytest

from etl import wrapup_codes


@pytest.fixture(autouse=True)
def isolate_dynamic_codes_file(tmp_path, monkeypatch):
    """Point the dynamic codes file at a temp path so tests never touch real data."""
    temp_file = tmp_path / "dynamic_wrapup_codes.json"
    monkeypatch.setattr(wrapup_codes, "DATA_DIR", tmp_path)
    monkeypatch.setattr(wrapup_codes, "DYNAMIC_CODES_FILE", temp_file)
    yield temp_file


def test_classify_known_static_codes():
    assert wrapup_codes.classify_wrapup_code("Claim status update") == "CLAIM_STATUS"
    assert wrapup_codes.classify_wrapup_code("Submission rejected missing docs") == "SUBMISSION_ISSUE"
    assert wrapup_codes.classify_wrapup_code("PPW medical record missing") == "PPW_GAP"
    assert wrapup_codes.classify_wrapup_code("Policy clarification") == "POLICY_GUIDANCE"
    assert wrapup_codes.classify_wrapup_code("Urgent escalation complaint") == "ESCALATION"
    assert wrapup_codes.classify_wrapup_code("Billing refund issue") == "BILLING_ISSUE"
    assert wrapup_codes.classify_wrapup_code("Portal login error") == "TECHNICAL_ISSUE"


def test_classify_blank_text_returns_default():
    assert wrapup_codes.classify_wrapup_code("", "") == wrapup_codes.DEFAULT_WRAPUP_CODE


def test_unknown_topic_learns_new_code(isolate_dynamic_codes_file):
    code = wrapup_codes.classify_wrapup_code("Shipment tracking delay for courier")

    assert code not in wrapup_codes.WRAPUP_CODE_DEFINITIONS
    assert isolate_dynamic_codes_file.exists()

    saved = json.loads(isolate_dynamic_codes_file.read_text())
    assert code in saved
    assert saved[code]["label"]
    assert saved[code]["keywords"]


def test_unknown_topic_reuses_learned_code_on_repeat():
    first_code = wrapup_codes.classify_wrapup_code("Shipment tracking delay for courier")
    second_code = wrapup_codes.classify_wrapup_code("Shipment tracking delay for courier")

    assert first_code == second_code


def test_similar_phrasing_matches_learned_code():
    first_code = wrapup_codes.classify_wrapup_code("Shipment tracking delay for courier")
    second_code = wrapup_codes.classify_wrapup_code("Shipment tracking delay again")

    assert first_code == second_code


def test_learn_new_false_falls_back_to_default():
    code = wrapup_codes.classify_wrapup_code("Completely novel unmatched topic", learn_new=False)
    assert code == wrapup_codes.DEFAULT_WRAPUP_CODE


def test_dissimilar_new_topic_reuses_wording_but_no_shared_words_creates_new_code(isolate_dynamic_codes_file):
    first_code = wrapup_codes.classify_wrapup_code("Shipment tracking delay for courier")
    second_code = wrapup_codes.classify_wrapup_code("Warehouse inventory mismatch report")

    assert first_code != second_code
    saved = json.loads(isolate_dynamic_codes_file.read_text())
    assert first_code in saved
    assert second_code in saved


def test_overlapping_new_topic_consolidates_into_existing_dynamic_code(isolate_dynamic_codes_file):
    first_code = wrapup_codes.classify_wrapup_code("Shipment tracking delay for courier")
    # Shares 2 of 3 core words ("shipment", "tracking") with the first topic.
    second_code = wrapup_codes.classify_wrapup_code("Shipment tracking confirmation request")

    assert first_code == second_code

    saved = json.loads(isolate_dynamic_codes_file.read_text())
    assert len(saved) == 1
    assert len(saved[first_code]["keywords"]) == 2


def test_get_wrapup_code_label_known_and_unknown():
    assert wrapup_codes.get_wrapup_code_label("CLAIM_STATUS") == "Claim Status Inquiry"
    assert wrapup_codes.get_wrapup_code_label("NOT_A_REAL_CODE") == "NOT_A_REAL_CODE"


def test_apply_wrapup_codes_fills_blank_rows_only():
    df = pd.DataFrame(
        [
            {"call_reason": "Claim status update", "notes": "", "wrapup_code": ""},
            {"call_reason": "Policy clarification", "notes": "", "wrapup_code": "CUSTOM_PRESET"},
        ]
    )

    result = wrapup_codes.apply_wrapup_codes(df)

    assert result.loc[0, "wrapup_code"] == "CLAIM_STATUS"
    assert result.loc[1, "wrapup_code"] == "CUSTOM_PRESET"


def test_apply_wrapup_codes_adds_missing_column():
    df = pd.DataFrame([{"call_reason": "Claim status update", "notes": ""}])
    result = wrapup_codes.apply_wrapup_codes(df)
    assert result.loc[0, "wrapup_code"] == "CLAIM_STATUS"
