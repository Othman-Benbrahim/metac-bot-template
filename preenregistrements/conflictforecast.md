# ConflictForecast contre B (préenregistrement, 2026-11-17)

Décision d'auteur du 2026-11-17 : ConflictForecast (Mueller et Rauh) est un modèle concurrent
(claude/hypotheses-concurrentes.md). Seule compte la qualité de la prévision.

## Pourquoi un indicateur, et non un concurrent direct

Ses cibles (conflit armé, toute violence, intensité, à 3 et 12 mois) ne sont pas celles des questions ACLED de
ForecastBench (« plus d'événements que la moyenne récente ? »). On ne peut pas comparer ses probabilités aux nôtres
question par question. On le lit donc comme un indicateur qui corrige B, comme nos mécanismes.

## États, fixés avant de voir le moindre résultat

- **ESC** (escalade prévue) : prévision d'intensité à 3 mois du modèle « best » (`int_lnbest_03`, `p_all`) moins le
  niveau observé au dernier mois de données (`actuel`) > 0,5 → 1 ; sinon 0.
- **AV** (toute violence probable) : p(anyviolence, 3 mois, `p_all`) ≥ 0,5 → 1 ; sinon 0.
  Les versions 2021-2024 donnent des pourcentages : ramenés à [0 ; 1].

## Règle contre la fuite

Une version dont les dernières données sont du mois M ne sert qu'à partir du 25 du mois M+1. Pour une question posée
le jour d (date du jeu), on prend la version la plus récente utilisable à d.

## Test

- Questions : `registre/combinaisons.jsonl` (ACLED « une fois », ForecastBench, depuis 2024-07-21), pays connu.
- Pour chaque indicateur, chaque état et chaque famille : δ = ln((O+0,5)/(E+0,5)) sur l'exploration (jeux avant
  2026-01-01), appliqué en logit à B sur la confirmation (jeux de 2026).
- Une case est jugée si elle a au moins 10 questions de chaque côté.
- Bootstrap par jeu ; risque `es.risque_corrige(1) / k`, k = nombre de cases jugées.
- Confirmé si la borne haute de l'écart de perte log (ajusté − B) est < 0.
- Attendu : ESC=1 et AV=1 relèvent la violence. La mobilisation sert de témoin : un effet là serait suspect.

## Réserves écrites d'avance

- Peu de questions de 2026 : il est probable que rien ne soit jugeable, ou que l'intervalle soit large.
- Même en cas de confirmation, l'indicateur reste en ombre jusqu'à une décision datée de l'auteur.
- Citation : Mueller et Rauh (2022), JEEA 20(6) ; Mueller, Rauh et Seimon (2024), Data & Policy 6.
