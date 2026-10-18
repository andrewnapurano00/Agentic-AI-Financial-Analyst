"""Local charts from approved scenario inputs; no provider/model access."""
import altair as alt
import pandas as pd

from langgraphagenticai.valuation.model import calculate

COLORS = ["#F87171", "#60A5FA", "#34D399"]


def scenario_chart(facts, result, years):
    rows = []
    for name, scenario in result.items():
        rows.append(dict(Scenario=name, Years=years, Target=scenario["target"], Reference=facts["price"], Basis="Hypothetical exit price", Price_return=scenario["price_return"] * 100))
    frame = pd.DataFrame(rows)
    color = alt.Color("Scenario:N", scale=alt.Scale(domain=["Bear", "Base", "Bull"], range=COLORS))
    chart = alt.Chart(frame).encode(y=alt.Y("Scenario:N", sort=["Bull", "Base", "Bear"], title=None), color=color)
    lines = chart.mark_rule(strokeWidth=5, opacity=.65).encode(x=alt.X("Reference:Q", title=f"Price / share ({facts['currency']})", scale=alt.Scale(zero=False)), x2="Target:Q")
    dots = chart.mark_point(filled=True, size=180).encode(x="Target:Q", tooltip=["Scenario", "Basis", "Years", alt.Tooltip("Target:Q", format=",.2f"), alt.Tooltip("Price_return:Q", title="Price return %", format="+.1f")])
    reference = alt.Chart(pd.DataFrame([{"Reference": facts["price"]}])).mark_rule(strokeDash=[5, 5], color="#CBD5E1").encode(x="Reference:Q")
    return (lines + dots + reference).properties(height=310).configure_view(strokeOpacity=0)


def sensitivity_chart(facts, years, growth, multiple):
    rows = []
    for offset in (-.04, -.02, 0, .02, .04):
        g = max(-.45, min(.60, growth + offset))
        for factor in (.8, .9, 1, 1.1, 1.2):
            m = max(.1, min(300, multiple * factor))
            base = calculate(facts, years, g, m)["Base"]
            rows.append({"Growth %": round(g * 100, 2), "Exit multiple": round(m, 2), "Target": base["target"], "Price return %": base["price_return"] * 100})
    frame = pd.DataFrame(rows).drop_duplicates(["Growth %", "Exit multiple"])
    chart = alt.Chart(frame).encode(
        x=alt.X("Growth %:O", title="Annual EPS / BVPS growth (%)"),
        y=alt.Y("Exit multiple:O", title=f"Exit {facts['method']} (x)", sort="descending"),
    )
    span = max(1., float(frame["Price return %"].abs().max()))
    tiles = chart.mark_rect(cornerRadius=3).encode(color=alt.Color("Price return %:Q", scale=alt.Scale(domain=[-span, 0, span], range=["#9F3348", "#142334", "#087A60"]), legend=alt.Legend(title="Price return %")), tooltip=["Growth %", "Exit multiple", alt.Tooltip("Target:Q", format=",.2f"), alt.Tooltip("Price return %:Q", format="+.1f")])
    labels = chart.mark_text(fontSize=12, color="#FFFFFF").encode(text=alt.Text("Target:Q", format=",.0f"))
    return (tiles + labels).properties(height=310).configure_view(strokeOpacity=0)
