# Keeping an LLM agent away from irreversible actions: notes from an open forecasting bot

*A partial answer, from a working system rather than a proposal. Othman Ben Brahim, November 2026.*

## Project overview

This repository runs an open-source forecasting agent on Metaculus. A language model reads a question, searches the
web, and produces a structured reading of the situation. Code then turns that reading into a probability, and the bot
posts it to the tournament.

Posting is the agent's real-world action. It cannot be undone: a forecast is scored as soon as it is posted, and every
later run on the question is scored too. The other actions with external effects follow the same rules: spending money
on model APIs, publishing a release, and writing to a public registry.

This is a low-stakes domain. That is why it makes a useful test bed: the same failure modes show up as in high-stakes
agents (overconfidence, a quietly changed rule, runaway cost), and they can be measured against resolved outcomes.

## Safety approach

**1. The model proposes; deterministic code decides.**
The language model never writes the number that gets posted. It writes a structured reading, a JSON dossier of cited
facts. Code then checks the dossier and repairs it.

The repair step is restricted by construction: it can only weaken the dossier. It removes unsupported claims and
illegible entries and caps excess; it never adds a fact, a link or a stronger intensity. A property-based test suite
(Hypothesis) checks this over hundreds of random dossiers. A deterministic engine then computes the probability, and
the posted value is clamped to a fixed range.

**2. A safe fallback is always ready, and it is the default.**
Every question has a plain base rate, computed by code from data series or reference classes. When the structured
reading is not trusted, the bot posts the base rate, and the reading is only computed and logged.

At the moment, the reading is not trusted in its main stratum (`POSTER_C = False`). Outcomes showed it was
overconfident, so the base rate is what gets posted there, and the reading stays sealed beside it. The reading's own
fallback order is code-defined: reading, then base rate, then model alone. This is a Simplex / runtime-assurance
pattern.

**3. No rule change acts before it is measured: shadow first, dated human decision.**
Any change to how readings are produced, validated or combined first runs *in shadow*. It is computed beside the
official path, logged, and never posted. A human author then promotes it with a dated decision, against a criterion
written before the data that will judge it.

Examples from this week:
- a reading without the hand-written matrix that was steering the model;
- a second, autoregressive base rate;
- empirically learned links.

**4. The validator is audited too.**
A validation rule that is edited can raise a score without anything improving. Every pull request that touches the
repair step or the engine replays all stored readings twice, once with the old code and once with the new. It then
publishes the list of verdicts that flip (`comparer_bascules.py`, run in CI on every pull request).

The first run caught an off-by-rounding refusal at a threshold boundary: 8 cases flipped, and nothing else.

**5. Hard caps on irreversible spending and actions.**
- **Cost:** each benchmark run stops before the next question would push spending past a dollar cap. The check uses
  the worst cost seen so far.
- **Volume:** scheduled tournament runs have a daily cap on how many questions they send.
- **No repeats:** questions already forecast are skipped.
- **No preview on live questions:** a dry run is only allowed in Metaculus's test area, because the rules forbid
  previews on open tournament questions.

**6. Humans hold the keys and the releases.**
- API keys live only in CI secrets, and error messages are masked before anything is written to the public registry.
- Releases (zips, tags) are published by the human author, never by the agent.
- Nothing is sent outside the pipeline (email, posts) without an explicit human request.

## Supporting evidence

All of the following is in this repository:

- **Test suites:** 209 tests, including property-based tests and replay determinism. They run on every pull request.
- **Public registries:** every reading, the official and shadow probabilities, and the replay data needed to reproduce
  each probability exactly (`registre/retro.jsonl`, `rejeu_banc.py`).
- **Version history:** the history in `README-alphabet.md` dates each rule change, with what triggered it and what it
  flipped.
- **Pre-registration documents:** each shadow has one, written before its first measurement.

## Limitations

- **The domain is low-stakes.** Posting a forecast is irreversible, but its cost is bounded. Nothing here has been
  tested on agents with physical or financial actuators.
- **The model still shapes the outcome indirectly.** It chooses what to search and which facts to cite. The
  weakening-only repair limits this but does not remove it.
- **Shadow-first slows adoption.** It suits a research system. A production system would also need a way to roll back
  fast.
- **A careless human can still bypass the safeguards.** The human gate depends on that person, and the caps are only as
  good as their settings.
- **The adversarial case is not covered.** These safeguards target honest failure, such as overconfidence, drift or
  runaway cost, not a deliberately deceptive agent.
