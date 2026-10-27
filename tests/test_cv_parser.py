"""Tests for CV section-heading detection — item 6 fixes."""
from app.cv_parser import _heading_key, SECTION_HEADINGS


def test_skills_and_tools_heading():
    assert _heading_key("SKILLS & TOOLS") == "skills"
    assert _heading_key("Skills & Tools") == "skills"


def test_certifications_heading():
    assert _heading_key("CERTIFICATIONS") == "skills"


def test_competences_heading():
    assert _heading_key("COMPÉTENCES & OUTILS") == "skills"


def test_experience_heading():
    assert _heading_key("EXPÉRIENCE PROFESSIONNELLE") == "experience"


def test_regular_skills_heading():
    assert _heading_key("SKILLS") == "skills"
    assert _heading_key("Technical Skills") == "skills"


def test_non_heading_long_line():
    assert _heading_key("Developed a Python backend using FastAPI and SQLite for a web app") is None
