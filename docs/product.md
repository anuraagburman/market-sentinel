# Product (blueprint §1–5)

Blueprint v1, 2026-09-26. Examples, thresholds and schedules are illustrative unless attributed.

## Thesis
Investors have prices, headlines, screeners and charts but little time to connect them to their own
exposure. Market Sentinel organizes inputs around the investor's **next decision**: find potentially
material changes, gather supporting and conflicting evidence, place them in market context, present
a short brief. Every brief answers: what changed, why it may matter, what remains unknown, what
would change the assessment.

Promise: understand the most important portfolio issues in ~5 minutes. "Early" means earlier
recognition of public information within the feed's real latency — never privileged information or
price prediction. Defensibility = decision taxonomy, point-in-time evidence archive, evaluation
corpus, longitudinal thesis history. Model access is not a moat.

## Initial decisions
- Market: liquid US-listed common equities + a few benchmark ETFs.
- User: active individual investor, ~10–30 holdings, 20–50 name watchlist.
- Horizon: swing and multiweek first; intraday later with proper feeds.
- Input: CSV holdings import with explicit reconciliation and manual correction.
- Execution: research, conditional plans, paper records. **No live orders.**
- Delivery: responsive web app, editorial, evidence-first.

## Success and boundaries
Primary success: users correctly identify material portfolio issues and understand evidence and
uncertainty faster than their current workflow. Session length, trade count, click-through are
diagnostics, not goals. Returns in paper studies can't establish effectiveness alone.
Excluded: leverage, options recommendations, auto-rebalancing, social leaderboards, live execution.
Monetization later; never tied to trading frequency, brokerage referrals, or promoted stocks.

## The three jobs
### Morning portfolio analysis
Scheduled pre-session brief in user's local timezone → prioritized review list, not a daily trade.
Acceptance: imports reconcile before activation; brief links to exact holdings version; every
material claim has evidence; missing prices never become zero; a quiet day may say "No new material
changes found within current coverage"; a failed news provider produces a visible partial state.

### Discovering stocks
Theme + horizon + liquidity + exclusions + portfolio context → natural language becomes visible,
editable filters → deterministic screen → JEV bounded judgments → short ranked list. Each candidate
shows why it matched, a counterargument, missing info, incremental exposure.
Acceptance: inclusion reason and data date on every result; constraints respected; no invented
results to fill an empty screen; exclusions inspectable; popularity/recent performance never
silently become quality scores.

### Preparing for a volatile day
Event timeline, exposed holdings, feed freshness, plausible scenarios. User writes action and
invalidation conditions, saves a paper plan; during the session the product reports changes
relative to those conditions, not fresh recommendations on every tick.
Acceptance: market-wide vs company-specific effects distinguished; buy and sell prep both
supported; "wait for information" is first-class; stale feed suppresses time-sensitive readiness.

## UX principles
- Every decision surface shows observation time, source coverage, horizon, evidence status,
  unresolved questions. Facts, calculations, interpretations labeled distinctly.
- Confidence is about a specific judgment, never the probability a trade makes money.
- Progressive disclosure: concise default, one click to excerpts, calculations, versions,
  contrary evidence. Corrections create a visible revision marker + "changed since last view".
- Visual: off-white canvas, dark text, gray separators, one muted accent; warning color only with
  text + icon. Tabular numerals, consistent dates, few stable components.
- Never: flashing prices, countdowns, confetti, streaks, trader rankings, "hot picks", big buy
  buttons. Verbs: Investigate, Compare evidence, Save plan, Review exposure, Record decision.
  Motion explains state, respects reduced motion, never creates urgency.
- Purposeful creativity: "What changed" diff vs last brief; evidence trail; scenario switcher;
  thesis timeline. Causal hypothesis map only in detail view, edges labeled observed vs proposed,
  with a text alternative.

## Information architecture
Four destinations: **Today, Portfolio, Discover, Plans**. Stock detail opens consistently from all.
Evidence: side panel on wide screens, full page on mobile. Settings: data coverage, import history,
preferences, privacy, notifications. Today = portfolio context + top 3 material changes + upcoming
events. Quiet days stay quiet; optional "View monitored coverage" link.

Accessibility: keyboard nav, visible focus, labeled controls, heading structure, contrast, zoom;
charts have summaries and tables. Test loading, empty, stale, partial, conflicting, failure states
as carefully as the happy path.

## Surfaces
- **Today:** header (session, timezone, snapshot time, coverage). Up to 3 issues, each: holding,
  observation, interpretation, evidence status, next research question, Investigate. Event times in
  exchange time + local equivalent. Good copy: "ExampleCo lowered its revenue outlook. Your position
  is 8% of the imported portfolio. The company release supports the guidance change; the effect on
  next year's margins is unresolved." + source/timestamp line. Never "AI is 92% sure you should sell."
- **Portfolio & import:** allocation, concentration, sectors, catalysts, coverage gaps. Position P&L
  ≠ portfolio performance; snapshot without cash flows can't give a return series. Missing cost
  basis = unavailable, not zero. Import wizard: sample CSV, column mapping, instrument matching,
  row errors, reconciliation preview, explicit confirm. Duplicates aggregate only after account/lot
  semantics. Shorts, derivatives, ambiguous currencies flagged, not transformed.
- **Discover & stock detail:** search + editable filters + short list. Detail: context, why it
  surfaced, fundamentals, catalyst timeline, evidence, counterevidence, portfolio fit; chart is
  secondary. Evidence panel: publication + retrieval times, licensed excerpts, claim links, corrections.
- **Plans & thesis:** intent, horizon, thesis, entry/reduction conditions, invalidation, catalysts,
  paper size, open questions; "do nothing until" conditions; deterministic before/after exposure.
  Thesis states: Supported, Under review, Invalidated, Insufficient evidence — each change points to
  a claim; no thesis-health percentage; original immutable, revisions need a reason.
- **Shared state model:** every surface takes `ready | running | partial | stale | failed |
  no_material_change`. Empty coverage ≠ no material change. Explicit retry; last good snapshot shown
  separately. API errors never appear as financial conclusions.

## MVP scope
First vertical slice: import CSV → confirm → morning brief from a frozen snapshot → open one cited
investigation → record a research decision. Runs on fixtures with no credentials.

MVP acceptance:
- 20-holding import with duplicate, ambiguous, missing-price, missing-cost-basis cases handled visibly.
- Brief produced once per portfolio version + session cutoff; idempotent retries.
- Every issue: reason, evidence refs, freshness state, decision version.
- Can abstain; can publish partial brief without fabricated reassurance.
- Discovery: explicit filters, small explainable queue.
- Volatile-day: conditional buy and sell plans incl. wait condition.
- Users can inspect corrections, export decision journal, delete imported holdings.

Later: intraday (after entitlements + measured latency), historical analogues (after point-in-time
data), paper fill simulation, options, factor models, cross-market.

Portfolio construction: start with transparent constraints (max single-name weight, sector limits,
cash reserve, exclusions); before/after weights. Correlations are uncertain and lookback-dependent.
Many tickers ≠ diversified. Optimizer optional, later.

Research plan: 5–8 active-investor interviews (morning routine, hard decisions, why they ignore
alerts); task tests on sample portfolios; record time, comprehension, confidence calibration.
Exploratory only.
