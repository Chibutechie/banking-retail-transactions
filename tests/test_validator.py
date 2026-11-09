from pipeline import validator


def test_normalize_location_state_accepts_abuja_fct_variants() -> None:
    assert validator._normalize_location_state("Abuja (FCT)") == "fct"
    assert validator._normalize_location_state("abuja(fct)") == "fct"
    assert validator._normalize_location_state("FCT") == "fct"
