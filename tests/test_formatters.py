from langgraphagenticai.utils.formatters import compact_numeric, compact_percent, rectangular_rows


def test_compact_numeric():
    assert compact_numeric(1_500_000_000) == "$1.5B"
    assert compact_numeric(2_500_000) == "$2.5M"


def test_compact_percent():
    assert compact_percent(0.25) == "25.0%"
    assert compact_percent(25) == "25.0%"


def test_rectangular_rows():
    rows = [["A", 1], ["B"]]
    out = rectangular_rows(rows)
    assert out == [["A", 1], ["B", "N/A"]]