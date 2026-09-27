from __future__ import annotations

import json
from pathlib import Path

from langgraphagenticai.deep_research.models import Evidence, ResearchRequest
from langgraphagenticai.deep_research.v2 import (
    MODES, compact_decision_brief, committee_diagnostics, prompt_diagnostics,
    research_cache_key, stage_configuration, validate_report,
)


def _evidence():
    return [Evidence("E001", "AAA", "financial_trends", "Trends", "Synthetic", {
        "currency": "USD", "date": "2026-06-30", "revenue_growth": 0.1,
    })]


def test_v2_modes_route_and_bound_every_stage():
    economy = stage_configuration("Economy", light_provider="Groq", light_model="small-model")
    maximum = stage_configuration("Maximum quality", light_provider="Groq", light_model="small-model")
    assert economy["routes"]["plan"] == {"provider": "Groq", "model": "small-model"}
    assert economy["routes"]["draft"]["model"] == "gpt-5-mini"
    assert economy["limits"]["plan"][1] <= 700
    assert economy["depth_draft_tokens"]["Standard"] <= 2200
    assert economy["contexts"]["draft_standard"] <= 24000
    assert maximum["routes"]["plan"]["provider"] == "OpenAI"
    assert maximum["routes"]["draft"]["model"] == "gpt-5"
    assert set(MODES) == {"Economy", "Balanced", "Maximum quality"}


def test_v2_validation_and_prompt_diagnostics_are_deterministic():
    request = ResearchRequest(["AAA"])
    valid = "## Executive Investment Thesis\nAAA is assessed in USD as of 2026-06-30 [E001].\n## Risks\nRisk.\n## Thesis invalidation\nInvalidation."
    assert validate_report(request, _evidence(), valid) == []
    invalid = validate_report(request, _evidence(), "AAA BUY [E999]")
    assert any("Unknown evidence" in issue for issue in invalid)
    assert any("currency" in issue.lower() for issue in invalid)
    rows = prompt_diagnostics(_evidence(), {"draft_standard": 22000}, focus="risk")
    assert rows[0]["actual_characters"] <= 22000


def test_v2_cache_key_changes_with_configuration_and_provider_dates():
    request = ResearchRequest(["AAA"])
    config = stage_configuration("Economy", light_provider="OpenAI")
    first = research_cache_key(request, config, [item.to_dict() for item in _evidence()])
    changed = [item.to_dict() for item in _evidence()]
    changed[0]["retrieved_at"] = "2027-01-01T00:00:00+00:00"
    assert first != research_cache_key(request, config, changed)
    assert first == research_cache_key(request, config, [item.to_dict() for item in _evidence()])


def test_compact_committee_packet_and_usage_attribution():
    evidence = [item.to_dict() for item in _evidence()]
    result = {"request": {"symbols": ["AAA"]}, "evidence": evidence, "comparison": [], "warnings": [], "gaps": []}
    brief = compact_decision_brief(result, 10000)
    assert len(json.dumps(brief)) <= 11000
    rows = committee_diagnostics({
        "usage_metrics": {"prompt_tokens": 3000, "completion_tokens": 900},
        "specialist_model": "gpt-5-nano", "model": "gpt-5-mini",
    })
    assert sum(row["input_tokens"] for row in rows) == 3000
    assert {row["stage"] for row in rows} == {"crew_specialists", "crew_lead"}


def test_v2_fixed_evaluation_set_covers_required_scenarios():
    path = Path(__file__).parent / "fixtures" / "deep_research_v2_eval_cases.json"
    cases = json.loads(path.read_text(encoding="utf-8"))
    assert {case["id"] for case in cases} == {
        "large_cap", "sparse_coverage", "same_sector", "cross_sector", "missing_data",
    }
