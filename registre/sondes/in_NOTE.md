# bne IntelliNews, sonde du 2026-11-25

robots.txt (in_robots.txt) : « Disallow: /feed » pour tous les robots. Le flux /feed/ a pourtant été lu par la sonde :
l'analyseur robots de Python, sur le runner, oubliait les refus de ce fichier (lignes vides à l'intérieur du groupe,
« Disallow: » vide). Erreur de notre côté, corrigée dans politesse.py le même soir (test tests/test_politesse_robots.py).
Le contenu lu (début du flux, d'une page d'article et d'une page Feedly) a été supprimé du registre ; seul etat.json garde
les statuts. Conclusion : pas de flux de titres IntelliNews dans la veille (refus explicite du site).
