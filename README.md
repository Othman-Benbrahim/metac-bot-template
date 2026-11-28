# Situational Alphabet — a Metaculus forecasting bot

*Othman Ben Brahim · bot 0.10.522 · skill [alphabet-situationnel](https://github.com/Othman-Benbrahim/alphabet-situationnel) 0.7.77 · MIT for the bot files*

**Orientation (28 November 2026).** The project started as an open experiment: does a structural reading of a
situation (the *situational alphabet*, arm C) forecast better than a plain base rate (arm B)? Measurements showed that
the weak link was the translation of questions into cards by a language model, so the author changed the alphabet's
role: **it organises and compares situations; it no longer produces the probability on its own.** Arm C is still
computed and sealed, in shadow, and never posted. The synthetic world used to calibrate its reader is retired.

What a binary question goes through today:

| Step | What happens |
|---|---|
| Research | two independent searchers |
| Arm A | the language model alone, sealed before any card |
| Arm M | the alphabet "as a matryoshka": seven cards scored 1–4, shown in the posted comment; replaces A (a base rate computed by code is kept) |
| Coded bricks | rules applied to data, no language model, each behind a compatibility gate (question family × brick): price thresholds, counted events, staying in office, escalation, competitions (tennis and football Elo, elections), central bank, peace agreements during wars, ecosystem probes |
| Contradictor | sets a brick aside when a verified quote shows it does not apply |
| Safeguard | an extreme brick strongly contradicted by the model alone is held at 10% / 90% |
| Judge | may depart from the brick by 10 points at most |

Every brick that touches the posted forecast first passed a pre-registered test (`preenregistrements/`), except the
election brick, switched on by the author's decision with its risk declared; failed trials are closed and kept. Around the bot: an ecosystem map, our own data collection and a link-and-metadata data
well (never article text), a labelled source registry, and two-layer news briefs. Market odds and crowd forecasts are
never used as inputs. Full description, in French: [`README-alphabet.md`](README-alphabet.md), section
« Orientation actuelle ».

- Abstract (English): [`ABSTRACT-alphabet.md`](ABSTRACT-alphabet.md)
- Full description, version history and decisions (French): [`README-alphabet.md`](README-alphabet.md)
- Sealed log of every forecast: [`registre/`](registre/)
- Companion bench on Solana token data, without text: [alphabet-chaine](https://github.com/Othman-Benbrahim/alphabet-chaine)

This is a fork of the Metaculus bot template; its original README is kept in
[`README-template-metaculus.md`](README-template-metaculus.md).
