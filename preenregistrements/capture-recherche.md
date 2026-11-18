# Préenregistrement : capture en direct de ce que lit le bot
2026-11-18, bot 0.10.296.

Décision d'auteur du 2026-11-18, 22 h 04 (« j'accepte les deux, à appliquer »). Origine : ForecastGym (arXiv
2611.23045). Seule une recherche gelée PENDANT que la question est ouverte est sans fuite par construction.

## Ce qui est fait
- À chaque passage du bot, après la recherche générale (celle que lisent A et M), le texte est gelé tel quel :
  fichier dans le cache de GitHub Actions (cache/recherche-tournoi), jamais dans le dépôt (les articles ne sont pas
  à nous). Le dépôt reçoit les métadonnées : registre/capture-tournoi.jsonl (question, horodatage, échéance, moteur,
  adresses et dates des sources, empreinte, longueur, nom du fichier).
- RIEN ne change dans ce que le bot poste : la capture n'intervient qu'après la recherche, ne modifie pas le texte et
  ne lève jamais d'erreur (décision du 2026-11-18, 19 h 40 : rien ne change côté Metaculus avant le tournoi).

## Usage prévu
Une fois les questions résolues : rejouer les variantes (avocat du OUI, tendance GDELT, abstention, cartes…) sur ces
recherches gelées, sans fuite, et comparer à ce qui a été posté.

## Limites connues
Le cache de GitHub Actions n'est pas un stockage durable (10 Go par dépôt, entrées non lues depuis 7 jours effacées) ;
il est relu à chaque passage du bot. Un archivage plus sûr (ailleurs que dans le dépôt public) reste à décider.
