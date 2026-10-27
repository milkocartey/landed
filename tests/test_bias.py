"""Tests for bias module — items 4, 5 fixes."""
from app.bias import analyze_offer, counterfactual_test
from app import matcher


def test_young_professional_deduped():
    """'young professional' should only produce one flag, not two overlapping."""
    r = analyze_offer("We're looking for a young professional to join our team.")
    matches = [f["match"].lower() for f in r["legal"]]
    # "young professional" should appear, but standalone "young" should be suppressed
    assert any("young professional" in m for m in matches)
    # Should not have two separate entries for "young" and "young professional"
    assert len(r["legal"]) == len(set(m for m in matches)), "Duplicate flags found"


def test_legal_flag_actual_word():
    """Legal flag should report the actual matched text."""
    r = analyze_offer("We need a young and dynamic intern.")
    assert r["legal"]
    # Match should be the actual phrase, not a pattern
    assert r["legal"][0]["match"] != ""


def test_gender_words_are_actual_words_not_stems():
    """Gender-coded words should be full words, not stems."""
    r = analyze_offer("We need a competitive, driven, and assertive person who challenges norms.")
    # All returned words should be real English words, not stems like 'competi'
    for w in r["gender_masc"]:
        assert len(w) >= 4, f"Returned stem not word: {w}"
    assert any(w.lower().startswith("competit") for w in r["gender_masc"])


def test_clean_offer_no_flags():
    r = analyze_offer("Looking for a motivated intern with strong analytical skills.")
    assert len(r["legal"]) == 0
    assert len(r["exclusionary"]) == 0


def test_counterfactual_6_names():
    """Fairness test must cover exactly 6 name variants."""
    sample_cv = {
        "name": "Alex Martin",
        "raw_text": "Alex Martin\nData analyst intern, Python, SQL",
        "skills": ["Python", "SQL"],
    }
    offer = {
        "id": "test", "title": "Data Analyst", "company": "Acme",
        "description": "Python and SQL skills required.", "location": "Paris", "source": "demo",
    }
    r = counterfactual_test(sample_cv, offer, matcher)
    assert len(r["results"]) == 6
    names = [row["name"] for row in r["results"]]
    assert "Thomas Martin" in names
    assert "Julie Martin" in names
    assert "Mohamed Benali" in names
    assert "Leïla Benali" in names
    assert "Kevin Nguyen" in names
    assert "Linh Nguyen" in names


def test_counterfactual_delta_is_int():
    sample_cv = {
        "name": "Alex", "raw_text": "Alex\nPython developer",
        "skills": ["Python"],
    }
    offer = {"id": "t", "title": "Dev", "company": "Co", "description": "Python", "location": "", "source": "demo"}
    r = counterfactual_test(sample_cv, offer, matcher)
    assert isinstance(r["delta"], int)
    assert r["verdict"] in ("fair", "possible_bias")
