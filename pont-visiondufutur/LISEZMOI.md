# Pont GDELT sur visiondufutur.com (alwaysdata)

1. Déposer `gdelt.php` sur le site, par exemple dans `/pont/gdelt.php` (adresse : https://visiondufutur.com/pont/gdelt.php).
2. À côté, créer `pont-cle.php` contenant une longue clé aléatoire (au moins 24 caractères) :
   `<?php return 'remplacer-par-une-longue-cle-aleatoire';`
   Ne jamais coller cette clé dans une conversation ; seulement dans ce fichier et dans GitHub.
3. Dans GitHub (Settings → Secrets and variables → Actions) :
   - variable `GDELT_PONT` = l'adresse complète de gdelt.php ;
   - secret `GDELT_PONT_CLE` = la même clé.
4. Lancer « Sonde GDELT (questions sans recherche) » : elle passera par le pont.

Le pont n'accepte que la clé, ne transmet que les paramètres de recherche d'articles de GDELT, espace les requêtes de
5,5 secondes, garde un cache (une recherche passée ne change plus) et renvoie les refus de GDELT tels quels.
Pour vérifier qu'il répond : sans la clé, l'adresse doit renvoyer {"erreur":"clé absente ou invalide"}.
