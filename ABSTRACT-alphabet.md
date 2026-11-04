# Situational Alphabet Bot — Abstract

*Othman Ben Brahim · bot version 0.2.1 · skill alphabet-situationnel 0.7.49 · Metaculus FutureEval*

**Question.** Does a structural reading of a situation improve on a plain base rate when forecasting real-world events?
This bot tests that question in the open, on Metaculus, against questions whose answers nobody knows yet.

**What it reads with.** The *situational alphabet* is a small, fixed set of 16 cross-domain structural cards (threshold,
network, hierarchy, cycle, constraint…) applied across 13 strata of reality (geopolitics, economy, domestic
politics…). A reading must anchor each card in dated, sourced facts, and may legitimately conclude that no structure is
present. A deterministic engine turns an accepted reading into a probability by adjusting a reference-class frequency.
The skill, its engine and its validation rules are documented in
[`alphabet-situationnel/README.md`](alphabet-situationnel/README.md) (in French).

**Design: three arms per binary question.**

| Arm | Probability produced by | Purpose |
|---|---|---|
| **A** | the language model alone (Metaculus template bot) | control, sealed before any reading |
| **B** | a reference class found by web search ("how often did this happen in comparable cases?") | base rate |
| **C** | the alphabet: reading of the situation, then the engine, starting from B | C vs B = what the reading adds |

The bot posts C when the engine produces a number, B when the reading finds no structure, and A otherwise (no honest
base rate, question outside the skill's scope, reading rejected by the engine). The engine currently quantifies
geopolitics only; that restriction will be lifted only on measured evidence. The language model never invents a
number: the engine accepts or rejects the reading, and rejections are logged.

**Pre-registration.** Every forecast is written, with all three arms and the full reading dossier, to a SHA-256-sealed
log committed to this repository before the question resolves. Git history timestamps each entry; a tampered line is
detected and excluded from scoring.

**Evaluation.** Forecasts are scored with the logarithmic score, as Metaculus does. The key result is the paired gain
of C over B (and of C over A), in peer-score points: 100 × the mean difference in ln p on the realized outcome, with a
check on whether a single question drives the result. The Brier score is reported only as a robustness check. Each
question counts once; dry runs and test-area questions are excluded.

**Limits, stated up front.** No human in the loop (tournament rule): this measures *the skill as played by a language
model*. The engine's card multipliers are still hypothetical; testing them is the point. Results on a few dozen
questions support no conclusion either way.

**Run.** Every 20 minutes the bot checks for new MiniBench questions, with a hard cap of three new questions per day.
Code: `alphabet_bot.py`, `alphabet_pipeline.py`, `score_registre.py`; offline tests in `tests/`, run on every push.
Full description (French): [`README-alphabet.md`](README-alphabet.md). License: MIT for the bot files
(`LICENSE-alphabet`).
