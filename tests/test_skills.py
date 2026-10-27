"""Tests for skill extraction — item 6 fixes."""
import pytest
from app.skills import extract_skills


def test_accounting_no_false_positive_from_audit():
    """'audit' in cybersecurity context must NOT extract Accounting."""
    result = extract_skills("Conducted a security audit and penetration test")
    assert "Accounting" not in result


def test_accounting_still_matches_real_accounting():
    result = extract_skills("Strong background in accounting and IFRS reporting")
    assert "Accounting" in result


def test_kpi_extracted():
    result = extract_skills("Tracked KPIs and reported on key performance indicators")
    assert "KPI" in result


def test_negotiation_extracted():
    result = extract_skills("Strong negotiation skills in client-facing roles")
    assert "Negotiation" in result


def test_b2b_extracted():
    result = extract_skills("3 years of B2B sales experience in SaaS")
    assert "Business Development" in result or "Sales" in result


def test_crm_extracted():
    result = extract_skills("Managed CRM development and account management")
    assert "Sales" in result


def test_linkedin_extracted():
    result = extract_skills("Grew company presence on LinkedIn and Instagram")
    assert "Social Media" in result


def test_go_to_market_extracted():
    result = extract_skills("Built the go-to-market strategy for product launch")
    assert "Strategy" in result
