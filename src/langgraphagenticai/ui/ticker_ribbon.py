"""Client animated ribbon; animation never requests data or models."""
from html import escape
import streamlit as st


def ribbon_html(rows):
    items = []
    for row in rows:
        change = row["change"]
        color = "#37b68c" if change is not None and change > 0 else "#e2747e" if change is not None and change < 0 else "#bac7d5"
        value = f"{change:+.2f}%" if change is not None else "Unavailable"
        title = escape("Quote as of: " + str(row.get("as_of") or "Unavailable") + "; currency unavailable", quote=True)
        items.append(f'<span class="quote" title="{title}"><b>{escape(row["symbol"])}</b> {row["price"]:,.2f} <strong style="color:{color}">{value}</strong></span>')
    group = '<div class="group">' + ''.join(items) + '</div>'
    return f'''<style>
body{{margin:0;background:#0e1724;color:#e4edf6;font:14px system-ui}}
.viewport{{overflow:auto;border-block:1px solid #27364a;padding:14px 0}}
.track{{display:flex;width:max-content;animation:roll {max(30, len(rows)*4)}s linear infinite}}
.group{{display:flex;flex-shrink:0}}.quote{{padding:0 24px;border-right:1px solid #27364a;white-space:nowrap}}
.quote b{{margin-right:10px}}.viewport:hover .track,.viewport:focus .track{{animation-play-state:paused}}
@keyframes roll{{to{{transform:translateX(-50%)}}}}
@media(prefers-reduced-motion:reduce){{.track{{animation:none}}}}
</style><div class="viewport" tabindex="0" aria-label="S&P 500 quotes; focus or hover to pause"><div class="track">{group}{group}</div></div>'''


def render_ticker_ribbon(packet):
    st.caption("S&P 500 · constituent prices and 1-day change · FMP · cached up to 5 minutes · hover or focus to pause")
    if packet["rows"]:
        import streamlit.components.v1 as components
        components.html(ribbon_html(packet["rows"]), height=68, scrolling=False)
        st.caption(f'{len(packet["rows"])} / {packet["requested"]} constituents · retrieved {packet["retrieved_at"]} · quote times in tooltips; currency and session completeness unverified. Saved quotes may be stale outside trading hours.')
    else:
        st.info("S&P 500 ribbon unavailable. Configure FMP or refresh market evidence to retry.")
    for warning in dict.fromkeys(packet["warnings"]):
        st.caption(warning)
