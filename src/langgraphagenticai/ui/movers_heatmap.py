"""Sector concentration of the exact filtered ranking, without new retrieval."""
import altair as alt
import pandas as pd
from langgraphagenticai.analysis.discovery import sector_summary
from langgraphagenticai.ui.opening_presentation import terminal_chart


def concentration_rows(frame, period):
    if frame.empty:
        return []
    summary = sector_summary(frame, period)
    total = int(summary.stocks.sum())
    rows = []
    for index, row in enumerate(summary.itertuples()):
        share = row.stocks / total
        intensity = min(abs(row.mean_return) / 5, 1)
        low, high = (38, 50, 65), (120, 47, 59) if row.mean_return < 0 else (18, 107, 81)
        fill = '#' + ''.join(f'{round(a+(b-a)*intensity):02x}' for a, b in zip(low, high))
        rows.append(dict(sector=str(row.sector), stocks=int(row.stocks), share=share,
                         mean=row.mean_return, label=f'{row.mean_return:+.2f}%',
                         count=f'{row.stocks} stocks · {share:.0%} of ranking',
                         x=index % 3, x2=index % 3 + .98, cx=index % 3 + .49,
                         y=index // 3, y2=index // 3 + .97, cy=index // 3 + .485, fill=fill))
    return rows


def concentration_chart(rows):
    base = alt.Chart(pd.DataFrame(rows))
    columns = min(3, len(rows))
    tiles = base.mark_rect(cornerRadius=3, stroke='#172334', strokeWidth=3).encode(
        x=alt.X('x:Q', axis=None, scale=alt.Scale(domain=[0, columns])), x2='x2:Q',
        y=alt.Y('y:Q', axis=None, scale=alt.Scale(domain=[(len(rows)+2)//3, 0])), y2='y2:Q',
        color=alt.Color('fill:N', scale=None, legend=None),
        tooltip=['sector:N', 'stocks:Q', alt.Tooltip('share:Q', format='.1%'), alt.Tooltip('mean:Q', title='Mean price change (%)', format='+.2f')])
    text = base.encode(x=alt.X('cx:Q', axis=None), y=alt.Y('cy:Q', axis=None))
    return terminal_chart((tiles + text.mark_text(dy=-25, color='white', fontSize=11, limit=alt.ExprRef(expr=f'width / {columns} - 12')).encode(text='sector:N')
                           + text.mark_text(color='white', fontSize=23, fontWeight='bold').encode(text='label:N')
                           + text.mark_text(dy=27, color='#c1cedd', fontSize=10, limit=alt.ExprRef(expr=f'width / {columns} - 12')).encode(text='count:N')).properties(height=max(160, ((len(rows)+2)//3)*140)))


def participation_chart(frame):
    rows = []
    for row in frame.itertuples():
        for status, count, order in (("In top movers", row.movers, 0), ("Other usable stocks", row.other, 1)):
            rows.append(dict(sector=row.sector, status=status, count=count, available=row.available,
                             share=count / row.available, order=order))
    base = alt.Chart(pd.DataFrame(rows))
    bars = base.mark_bar().encode(
        y=alt.Y('sector:N', sort=frame.sector.tolist(), title=None, axis=alt.Axis(labelLimit=165)),
        x=alt.X('share:Q', stack='zero', title='Share of usable screened sector stocks',
                scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format='.0%', tickCount=5)),
        color=alt.Color('status:N', title=None, scale=alt.Scale(domain=['In top movers', 'Other usable stocks'], range=['#37B68C', '#364458']), legend=alt.Legend(orient='bottom')),
        order=alt.Order('order:Q'),
        tooltip=['sector:N', 'status:N', alt.Tooltip('count:Q', title='Stocks'),
                 alt.Tooltip('available:Q', title='Usable sector stocks'), alt.Tooltip('share:Q', format='.1%')],
    )
    labels = alt.Chart(frame.assign(label=frame.apply(lambda row: f"{row.movers}/{row.available} ({row.share:.0%})", axis=1))).mark_text(
        align='left', dx=6, color='#ffffff', fontSize=12,
    ).encode(y=alt.Y('sector:N', sort=frame.sector.tolist(), title=None), x=alt.value(0), text='label:N')
    return terminal_chart((bars + labels).properties(height=max(240, len(frame)*36+110)))
