# L-GPT — Assistant IA local pour Windows

## Ce que fait cette version
- Interface sombre premium bleu nuit / violet, inspirée d'une conversation ChatGPT.
- Réponses affichées directement dans le fil, sur toute la largeur disponible : pas de petite boîte de réponse ni de barre de défilement indépendante.
- Import de plusieurs PDF en une fois et questions sur l'ensemble des documents.
- Affichage du nom du PDF et du numéro de page dans les sources.
- Bouton **Créer un résumé PDF** : l'IA analyse les documents importés, construit une synthèse organisée et l'enregistre dans un PDF que tu choisis.
- Traitement local avec Ollama. Les PDF et leurs index restent sur ton ordinateur.

## Installation (à faire une seule fois)
1. Extrais **tout** le ZIP dans un dossier normal, par exemple `Documents\L-GPT`. Ne lance pas les fichiers depuis l'aperçu du ZIP.
2. Vérifie que Python (3.11 ou plus récent) et Ollama sont installés.
3. Double-clique sur `INSTALLER.bat`. Une fenêtre reste ouverte pendant l'installation et affiche les erreurs éventuelles. Attends le message de réussite.
4. Vérifie que les modèles sont présents dans Ollama. D'après ta configuration actuelle, tu as notamment `nomic-embed-text:latest`, `qwen3.8:27b`, `qwen3.5:9b` et `qwen3.5:4b`.
5. Double-clique sur `L-GPT.bat`.

## Utilisation
1. Démarre Ollama.
2. Lance L-GPT avec `L-GPT.bat`.
3. Clique sur **Importer des PDF** et sélectionne un ou plusieurs cours.
4. Attends que l'indexation soit terminée. Tu peux ensuite poser tes questions dans la zone du bas ; Entrée envoie et Maj+Entrée ajoute une ligne.
5. Pour obtenir une synthèse, clique sur **Créer un résumé PDF**, choisis où enregistrer le fichier et attends la fin de l'analyse.

Les index sont mis en cache à côté des PDF (`.rag.json`) afin d'éviter de recalculer les embeddings à chaque lancement. Les PDF scannés sans couche de texte nécessitent un OCR et ne sont pas pris en charge dans cette version.

## Créer une application `.exe`
Lance `BUILD_EXE.bat` après l'installation. Le résultat est dans `dist\L-GPT\L-GPT.exe`. Il faut conserver tout le dossier `dist\L-GPT`, pas seulement le fichier EXE. Ollama et ses modèles restent des prérequis externes.

## En cas de problème
- Si `L-GPT.bat` détecte un environnement ou une dépendance manquante, il affiche une erreur et garde la fenêtre ouverte.
- Les erreurs Python au démarrage de l'interface sont consignées dans `L-GPT_erreurs.log`.
- Pour réinstaller les dépendances, relance `INSTALLER.bat`.

## Mémoire / erreur de démarrage du serveur IA
Cette version utilise `num_ctx=2048` pour les questions et la génération des résumés, afin de réduire la mémoire réservée au cache KV. Si un modèle 27B échoue encore au chargement, ferme les applications lourdes et choisis `qwen3.5:9b` ou `qwen3.5:4b` dans la liste des modèles. La mémoire nécessaire dépend du modèle, de sa quantification et du partage RAM/graphique.

## Historique des conversations
Le bouton « Nouvelle conversation » archive l'échange actuel dans la liste « Récent » et réinitialise le fil. Les conversations sont conservées pendant la session de l'application ; elles ne sont pas encore enregistrées après fermeture.

## Formules dans les PDF générés
Les consignes de génération interdisent le LaTeX. Les formules doivent être écrites en notation texte lisible (par exemple `(a)/(b)`, `x^2`, `×`, `√(...)`). Le moteur nettoie également plusieurs commandes LaTeX fréquentes avant la mise en page du PDF.
