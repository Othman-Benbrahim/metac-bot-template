# Situational Alphabet Bot — Abstract

*Othman Ben Brahim · bot version 0.9.4 · skill alphabet-situationnel 0.7.52 · Metaculus FutureEval*

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
| **B** | a reference class found by web search, open databases and already-resolved Metaculus questions (outcomes only); median of three estimates, each on a different source, whose arithmetic is recomputed by code; when a dated open-data series measures the resolution criterion exactly, a count computed by code is the base rate instead (the model's median kept in shadow) | base rate |
| **C** | the alphabet: reading of the situation, then the engine, starting from B | C vs B = what the reading adds |

The bot posts C when the engine produces a number, B when the reading finds no structure, and A otherwise (no honest
base rate, question outside the skill's scope, reading rejected by the engine). The engine currently quantifies
geopolitics only; that restriction will be lifted only on measured evidence. Outside geopolitics, the alphabet still
reads every binary question and the engine computes an *exploratory* C (scope restriction lifted for that computation
only): it is sealed and scored separately, by stratum, but never posted and never counted in the main result. Because the engine
can only raise a probability above the base rate, two shadow corrections are also sealed: a symmetric one (a candidate
pattern contradicted by the facts lowers the odds by the multiplier it would have added) and a learned logit offset.
Non-binary questions are read the same exploratory way, through one derived binary question (the model's median, or
its most likely option). The language model never invents a
number: the engine accepts or rejects the reading, and rejections are logged.

**Pre-registration.** Every forecast is written, with all three arms and the full reading dossier, to a SHA-256-sealed
log committed to this repository before the question resolves. Git history timestamps each entry; a tampered line, or a reading dossier that no
longer matches its seal, is detected and excluded from scoring. No forecast is posted without its sealed line.

**Evaluation.** Forecasts are scored with the logarithmic score, as Metaculus does. The key result is the paired gain
of C over B (and of C over A), in peer-score points: 100 × the mean difference in ln p on the realized outcome, with an
anytime-valid sequential test (betting e-values), so the score can be checked weekly without inflating false
positives, and an a-priori power estimate. The paired Brier score is also reported: it is the skill's own,
Metaculus-independent criterion for widening the engine's scope. A "null state" (no structure read) is never scored as
if it were a reading; before one is accepted, candidates dismissed only for lack of search get a targeted second
search, and null states are tracked separately by kind (evidence-based vs. blind spot). In a null state the reader also
describes, without naming any card, the dynamic the facts show: a corpus for later searching for a structure the
alphabet may lack. Each question counts once; dry
runs and test-area questions are excluded.

**Limits, stated up front.** No human in the loop (tournament rule): this measures *the skill as played by a language
model*. The engine's card multipliers are still hypothetical; testing them is the point. Results on a few dozen
questions support no conclusion either way.

**Run.** Every 20 minutes the bot checks for new MiniBench questions and forecasts every new open one (no daily cap since 0.6.0).
Code: `alphabet_bot.py`, `alphabet_pipeline.py`, `alphabet_puits.py`, `score_registre.py`; offline tests in `tests/`, run on every push.
Full description (French): [`README-alphabet.md`](README-alphabet.md). License: MIT for the bot files
(`LICENSE-alphabet`).
