# Use AI Portfolio Architect

1. In Axiom, open **AI Robo Advisor** and choose **Portfolio architect**. Choose **Agent traders** on the same page for existing manual paper rounds and historical replay. Portfolio Lab retains Optimizer and AI Portfolio Manager; Portfolio Ideas is no longer exposed. Start the normal Axiom app with `python -m streamlit run app.py`; shared Settings supply credentials and model selection. The earlier standalone launcher is an optional historical export convenience.
2. Choose **SYNTHETIC DEMO** first. It works without keys, makes no external calls, and invents every market value. It demonstrates controls and software behavior; its apparent performance has no investment meaning.
3. Enter an **Investment objective**, such as “Build an aggressive five-year growth portfolio focused on AI with diversified risk.” Click **Interpret mandate**. Local interpretation extracts only explicit risk words, numeric year horizons and curated theme keywords; review every other requirement in the editor. AI interpretation is optional in live mode.
4. Review **Horizon**, **Risk preference**, **Hypothetical amount**, **Holdings** (5–15), **Allowed assets** and **Sizing method**. Open **Allocation limits, exclusions and themes** for cash, position/category caps, excluded sectors, forbidden tickers, themes and benchmark. These controls enforce the constraints. They do not assess personal suitability. Unsupported themes/benchmarks cannot be silently turned into research promises.
5. Click **Build portfolio**. If caps or exclusions leave insufficient capacity or eligible names, revise the mandate. No portfolio is fabricated to fill missing slots. The report preserves your previous valid result on failure.
6. Read **Allocation** for weights and hypothetical dollars, **Holding research** for supporting observations/counterarguments and sizing, **Risk & tradeoffs** for historical diagnostics and limitations, and **Investment committee** for initial-to-final changes, vulnerabilities, dissent and rejected alternatives.
7. Use **Evidence & exports** to download CSV, JSON or HTML. Exports use the saved evidence and do not refresh data or call AI. Raw objective text is omitted from exported JSON/HTML. Save up to six **session snapshots** and reopen them locally; download before ending the app because snapshots are not restored after restart.

## Live research

Choose **FMP live**, configure your own **FMP API Key** in Axiom Settings (or the focused launcher's sidebar) and explicitly Build. Your FMP subscription must cover quotes, profiles, TTM ratios and history. Successful partial data is retained. Missing eligible quotes, currency, classifications or liquidity can block candidates; missing ratios/history are disclosed. No current news, catalyst, sentiment, forward earnings, price target or fund look-through service is included.

Enable **Use bounded AI interpretation and specialist review** only when an OpenAI key and available structured-output model are configured. Interpret and Build each permit one model attempt, no automatic retry; repeat clicks are new actions and may incur charges. The review combines four responsibilities in one call and does not claim independent-agent consensus. Failed/refused/truncated/invalid output preserves the deterministic portfolio. Conviction is subjective, not probability of return; hard caps always apply.

Quote caches last five minutes and history six hours. **Refresh provider evidence on next Build** explicitly requests fresh collection. Check each quote's observation date and original retrieval times. A saved report can age without changing; a timestamp is not an executable market price. Reopening, navigating, editing presentation, saving and downloading do not collect or generate.

## Interpret the limits

Stock-sector caps and ETF-category caps are separate from underlying fund exposure. With any excluded stock sector, all ETFs are conservatively excluded because holdings cannot be verified. ETF duplication is a qualitative category warning, not a measured overlap percentage. Themes are curated preferences. Risk preference does not enforce a specific future loss or volatility ceiling.

Historical risk uses a common window, no missing-price filling and a zero cash-return assumption. The displayed static daily-rebalanced mix is not a historical strategy backtest; current constituents and fundamentals were not frozen in the past. FMP price adjustment is unverified and dividend cash flows are absent. Estimates can be unavailable or distorted by corporate actions. Zero history does not mean zero risk. Consult the report's sample count, dates, method and disclosures before interpreting figures.

To revise a prompt, click **Interpret mandate** again, edit the new mandate and Build. Changed controls do not alter previously saved recommendations. If evidence or AI fails, the prior report stays available with the failure message; review its dates before using it. There is no broker connection, scheduled monitoring or automatic rebalance.

## If Build reports no eligible securities

Open **Latest collection diagnostics** to see provider errors and per-ticker exclusions. A batch-quote plan restriction now triggers bounded individual FMP quotes automatically; quote eligibility checks still apply. Provider failures require checking endpoint access, credentials or network settings, not loosening allocation caps. Enable **Refresh provider evidence on next Build** and click **Build portfolio** to retry explicitly. These diagnostics remain visible alongside an older saved result and do not recollect data on ordinary reruns.
