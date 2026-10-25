# Robo Advisor interruption review - 2026-10-24

User reports the local app reset completely, including the objective/mandate. No original process/browser trace is available to determine whether the Python process restarted, a new browser session was created, or another runtime failure occurred. The configured main health endpoint (7860) was unreachable during investigation; no matching accessible Windows application crash event was found. Neither observation proves the cause of the earlier reset.

Code review found synchronous full-screen collection with approximately 1,000 regular financial requests, three workers and 30-second cooldowns per 100 logical calls. Ten cooldowns alone can add about five minutes; request latency/retries add more. AI review has a separate 90-second request timeout with zero automatic retries. These are bounded operations but not a guaranteed whole-build completion time.

The app already stores completed evidence and a local portfolio before AI review. However, an interrupted AI stage leaves the local result marked not_requested and previously provided no saved-evidence retry. Session stage checkpoints now distinguish collecting, constructing and AI review; the submitted mandate is retained before collection. A matching interrupted local result now offers an explicit Retry AI review using saved evidence action. No work starts just because the page reruns, and a different saved result ID cannot inherit the interrupted review. Timeouts receive a safe specific diagnostic without raw errors/prompts.

Visible progress labels show each stage. Existing failed-review/local fallback and downloads remain. This repair improves interruption recovery in the same session; it does not add durable save/resume or restore state after a Python/server/browser-session reset. Those broader persistence gates remain open. No provider endpoints, model choice, request timeout, retry count or collection pacing were changed, and no live/paid call was made.

| Contract | Before | After |
| --- | --- | --- |
| Ordinary rerun provider/model calls | 0 | 0 |
| Explicit saved-evidence retry provider calls | 0 | 0 |
| Explicit review model attempts | At most 1 | At most 1 |
| AI request timeout / output cap | 90 seconds / 9,000 tokens | Unchanged |
| Input packet cap | 42KB | Unchanged |
| Live latency/cost | Not measured; pricing unknown | Not measured; no speed/cost claim |
