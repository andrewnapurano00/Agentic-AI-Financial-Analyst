from __future__ import annotations

import sys
from types import SimpleNamespace

import pandas as pd
import pytest
from pydantic import ValidationError

from langgraphagenticai.equity_committee import (
    EquityCommitteeDecision,
    build_equity_committee_packet,
    run_equity_committee,
)


def test_committee_packet_is_bounded_stable_and_preserves_zero():
    frame = pd.DataFrame([
        {"Ticker": "AAA", "Final Rank": 1, "Revenue Growth": 0.0, "P/E": float("nan")},
        {"Ticker": "BBB", "Final Rank": 2, "Revenue Growth": 12.5, "P/E": 18.0},
    ])
    first = build_equity_committee_packet(frame, peer_group="Technology", generated_at="2026-09-27T12:00:00Z")
    second = build_equity_committee_packet(frame.copy(), peer_group="Technology", generated_at="2026-09-27T12:00:00Z")
    assert first["fingerprint"] == second["fingerprint"]
    assert first["scorecard"][0]["Revenue Growth"] == 0.0
    assert first["scorecard"][0]["P/E"] is None
    assert "api_key" not in str(first).lower()


def test_committee_schema_requires_consistent_verdict():
    with pytest.raises(ValidationError):
        EquityCommitteeDecision(
            best_buy="AAA", confidence=50, verdict="NO_BUY", summary="No.", debate_summary="Split.",
            specialist_views=[],
        )


def test_committee_rejects_out_of_universe_ticker(monkeypatch):
    class FakeComponent:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class FakeCrew(FakeComponent):
        def kickoff(self):
            decision = EquityCommitteeDecision(
                best_buy="ZZZ", confidence=70, verdict="BUY", summary="Winner.",
                debate_summary="The agents disagreed.", specialist_views=[],
            )
            return SimpleNamespace(pydantic=decision)

    fake = SimpleNamespace(
        Agent=FakeComponent, Task=FakeComponent, Crew=FakeCrew, LLM=FakeComponent,
        Process=SimpleNamespace(sequential="sequential"),
    )
    monkeypatch.setitem(sys.modules, "crewai", fake)
    packet = build_equity_committee_packet(
        pd.DataFrame([{"Ticker": "AAA", "Final Rank": 1}]),
        peer_group="General", generated_at="2026-09-27T12:00:00Z",
    )
    with pytest.raises(ValueError, match="out-of-universe"):
        run_equity_committee(packet, openai_api_key="test-only", model_name="gpt-test")
