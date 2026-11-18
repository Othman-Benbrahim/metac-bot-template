sources: registre/banc-cartes-ancrees.json, registre/banc-filtre-azure.json
constantes: 0,15; 4000
# Résultat : cartes ancrées (DÉCLENCHEUR, PROPORTION) — 2026-11-18

Run 44363011276 ([journal: 33 min]), bot 0.10.281, préenregistrement preenregistrements/cartes-ancrees.md. Deux lecteurs
(gpt-5-mini Azure, Claude Haiku 4.5 Bedrock), 114 questions distinctes, recherche gelée.

## Verdict principal (préenregistré) : ancrage NON retenu
Accord de rang entre les deux lecteurs sur DÉCLENCHEUR, sur les 57 questions communes : notes ancrées 0,326 contre
notes libres 0,356 (gain −0,03 ; seuil d'adoption +0,15). L'ancrage ne rend pas les deux lecteurs plus d'accord.
PROPORTION : trop peu de questions chiffrées (7 communes) pour juger.

## Ce que le banc montre quand même
- Faits rejetés par le code : 29 % (gpt, 9/31) et 34 % (Haiku, 22/65). Lecture des rejets de Haiku : la plupart ne
  sont pas des inventions mais des phrases copiées depuis les CRITÈRES DE RÉSOLUTION de la question, pas depuis la
  recherche (« This question will resolve as Yes if… ») ; le code les refuse à juste titre (ce n'est pas un fait daté).
- Un vrai cas de fuite attrapé : question jouée le 2026-02-15, Haiku cite « On July 19, 2026, Spain beat Argentina
  1–0 after extra time to win the 2026 FIFA World Cup », phrase absente de la recherche (connaissance postérieure ou
  invention). Rejetée par le code. C'est exactement le rôle prévu de l'ancrage : rien de ce qui n'est pas dans la
  recherche n'entre dans la note.
- Lien avec l'issue (descriptif) : DÉCLENCHEUR ancré quasi nul (Spearman 0,06 gpt, 0,08 Haiku) ; PROPORTION 0,30 sur
  20 questions (gpt), 0,03 (Haiku) : trop peu pour conclure.
- Refus du FILTRE DE CONTENU d'Azure : [journal: 22 questions sur 114 (19 %)] ; Haiku : aucun refus.
  CORRECTION : il ne s'agit PAS de passages sur la guerre ou la violence (première lecture erronée) ; les questions
  refusées portent sur les Oscars, le Bitcoin, un navigateur, Neymar, Lula, etc.

## Sonde du filtre Azure (run 44374896363, [journal: 0,01 $], bot inchangé)
Les 22 consignes refusées, rejouées avec la même recherche, une seule chose changée à la fois :
- identique : 22 refus sur 22 (le refus est reproductible, pas aléatoire) ;
- recherche ramenée à 4 000 caractères : 22/22 refus (la longueur n'y est pour rien ; refus même avec [journal: 1 055
  caractères] de recherche) ;
- sans l'exigence de copier mot pour mot : 19/22 refus ;
- sans les critères de résolution : 17/22 refus.
Lecture : le déclencheur est surtout la CONSIGNE elle-même (ton très impératif, capitales, interdits répétés), que le
détecteur d'Azure semble prendre pour une tentative de détournement ; critères et copie n'y contribuent qu'un peu.
Hypothèse non testée. Les consignes du bot et des bancs du jugement n'ont jamais été refusées ([journal: 530 lignes de
bancs, 30 passages du bot relus]). Règle pratique : toute NOUVELLE consigne passe d'abord par la sonde avant usage ;
décision de l'auteur (2026-11-18, 19 h 40) : rien ne change côté Metaculus avant le tournoi.

## Suite
Pas d'ancrage dans le bot. Le contrôle de citation reste utile comme garde-fou contre les fuites de date (un fait
cité doit figurer dans la recherche datée).
