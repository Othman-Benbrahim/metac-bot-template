# Situational Alphabet — a Metaculus forecasting bot

*Othman Ben Brahim · bot 0.10.46 · skill [alphabet-situationnel](https://github.com/Othman-Benbrahim/alphabet-situationnel) 0.7.74 · MIT for the bot files*

This repository runs an open experiment: **does a structural reading of a situation forecast better than a plain base
rate?** Each binary question gets three forecasts, sealed before resolution and scored with the log score:

| Arm | Produced by |
|---|---|
| **A** | the language model alone (control) |
| **B** | a base rate: a reference class counted by code from open data when possible, otherwise estimated |
| **C** | the *situational alphabet*: 16 structural cards anchored in dated, sourced facts, turned into a probability by a deterministic engine starting from B |

The key result is C against B, with an anytime-valid sequential test. Nothing is claimed yet: the engine's
multipliers are hypotheses, and the reader (a language model) is being calibrated on a **synthetic world** whose truth
is known by construction.

- Abstract (English): [`ABSTRACT-alphabet.md`](ABSTRACT-alphabet.md)
- Full description, version history and decisions (French): [`README-alphabet.md`](README-alphabet.md)
- Sealed log of every forecast: [`registre/`](registre/)
- Companion bench on Solana token data, without text: [alphabet-chaine](https://github.com/Othman-Benbrahim/alphabet-chaine)

This is a fork of the Metaculus bot template; its original README is kept in
[`README-template-metaculus.md`](README-template-metaculus.md).
