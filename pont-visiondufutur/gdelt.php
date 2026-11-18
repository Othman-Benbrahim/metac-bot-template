<?php
/*
 * Pont GDELT pour le bot de l'alphabet situationnel (bot 0.10.272), à déposer sur visiondufutur.com.
 *
 * Décision d'auteur du 2026-11-18, 15 h 21 : passer par le site pour les requêtes GDELT, refusées en 429 depuis les
 * adresses partagées des serveurs de GitHub. Ce n'est PAS un contournement : un seul client dédié, qui respecte la
 * règle publique de GDELT (une requête toutes les 5 secondes au plus), garde un cache et s'identifie. Si GDELT
 * refuse aussi cette adresse, on s'arrête là (pas de rotation d'adresses).
 *
 * Sécurité : ce n'est PAS un relais ouvert. Il faut la clé partagée (en-tête X-Pont-Cle, comparée en temps constant),
 * seuls les paramètres de l'API DOC 2.0 de GDELT en mode liste d'articles sont transmis, et rien d'autre.
 *
 * Installation : copier ce fichier, et un fichier pont-cle.php À CÔTÉ (hors de la racine web si possible) contenant
 *   <?php return 'une-longue-cle-aleatoire';
 * puis mettre l'adresse de ce fichier dans la variable GitHub GDELT_PONT et la même clé dans le secret GDELT_PONT_CLE.
 */
declare(strict_types=1);
header('Content-Type: application/json; charset=utf-8');

$cle_attendue = @include __DIR__ . '/pont-cle.php';
$cle_recue = $_SERVER['HTTP_X_PONT_CLE'] ?? '';
if (!is_string($cle_attendue) || strlen($cle_attendue) < 24 || !hash_equals($cle_attendue, $cle_recue)) {
    http_response_code(403);
    echo json_encode(['erreur' => 'clé absente ou invalide']);
    exit;
}

// Paramètres admis : ceux de l'API DOC 2.0, mode liste d'articles, rien d'autre.
$q = trim((string)($_GET['query'] ?? ''));
$debut = (string)($_GET['startdatetime'] ?? '');
$fin = (string)($_GET['enddatetime'] ?? '');
$max = min(15, max(1, (int)($_GET['maxrecords'] ?? 15)));
if ($q === '' || strlen($q) > 300 || ($debut !== '' && !preg_match('/^\d{14}$/', $debut))
    || ($fin !== '' && !preg_match('/^\d{14}$/', $fin))) {
    http_response_code(400);
    echo json_encode(['erreur' => 'paramètres refusés']);
    exit;
}
$params = ['query' => $q, 'mode' => 'artlist', 'format' => 'json', 'maxrecords' => $max, 'sort' => 'datedesc'];
if ($debut !== '') { $params['startdatetime'] = $debut; }
if ($fin !== '') { $params['enddatetime'] = $fin; }

// Cache : une recherche dont la fenêtre est passée ne change plus ; sinon 6 heures.
$dossier = sys_get_temp_dir() . '/pont-gdelt';
@mkdir($dossier, 0700, true);
$fichier = $dossier . '/' . sha1(json_encode($params)) . '.json';
$passee = $fin !== '' && $fin < gmdate('YmdHis', time() - 86400);
if (is_file($fichier) && ($passee || time() - filemtime($fichier) < 6 * 3600)) {
    header('X-Pont-Cache: oui');
    readfile($fichier);
    exit;
}

// Espacement : 5,5 secondes entre deux requêtes vers GDELT, pour tout le site (verrou de fichier).
$verrou = fopen($dossier . '/verrou', 'c+');
flock($verrou, LOCK_EX);
$derniere = (float)stream_get_contents($verrou);
$attente = 5.5 - (microtime(true) - $derniere);
if ($attente > 0) { usleep((int)($attente * 1e6)); }

$url = 'https://api.gdeltproject.org/api/v2/doc/doc?' . http_build_query($params);
$ctx = stream_context_create(['http' => ['timeout' => 40, 'ignore_errors' => true,
    'header' => "User-Agent: alphabet-situationnel/1.0 (recherche non commerciale ; visiondufutur.com)\r\n"]]);
$corps = @file_get_contents($url, false, $ctx);
$statut = 0;
foreach ($http_response_header ?? [] as $h) {
    if (preg_match('#^HTTP/\S+\s+(\d{3})#', $h, $m)) { $statut = (int)$m[1]; }
}
ftruncate($verrou, 0);
rewind($verrou);
fwrite($verrou, (string)microtime(true));
flock($verrou, LOCK_UN);
fclose($verrou);

if ($corps === false || $statut === 0) {
    http_response_code(502);
    echo json_encode(['erreur' => 'GDELT injoignable depuis le site']);
    exit;
}
if ($statut !== 200) {
    http_response_code($statut);            // 429 compris : le bot le verra tel quel
    echo json_encode(['erreur' => 'GDELT a répondu ' . $statut, 'texte' => mb_substr(trim($corps), 0, 200)]);
    exit;
}
$json = json_decode($corps, true);
if (!is_array($json)) {
    // GDELT répond parfois en texte (requête refusée, « limit requests ») : renvoyé tel quel au bot
    http_response_code(200);
    header('X-Pont-Texte: oui');
    echo json_encode(['texte_gdelt' => mb_substr(trim($corps), 0, 300)]);
    exit;
}
file_put_contents($fichier, $corps, LOCK_EX);
header('X-Pont-Cache: non');
echo $corps;
