from __future__ import annotations

from datetime import datetime
from html import escape

import streamlit as st


PAGE_LABELS = {
    "Introduction": ("Introduction", "MARKET OVERVIEW", "Live markets and AI-assisted intelligence."),
    "Top Movers": ("Top Movers", "MARKET LEADERSHIP", "Weekly price leadership, sector breadth, and current news catalysts."),
    "Research": ("Research", "LLM WORKSPACE", "Ask, compare, and synthesize market evidence."),
    "Equity Report": ("Equity Research", "REPORT WORKSPACE", "Decision-ready company and peer analysis."),
    "Stock Screener": ("Stock Screener", "DISCOVERY WORKSPACE", "Filter a universe by fundamental and market criteria."),
    "Portfolio Lab": ("Portfolio Lab", "ALLOCATION WORKSPACE", "Optimize allocations and review agent decisions."),
    "Deep Research": ("Deep Research", "INVESTIGATION WORKSPACE", "Run a sourced, multi-step company or thematic investigation."),
}


def inject_app_shell_css() -> None:
    """Apply the shared Axiom terminal visual system to native Streamlit UI."""
    st.markdown(
        """
        <style>
        :root {
          --ax-bg: #071018;
          --ax-panel: #0b1620;
          --ax-panel-2: #0f1d29;
          --ax-panel-3: #132432;
          --ax-line: #263847;
          --ax-line-soft: #1b2b38;
          --ax-text: #e8edf2;
          --ax-muted: #8fa2b3;
          --ax-dim: #5f7486;
          --ax-amber: #f0a51a;
          --ax-amber-2: #ffc24a;
          --ax-cyan: #26c6da;
          --ax-green: #35d07f;
          --ax-red: #ff5964;
        }

        html, body, [class*="css"] {
          font-family: "Arial Narrow", "Roboto Condensed", Inter, "Segoe UI", sans-serif;
          color: var(--ax-text);
        }
        .stApp, [data-testid="stAppViewContainer"] { background: var(--ax-bg); color: var(--ax-text); }
        [data-testid="stHeader"] { background: rgba(7,16,24,.97); border-bottom: 1px solid var(--ax-line); height: 2.25rem; }
        [data-testid="stToolbar"] { right: .25rem; }
        [data-testid="stMainBlockContainer"] { max-width: 1680px; padding: 1rem 1.1rem 3.25rem; }

        [data-testid="stSidebar"] { width: 218px !important; background: #06111b; border-right: 1px solid var(--ax-line); }
        [data-testid="stSidebar"] > div:first-child { padding-top: .7rem; }
        [data-testid="stSidebar"] * { color: var(--ax-text); }
        [data-testid="stSidebar"] .stCaption { color: var(--ax-muted) !important; }
        [data-testid="stSidebar"] hr { margin: .8rem 0; border-color: var(--ax-line); }
        [data-testid="stSidebar"] [data-testid="stExpander"] { border: 1px solid var(--ax-line); background: #091722; border-radius: 3px; }
        [data-testid="stSidebar"] [data-baseweb="select"] > div,
        [data-testid="stSidebar"] input { background: #0b1a26 !important; border-color: var(--ax-line) !important; color: #fff !important; }

        .ax-brand { padding: .18rem .15rem .1rem; font-size: 1.05rem; letter-spacing: .01em; color: #fff; }
        .ax-brand strong { font-weight: 780; color: #fff; }
        .ax-brand span { font-weight: 430; color: #d4dee6; }
        .ax-tagline { padding: 0 .15rem .8rem; color: #8ca0b0; font-size: .57rem; letter-spacing: .15em; }
        .ax-sidebar-label { margin: .1rem 0 .35rem; color: var(--ax-dim); font-size: .61rem; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; }

        [data-testid="stSidebar"] div[role="radiogroup"] { gap: 0; }
        [data-testid="stSidebar"] div[role="radiogroup"] label {
          min-height: 2.8rem; margin: 0 -.75rem; padding: .65rem 1rem; border-radius: 0;
          border-left: 3px solid transparent; transition: background-color .12s ease, border-color .12s ease;
        }
        [data-testid="stSidebar"] div[role="radiogroup"] label:hover { background: #0d1d29; }
        [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) { background: #10202c; border-left-color: var(--ax-amber); }
        [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p { color: var(--ax-amber-2); }
        [data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child { display: none; }
        [data-testid="stSidebar"] div[role="radiogroup"] label p { font-size: .78rem; font-weight: 680; letter-spacing: .015em; }

        .ax-command-shell { border: 1px solid var(--ax-line); background: #08141e; padding: .45rem .55rem; margin: 0 0 .55rem; }
        .ax-market-strip { display: grid; grid-template-columns: repeat(5, 1fr); border: 1px solid var(--ax-line); border-left: 3px solid var(--ax-amber); margin-bottom: .7rem; background: #091722; }
        .ax-market-item { display: flex; justify-content: space-between; gap: .55rem; padding: .42rem .7rem; border-right: 1px solid var(--ax-line); font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: .68rem; }
        .ax-market-item:last-child { border-right: 0; }
        .ax-market-name { color: var(--ax-muted); }
        .ax-market-state { color: var(--ax-dim); }

        .ax-page-head { display: flex; justify-content: space-between; align-items: end; border: 1px solid var(--ax-line); border-left: 3px solid var(--ax-amber); background: var(--ax-panel); margin: 0 0 .75rem; padding: .72rem .85rem; }
        .ax-page-kicker { color: var(--ax-amber); font-size: .61rem; font-weight: 800; letter-spacing: .14em; }
        .ax-page-head h1 { margin: .13rem 0 0; color: var(--ax-text); font-family: "Arial Narrow", "Roboto Condensed", sans-serif; font-size: 1.55rem; line-height: 1; letter-spacing: -.015em; }
        .ax-page-head p { margin: 0; color: var(--ax-muted); font-size: .72rem; }
        .ax-live { display: inline-flex; align-items: center; gap: .4rem; color: var(--ax-muted); font: .62rem ui-monospace, Consolas, monospace; }
        .ax-live:before { content: ""; width: 6px; height: 6px; border-radius: 50%; background: var(--ax-green); }

        h1, h2, h3, h4 { color: var(--ax-text) !important; font-family: "Arial Narrow", "Roboto Condensed", Inter, sans-serif !important; letter-spacing: .005em; }
        h2 { font-size: 1.35rem !important; }
        h3 { font-size: .98rem !important; font-weight: 750 !important; border-left: 3px solid var(--ax-amber); padding-left: .55rem !important; }
        h4 { font-size: .82rem !important; }
        p, label, .stMarkdown { line-height: 1.42; }
        [data-testid="stCaptionContainer"] { color: var(--ax-muted); font-size: .7rem; }

        .stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {
          min-height: 2.25rem; border-radius: 3px; border: 1px solid #3a5061; background: #10202c;
          color: var(--ax-text); font-size: .72rem; font-weight: 780; letter-spacing: .035em; box-shadow: none;
        }
        .stButton > button:hover, .stDownloadButton > button:hover { border-color: var(--ax-amber); color: var(--ax-amber-2); }
        .stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] > button[kind="primary"] {
          background: var(--ax-amber); border-color: var(--ax-amber); color: #111820;
        }
        .stButton > button[kind="primary"]:hover, [data-testid="stFormSubmitButton"] > button[kind="primary"]:hover { background: var(--ax-amber-2); color: #071018; }

        [data-baseweb="input"] > div, [data-baseweb="select"] > div, textarea {
          border-color: var(--ax-line) !important; border-radius: 3px !important; background: #091722 !important; color: var(--ax-text) !important;
        }
        input, textarea { color: var(--ax-text) !important; caret-color: var(--ax-amber) !important; }
        input::placeholder, textarea::placeholder { color: #688093 !important; }
        [data-baseweb="input"] > div:focus-within, [data-baseweb="select"] > div:focus-within { border-color: var(--ax-amber) !important; box-shadow: 0 0 0 1px var(--ax-amber) !important; }
        [data-testid="stForm"] { border: 1px solid var(--ax-line); border-radius: 3px; background: var(--ax-panel); padding: .85rem .9rem .2rem; }

        [data-baseweb="tab-list"] { gap: 0; border: 1px solid var(--ax-line); background: #091722; }
        [data-baseweb="tab"] { height: 2.55rem; padding: 0 1rem; border-right: 1px solid var(--ax-line); color: var(--ax-muted); font-size: .68rem; font-weight: 750; letter-spacing: .045em; }
        [aria-selected="true"][data-baseweb="tab"] { color: var(--ax-amber); background: #0f1e2a; }
        [data-baseweb="tab-highlight"] { background: var(--ax-amber); height: 2px; }

        [data-testid="stMetric"] { padding: .42rem .7rem; border: 1px solid var(--ax-line); background: #0a1823; }
        [data-testid="stMetricLabel"] { color: var(--ax-muted); font-size: .65rem; letter-spacing: .04em; text-transform: uppercase; }
        [data-testid="stMetricValue"] { color: var(--ax-text); font: 700 1.2rem ui-monospace, SFMono-Regular, Consolas, monospace; }
        [data-testid="stMetricDelta"] { font-family: ui-monospace, Consolas, monospace; }
        [data-testid="stDataFrame"] { border: 1px solid var(--ax-line); border-radius: 2px; overflow: hidden; }
        [data-testid="stAlert"] { border-radius: 2px; border: 1px solid var(--ax-line); background: #0d1d29; color: var(--ax-text); }
        [data-testid="stExpander"] { border: 1px solid var(--ax-line); border-radius: 2px; background: #091722; }
        [data-testid="stChatMessage"] { background: #0b1823; border: 1px solid var(--ax-line); border-radius: 2px; padding: .75rem .85rem; }
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] { max-width: 1100px; color: #cbd9e4; font-size: .76rem; line-height: 1.58; }
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h3 { margin: 1rem 0 .4rem!important; padding: .32rem 0 .32rem .6rem!important; border-left: 3px solid var(--ax-amber)!important; border-bottom: 1px solid #19354a; color: #eef6fc!important; font-size: .82rem!important; text-transform: uppercase; letter-spacing: .055em; }
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h3:first-child { margin-top: .1rem!important; }
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p { margin: .3rem 0 .65rem; }
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] ul,
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] ol { margin: .25rem 0 .75rem; padding-left: 1.35rem; }
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li { margin: .24rem 0; padding-left: .18rem; }
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li::marker { color: var(--ax-cyan); font-weight: 800; }
        [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] strong { color: #f2f7fb; }
        [data-testid="stChatInput"] { background: #071018; }
        [data-testid="stChatInput"] textarea { border-color: #3a5061 !important; }
        [data-testid="stPlotlyChart"], [data-testid="stArrowVegaLiteChart"] { border: 1px solid var(--ax-line); background: var(--ax-panel); }
        [data-testid="stCheckbox"] label span { font-size: .72rem; }
        [role="radiogroup"] label p { font-size: .72rem; }

        .ax-research-intro { display: grid; grid-template-columns: 1.35fr .65fr; gap: .7rem; margin: .15rem 0 .8rem; }
        .ax-terminal-panel { border: 1px solid var(--ax-line); background: var(--ax-panel); padding: .85rem; }
        .ax-terminal-panel h3 { margin: 0 0 .55rem !important; }
        .ax-terminal-panel p { color: var(--ax-muted); font-size: .75rem; margin: .25rem 0; }
        .ax-security-head { display: flex; justify-content: space-between; align-items: center; gap: 1rem; border: 1px solid var(--ax-line); background: #091722; padding: .7rem .8rem; margin: 0 0 .55rem; }
        .ax-security-symbol { color: var(--ax-text); font: 800 1.45rem "Arial Narrow", sans-serif; }
        .ax-security-meta { color: var(--ax-muted); font: .66rem ui-monospace, Consolas, monospace; margin-top: .15rem; }
        .ax-security-context { color: var(--ax-amber); font: 700 .68rem ui-monospace, Consolas, monospace; text-align: right; }
        .ax-shortcuts { display: grid; grid-template-columns: 1fr 1fr; gap: 1px; background: var(--ax-line); border: 1px solid var(--ax-line); }
        .ax-shortcut { background: #0b1823; padding: .55rem .65rem; color: #b8c6d1; font-size: .68rem; }
        .ax-shortcut b { color: var(--ax-cyan); display: block; margin-bottom: .16rem; }

        .ax-statusbar { position: fixed; z-index: 990; left: 218px; right: 0; bottom: 0; display: flex; gap: 1rem; align-items: center; min-height: 1.8rem; padding: .3rem .8rem; border-top: 1px solid var(--ax-line); background: #06111b; color: var(--ax-muted); font: .61rem ui-monospace, Consolas, monospace; }
        .ax-statusbar b { color: var(--ax-text); }
        .ax-status-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--ax-green); }

        @media (max-width: 900px) {
          [data-testid="stMainBlockContainer"] { padding: .75rem .65rem 3rem; }
          .ax-market-strip { grid-template-columns: 1fr 1fr; }
          .ax-market-item:nth-child(n+4) { display: none; }
          .ax-page-head { align-items: start; flex-direction: column; gap: .45rem; }
          .ax-page-head h1 { font-size: 1.3rem; }
          .ax-research-intro { grid-template-columns: 1fr; }
          .ax-security-head { align-items: start; flex-direction: column; }
          .ax-security-context { text-align: left; }
          .ax-statusbar { left: 0; overflow-x: auto; white-space: nowrap; }
          [data-baseweb="tab"] { padding: 0 .65rem; }
        }
        @media (prefers-reduced-motion: reduce) { * { scroll-behavior: auto !important; transition: none !important; } }

        /* Introduction dashboard */
        .intro-controls-anchor + div { margin-bottom: .35rem; }
        .intro-topline { display:flex; justify-content:space-between; align-items:center; padding:.25rem .1rem .65rem; color:#748da6; font:600 .66rem ui-monospace,Consolas,monospace; letter-spacing:.04em; }
        .intro-title { color:#eef6ff; font:800 1.45rem "Arial Narrow",Inter,sans-serif; letter-spacing:.035em; margin-right:1rem; }
        .intro-topline b { color:#20e7ad; font-size:.67rem; }.live-dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:#20e7ad;margin-right:.38rem;box-shadow:0 0 9px #20e7ad}
        .ticker-row{display:grid;grid-template-columns:repeat(4,1fr);background:#071522;border:1px solid #17334b;margin-bottom:.55rem}.ticker-row.intro-five{grid-template-columns:repeat(5,1fr)}.ticker-row>div{display:grid;grid-template-columns:1fr auto;gap:.15rem .7rem;padding:.48rem .75rem;border-right:1px solid #17334b}.ticker-row>div:last-child{border:0}.ticker-row small{color:#9bb0c5;font-size:.62rem}.ticker-row strong{grid-row:2;color:#eaf4ff;font:700 .78rem ui-monospace,monospace}.ticker-row em{grid-row:2;color:#20e7ad;font:700 .65rem ui-monospace,monospace}.ticker-row em.down,.loss,.market-table-row em.down,.row em.down{color:#ff4f78!important}.ticker-row em.up,.market-table-row em.up,.row em.up{color:#20e7ad!important}
        .intro-grid{display:grid;grid-template-columns:1.45fr 1.45fr 1.35fr;gap:.55rem}.terminal-card{border:1px solid #193953;background:linear-gradient(145deg,#091927,#07141f);box-shadow:inset 0 1px 0 rgba(255,255,255,.02);padding:.72rem}.market-main{grid-column:1/3}.ai-brief{grid-column:3;grid-row:1/3}.card-head{display:flex;justify-content:space-between;align-items:start}.card-head span,.terminal-card h3{font-size:.74rem;font-weight:800;margin:0;color:#eef6ff}.card-head h2{font:800 1.62rem ui-monospace,monospace!important;margin:.12rem 0 .25rem!important}.card-head h2 b{font-size:.82rem;color:#20e7ad}.range-tabs{display:flex;border:1px solid #17334b}.range-tabs i{font-style:normal;font-size:.57rem;padding:.28rem .48rem;color:#85a0b9}.range-tabs i:first-child{background:#103a69;color:#fff}.intro-chart{width:100%;height:155px}.grid path{stroke:#17334b;stroke-width:1;fill:none}.cyan-line{fill:none;stroke:#19d6f5;stroke-width:2}.amber-line{fill:none;stroke:#ff9f2e;stroke-width:1.7}.area{fill:url(#area)}.chart-axis,.mini-axis{display:flex;justify-content:space-between;color:#718ba3;font: .54rem ui-monospace,monospace}
        .brief-head{display:flex;align-items:center;gap:.5rem;border-bottom:1px solid #17334b;padding-bottom:.55rem}.brief-head b{font-size:.82rem}.brief-head small{margin-left:auto;color:#7791aa}.ai-star{color:#9f5cff;font-size:1.2rem}.ai-brief>p{font-size:.72rem;color:#c7d6e5;line-height:1.55;margin:.7rem 0}.insight{border:1px solid #21435c;padding:.55rem;margin:.48rem 0;background:#0b2030}.insight b{display:block;font-size:.68rem;margin-bottom:.2rem}.insight span{display:block;color:#a7bbce;font-size:.62rem;padding-left:1.2rem}.green b{color:#20e7ad}.red b{color:#ff557b}.amber b{color:#ffc044}
        .mini-grid{grid-column:1/3;display:grid;grid-template-columns:1fr 1fr .82fr;gap:.55rem}.terminal-card h3{padding-bottom:.5rem;border-left:0!important;border-bottom:1px solid #17334b}.terminal-card h3 small{float:right;color:#20b9ff;font-size:.52rem}.row{display:grid;grid-template-columns:.7fr .75fr .7fr .8fr;align-items:center;min-height:31px;border-bottom:1px solid #132c40;font: .61rem ui-monospace,monospace}.row span{color:#afc1d1}.row em{color:#20e7ad;font-style:normal;font-weight:700}.spark{width:100%;height:25px}.mini-chart strong{display:block;font:800 1.25rem ui-monospace,monospace;margin:.75rem 0 .4rem}.mini-chart strong em{color:#ff4f78;font-size:.66rem;font-style:normal}.mini-chart>.spark{height:58px}
        .market-table-row{display:grid;grid-template-columns:1.35fr .8fr .65fr;gap:.4rem;align-items:center;min-height:29px;border-bottom:1px solid #132c40;font:.59rem ui-monospace,monospace}.market-table-row small{grid-column:1/-1;color:#9bb0c5;font-size:.55rem;overflow-wrap:anywhere}.ticker-row>div>small:last-child{grid-column:1/-1;overflow-wrap:anywhere}.market-table-row b{color:#dbe8f3}.market-table-row span{color:#a9bdce;text-align:right}.market-table-row em{font-style:normal;font-weight:750;text-align:right}.source-line{margin-top:.35rem;color:#638097;font:.52rem ui-monospace,monospace}.chart-empty{height:155px;display:grid;place-items:center;color:#7890a4;font-size:.67rem;border:1px dashed #17334b}.intro-sector .heatmap{grid-template-columns:repeat(4,1fr);height:auto;min-height:125px}.intro-sector .heatmap div{display:grid;place-content:center;text-align:center;padding:.42rem .3rem}.intro-assets{grid-column:2}.intro-sector{grid-column:1}
        .company-head{display:grid;grid-template-columns:1fr auto auto;gap:1.4rem;align-items:center;margin:.55rem 0}.company-head small{color:var(--ax-amber);font:.58rem ui-monospace,monospace;letter-spacing:.1em}.company-head h2{margin:.16rem 0 .1rem!important;font-size:1.65rem!important}.company-head p{margin:0;color:#87a0b5;font-size:.67rem}.company-price{min-width:125px;border-left:1px solid #234157;padding-left:1rem}.company-price span{display:block;color:#7790a5;font:.54rem ui-monospace,monospace}.company-price strong{display:block;color:#edf7ff;font:800 1.15rem ui-monospace,monospace;margin:.16rem 0}.company-price em{font:700 .62rem ui-monospace,monospace;color:#8299ad;font-style:normal}.company-price em.up{color:#20e7ad}.company-price em.down{color:#ff4f78}.company-layout{display:grid;grid-template-columns:1fr;gap:.55rem}.company-main{display:grid;gap:.55rem}.company-subgrid{display:grid;grid-template-columns:1.35fr .65fr;gap:.55rem}.company-metrics{display:grid;grid-template-columns:1fr 1fr;gap:0}.company-metric{display:flex;justify-content:space-between;gap:.8rem;padding:.5rem .55rem;border-bottom:1px solid #163148;font:.59rem ui-monospace,monospace}.company-metric:nth-child(odd){border-right:1px solid #163148}.company-metric span{color:#88a1b5}.company-metric b{color:#e8f2fa}.company-news ul{display:grid;grid-template-columns:1fr 1fr;column-gap:1rem}.company-news li{grid-template-columns:66px 10px 1fr auto}.company-news a{color:#b9d9ed;text-decoration:none}.company-news a:hover{color:#20d7f5}.company-news small{color:#617f96}.company-ai-title{margin:.6rem 0 .3rem;border-left:3px solid var(--ax-amber);padding-left:.55rem;color:#edf5fb;font-size:.76rem;font-weight:800;letter-spacing:.04em}.source-warning{margin-top:.5rem;padding:.5rem;border:1px solid #73552c;background:#251d13;color:#e8bd76;font-size:.62rem}
        /* Top movers */
        .movers-head{display:grid;grid-template-columns:minmax(260px,2fr) repeat(4,minmax(105px,.7fr));align-items:stretch;margin-bottom:.55rem;padding:0}.movers-head>div{padding:.75rem;border-right:1px solid #193953;display:flex;flex-direction:column;justify-content:center}.movers-head>div:last-child{border:0}.movers-head small,.movers-head span{color:#7892a8;font:.55rem ui-monospace,monospace;letter-spacing:.08em}.movers-head h2{margin:.12rem 0!important;font-size:1.55rem!important}.movers-head p{margin:0;color:#91a8ba;font-size:.62rem}.movers-head b{margin-top:.2rem;color:#eaf4ff;font:800 .95rem ui-monospace,monospace}.movers-head b.up{color:#20e7ad}.movers-head b.down{color:#ff4f78}
        .movers-grid{display:grid;grid-template-columns:1.55fr 1fr;gap:.55rem}.movers-table{grid-column:1/3;overflow-x:auto}.mover-row{display:grid;grid-template-columns:34px minmax(155px,1.5fr) minmax(115px,1fr) 80px 65px 65px 95px 75px;gap:.55rem;align-items:center;min-width:790px;min-height:40px;border-bottom:1px solid #132c40;font:.59rem ui-monospace,monospace}.mover-row>span:nth-child(n+4),.mover-row>em{text-align:right}.mover-row b{display:block;color:#edf6ff;font-size:.67rem}.mover-row small{display:block;max-width:210px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#718ba2;font-size:.52rem;margin-top:.12rem}.mover-row em{font-style:normal;font-weight:800}.mover-rank{color:#4c9ccd!important}.mover-header{min-height:29px;color:#718ba2;font-size:.52rem;font-weight:800;letter-spacing:.04em}.mover-header span:nth-child(n+4){text-align:right}
        .mover-sector-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:3px}.mover-sector-grid>div{min-height:78px;padding:.55rem;display:flex;flex-direction:column;justify-content:end}.mover-sector-grid b{font-size:.62rem}.mover-sector-grid strong{font:800 .83rem ui-monospace,monospace;margin:.18rem 0}.mover-sector-grid small{color:#c1d0dc;font-size:.5rem}.movers-news{max-height:550px;overflow:auto}.mover-news-group{display:grid;grid-template-columns:46px 1fr;border-bottom:1px solid #163148;padding:.42rem 0}.mover-news-group h4{grid-row:1/5;margin:.12rem 0!important;color:#20d7f5!important;font:.75rem ui-monospace,monospace!important}.mover-news-group a{display:block;padding:.2rem .35rem;color:#c8d9e6;text-decoration:none;font-size:.6rem}.mover-news-group a:hover{background:#10293b;color:#fff}.mover-news-group a span{display:block;color:#68869e;font-size:.5rem;margin-top:.1rem}.mover-no-news{color:#718ba2;font-size:.57rem;padding:.3rem}
        .world{grid-column:1}.world-map{height:125px;position:relative;background:radial-gradient(ellipse at center,#0d3450 0,#071622 65%);overflow:hidden}.world-map:before{content:"";position:absolute;inset:22px 8px;background:linear-gradient(25deg,transparent 40%,rgba(22,138,190,.22) 41%,transparent 43%),radial-gradient(ellipse at 30% 40%,#13628b55 0 18%,transparent 19%),radial-gradient(ellipse at 70% 42%,#13628b55 0 25%,transparent 26%)}.world-map span{position:absolute;font-size:.56rem;color:#b7cadb}.world-map b{color:#20e7ad}.ny{left:18%;top:45%}.lon{left:43%;top:25%}.tok{right:7%;top:35%}.tok b{color:#ff557b}.sha{right:24%;top:58%}
        .heat{grid-column:2}.heatmap{display:grid;grid-template-columns:repeat(4,1fr);gap:3px;height:125px}.heatmap div{background:linear-gradient(145deg,#0e8a58,#07563d);padding:.65rem .5rem;font-size:.55rem}.heatmap b{font-size:.7rem}.heatmap div:nth-child(5){grid-column:span 2}.heatmap .neg{background:linear-gradient(145deg,#7b263b,#491e31)}.updates{grid-column:3}.updates ul{list-style:none;padding:0;margin:.2rem 0}.updates li{display:grid;grid-template-columns:38px 10px 1fr;align-items:center;gap:.25rem;border-bottom:1px solid #142d40;padding:.4rem 0;color:#b7c8d8;font-size:.58rem}.updates time{color:#4ba9ec}.updates i{width:6px;height:6px;border-radius:50%;background:#20e7ad}.updates i.pink{background:#ff4f78}.updates i.yellow{background:#ffc044}.ask-label{font-size:.58rem;color:#8299af;font-weight:800;letter-spacing:.12em;margin:.7rem 0 .25rem}
        @media(max-width:1050px){.intro-grid{grid-template-columns:1fr 1fr}.market-main{grid-column:1/3}.ai-brief{grid-column:1/3;grid-row:auto}.mini-grid{grid-column:1/3}.updates{grid-column:1/3}.world{grid-column:1}.heat{grid-column:2}.movers-head{grid-template-columns:2fr repeat(2,1fr)}.movers-head>div:first-child{grid-row:span 2}.movers-grid{grid-template-columns:1fr}.movers-table{grid-column:1}.mover-sector-grid{grid-template-columns:repeat(4,1fr)}}
        @media(max-width:700px){.ticker-row,.ticker-row.intro-five{grid-template-columns:1fr 1fr}.ticker-row.intro-five>div:last-child{grid-column:1/3}.intro-grid{display:block}.terminal-card{margin-bottom:.55rem}.mini-grid{display:block}.mini-grid>.terminal-card{margin-bottom:.55rem}.intro-topline>span:last-child{display:none}.card-head{display:block}.range-tabs{margin:.3rem 0;width:max-content}.heatmap{grid-template-columns:1fr 1fr}.ticker-row>div:nth-child(even){border-right:0}.company-head{grid-template-columns:1fr}.company-price{border-left:0;border-top:1px solid #234157;padding:.55rem 0 0}.company-subgrid,.company-news ul{grid-template-columns:1fr}.company-metrics{grid-template-columns:1fr}.company-metric:nth-child(odd){border-right:0}.company-news li{grid-template-columns:62px 8px 1fr}.company-news small{display:none}.movers-head{grid-template-columns:1fr 1fr}.movers-head>div:first-child{grid-column:1/3;grid-row:auto}.mover-sector-grid{grid-template-columns:1fr 1fr}}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_command_bar() -> str:
    """Render the real global command input; submitted text routes to Research chat."""
    with st.container():
        left, action, hint = st.columns([7.2, 1.45, .8], vertical_alignment="bottom")
        with left:
            query = st.text_input(
                "Global command",
                key="terminal_command",
                placeholder="Search ticker, report, or command",
                label_visibility="collapsed",
            )
        with action:
            submitted = st.button("RUN ANALYSIS", type="primary", use_container_width=True, key="terminal_run")
        with hint:
            st.markdown('<div style="padding:.62rem .35rem;color:#8fa2b3;font:11px ui-monospace,Consolas,monospace">CTRL K</div>', unsafe_allow_html=True)
    return query.strip() if submitted and query.strip() else ""


def render_market_strip() -> None:
    items = ["S&P 500", "NASDAQ", "DOW", "RUSSELL 2000", "VIX"]
    cells = "".join(
        f'<div class="ax-market-item"><span class="ax-market-name">{name}</span><span class="ax-market-state">MARKET CONTEXT</span></div>'
        for name in items
    )
    st.markdown(f'<div class="ax-market-strip">{cells}</div>', unsafe_allow_html=True)


def render_page_header(page: str) -> None:
    title, kicker, description = PAGE_LABELS.get(page, (page, "WORKSPACE", ""))
    st.markdown(
        f'''<div class="ax-page-head"><div><div class="ax-page-kicker">{escape(kicker)}</div><h1>{escape(title)}</h1></div>
        <div><p>{escape(description)}</p><div class="ax-live">SYSTEM READY</div></div></div>''',
        unsafe_allow_html=True,
    )


def render_research_launchpad() -> None:
    st.markdown(
        """
        <div class="ax-research-intro">
          <div class="ax-terminal-panel">
            <h3>LLM Research Console</h3>
            <p>Use the command bar or chat field to ask a finance question, compare securities, review news and earnings, or build a company research report.</p>
            <p>Your existing LangGraph tools, conversation history, structured tables, and debug trace remain available here.</p>
          </div>
          <div class="ax-terminal-panel">
            <h3>Command Examples</h3>
            <div class="ax-shortcuts">
              <div class="ax-shortcut"><b>COMPARE</b>AAPL vs MSFT valuation</div>
              <div class="ax-shortcut"><b>ANALYZE</b>NVDA risks and catalysts</div>
              <div class="ax-shortcut"><b>EARNINGS</b>Latest AMZN takeaways</div>
              <div class="ax-shortcut"><b>REPORT</b>Full research on JPM</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_terminal_status(model_name: str, *, fmp_ready: bool, openai_ready: bool) -> None:
    now = datetime.now().astimezone().strftime("%b %d %Y  %H:%M %Z")
    st.markdown(
        f'''<div class="ax-statusbar"><span class="ax-status-dot"></span><b>AXIOM RESEARCH</b>
        <span>FMP: {'READY' if fmp_ready else 'OFFLINE'}</span><span>LLM: {'READY' if openai_ready else 'OFFLINE'}</span>
        <span>MODEL: {escape(model_name.upper())}</span><span>AS OF: {escape(now)}</span><span>/ SEARCH &nbsp; CTRL K COMMAND</span></div>''',
        unsafe_allow_html=True,
    )
