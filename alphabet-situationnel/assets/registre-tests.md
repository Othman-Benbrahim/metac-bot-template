# Registre des tests — alphabet situationnel

> Registre vide, à remplir. Chaque test se colle ici en deux parties, sans rien retoucher :
>
> 1. **Partie TEST**, avant l'échéance : la sortie de
>    `python3 scripts/moteur.py fiche-test --journal J.jsonl --id P-xxxx`.
> 2. **Partie RÉSULTAT**, après l'échéance : la sortie de
>    `python3 scripts/moteur.py fiche-resultat --journal J.jsonl --id P-xxxx --issue 0|1 --preuve "…" --date AAAA-MM-JJ`.
>    Depuis 0.7.44, ajouter `--source-utilisee "…" --source-conforme oui|non --mode positif|absence`
>    (et `--ecart-source "…"` si la source n'est pas celle du dossier).
>
> Puis : `python3 scripts/moteur.py ingerer assets/registre-tests.md` relit les blocs JSON, vérifie que chaque résultat
> correspond bien à sa prévision (empreinte), et score le registre. Le texte autour des blocs peut se lire et
> s'annoter ; les blocs `alphabet-test` et `alphabet-resultat` ne se modifient jamais : une prévision retouchée est
> refusée. Pour qu'un test compte dans V4, publier aussi la partie TEST chez un tiers horodaté avant l'échéance
> (`validation.md` §11 et §14).

<!-- Coller les tests ci-dessous, le plus ancien en premier. -->
