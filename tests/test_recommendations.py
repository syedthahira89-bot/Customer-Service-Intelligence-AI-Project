from etl.recommendations import (
    WRAPUP_CODE_RECOMMENDATIONS,
    get_wrapup_code_recommendations,
)


def test_known_codes_return_specific_recommendations():
    for code in WRAPUP_CODE_RECOMMENDATIONS:
        recs = get_wrapup_code_recommendations(code)
        assert recs == WRAPUP_CODE_RECOMMENDATIONS[code]
        assert len(recs) > 0


def test_unknown_code_returns_generic_but_labeled_recommendations():
    recs = get_wrapup_code_recommendations("SOME_NEW_TOPIC")

    assert len(recs) == 3
    assert all("SOME_NEW_TOPIC" in rec for rec in recs)


def test_all_recommendation_lists_are_non_empty():
    for code, recs in WRAPUP_CODE_RECOMMENDATIONS.items():
        assert isinstance(recs, list)
        assert all(isinstance(item, str) and item.strip() for item in recs)
