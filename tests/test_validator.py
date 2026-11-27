from pipeline import validator


def test_normalize_location_state_accepts_abuja_fct_variants() -> None:
    assert validator._normalize_location_state("Abuja (FCT)") == "fct"
    assert validator._normalize_location_state("abuja(fct)") == "fct"
    assert validator._normalize_location_state("FCT") == "fct"


def test_normalize_location_state_handles_empty_and_unknown_values() -> None:
    assert validator._normalize_location_state(None) == ""
    assert validator._normalize_location_state("  Lagos  ") == "lagos"
    assert validator._normalize_location_state("Unknown State") == "unknown state"
