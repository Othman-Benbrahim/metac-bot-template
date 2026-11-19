# Kuran — Private Truths, Public Lies

## Référence
Timur Kuran, *Private Truths, Public Lies: The Social Consequences of Preference Falsification*, Harvard University
Press, 1995 ; édition de poche 1997. Lu en epub (envoyé par l'auteur le 2026-11-19), 19 chapitres en quatre parties
(vivre dans le mensonge, freiner le changement, déformer la connaissance, produire la surprise). Mémo dans nos mots.

## Thèse en trois phrases
Les gens disent souvent autre chose que ce qu'ils pensent, pour leur réputation ou leur sécurité : c'est la
falsification des préférences, et elle rend l'opinion publique trompeuse sur l'opinion privée. Comme chacun ne parle
qu'au-delà de son propre seuil (qui dépend du nombre de ceux qui parlent déjà) et que ces seuils sont cachés, un
régime ou une norme peuvent tenir longtemps malgré un rejet privé massif, puis s'effondrer d'un coup sur un incident
mineur, à la surprise de tous, y compris des acteurs. À long terme, la falsification appauvrit le discours public et
finit par façonner les croyances privées elles-mêmes (falsification de la connaissance), ce qui fige les sociétés.

## Mécanismes retenus
Format : phrase · niveau · relation (fiche `humain`) ou code · paramètres · trace.

1. **Écart privé-public.** On dit ce qui est attendu ; le coût de la vérité vient de la sanction politique et sociale.
   · psychologique · compartiment falsification ; hierarchie → falsification (±), conventions → falsification (+),
   pont entrant information-cyber:censure → falsification · — · censure mesurée (OONI, `ooni:RU`), moteur de l'écart.
2. **Seuils politiques distribués et cascades.** Chacun parle quand assez d'autres ont parlé ; une petite variation
   des seuils ou un incident mineur déclenche une cascade. · societe · opinion_privee → opinion_publique (+, masse
   critique), opinion_publique → opinion_publique (+, masse critique) · `mu`, `sigma` · prises de position publiques
   datées (à brancher).
3. **La surprise.** L'écart se referme d'un coup quand beaucoup parlent : révolutions imprévues (Europe de l'Est 1989,
   Iran 1979). · psychologique, societe · opinion_publique → falsification (−, forte) ; `Carte.marges_de_bascule` :
   pour chaque relation à seuil ou à masse critique, seuil effectif d'aujourd'hui moins intensité observée — les
   « poudrières » d'abord · — · toutes les traces branchées ; ligne de commande `--bascules`.
4. **Mécontentement muet.** La précarité nourrit un mécontentement privé qui ne se voit pas tant que dire coûte. ·
   psychologique · stress_chronique → opinion_privee (+) · — · trace fermée par définition.
5. **Falsification de la connaissance et conservatisme collectif.** Un discours sans contradiction façonne les
   croyances des générations suivantes ; l'impensable devient impensé. · psychologique · falsification →
   opinion_privee (−, décennie, hystérésis) · — · —
6. **De l'opinion à la rue.** Une opinion publique qui bascule se traduit en actes. · societe · opinion_publique →
   passage_acte (+) · retard · manifestations GDELT.
7. **Les sondages mentent sous contrainte.** Dans un régime répressif ou sous une norme forte, sondages et déclarations
   sous-estiment la dissidence. · convention, technique · pont falsification → observateur-mesure:biais · — · à garder
   en tête pour toute question qui s'appuie sur un sondage dans un pays où dire coûte.

## Ce qui a été écrit dans le programme (bot 0.10.327)
- `ecosystemes/humain.yaml` : compartiments opinion_privee, falsification, opinion_publique ; 9 relations ; 2 ponts
  sortants ; 1 pont entrant (information-cyber).
- `carte.py` : `marges_de_bascule` ; les comptes à rebours ne comptent plus comme intensités (liste partagée avec
  `calibrer.py`).
- Tests : cascade (un mécontentement modéré reste muet, un fort fait basculer l'opinion publique et effondre l'écart),
  ordre des marges.

## Limites et critiques connues
- L'opinion privée est inobservable par construction : la théorie explique très bien après coup, prédit mal le moment
  exact ; Kuran le revendique (on peut dire qu'une société est fragile, pas quand elle basculera). La carte suit la
  même modestie : marges et simulations disent la fragilité, pas la date.
- Les études de cas (castes, discrimination positive aux États-Unis) mêlent analyse et position personnelle de
  l'auteur et ont été discutées ; nous n'en retenons que les mécanismes.
- Les seuils sont supposés stables pendant la cascade ; en réalité la répression peut répondre et les relever.
