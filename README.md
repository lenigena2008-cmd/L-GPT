# L-GPT 3.0 — Assistant IA local multiplateforme (base Windows + macOS)

L-GPT est un assistant de bureau local dont la mission principale est de lire, comprendre, expliquer et synthétiser des cours PDF. Il peut également répondre à des questions générales, avec ou sans document.

L'application est écrite en Python et PySide6, utilise Ollama pour les modèles locaux et SQLite pour conserver les conversations, les paramètres et les mémoires. Aucun compte cloud n'est nécessaire pour l'utilisation locale.

> **État de la version 3.0 :** Windows reste la plateforme de référence. Cette version prépare et ajoute les scripts ainsi qu'une compilation macOS automatisée par GitHub Actions. Le code et le workflow macOS sont vérifiés statiquement dans cet environnement, mais le lancement sur un vrai Mac, la signature Apple et la notarisation ne sont pas certifiés ici. Ne présente pas encore le binaire macOS comme une version officiellement testée.

## Nouveautés de la 3.0

- **Fondation multiplateforme :** chemins de données adaptés à Windows, macOS et Linux. Le chemin Windows historique est conservé pour retrouver les bases des versions précédentes.
- **Préparation macOS pour puce apple silicon (M1, M2, M3, M4, M5):** scripts `INSTALLER.sh`, `L-GPT.command` et `BUILD_MACOS.sh`. 
- **Compilation macOS sur GitHub :** workflow `.github/workflows/build-macos.yml` qui utilise un runner macOS fourni par GitHub pour construire et publier un artefact `.app` compressé. Aucun Mac personnel n'est requis pour lancer cette compilation distante.
- **Ressources d'application :** résolution des fichiers compatible avec le mode Python et PyInstaller.
- **Version et documentation :** version 3.0, README actualisé et instructions de publication GitHub.
- **Fonctions conservées :** chat, historique, import et indexation PDF, synthèses PDF, modes Document/Connaissances/Intelligent, mémoire contextuelle lexicale, paramètres Ollama et sélection des modèles.

## Les trois modes

- **Intelligent (par défaut)** : choisit entre les documents et les connaissances générales en fonction de la question et des passages retrouvés. Fonctionne sans PDF.
- **Document** : répond uniquement à partir des PDF indexés. Si aucun passage pertinent n'est disponible, L-GPT le signale.
- **Connaissances** : répond à partir du modèle, sans utiliser les PDF.

Les réponses indiquent leur provenance : Documents, Connaissances ou Documents + connaissances. Les mémoires sont un contexte auxiliaire, pas une preuve documentaire ; elles ne sont pas injectées en mode Document.

## Mémoire et continuité

Les conversations, paramètres et mémoires sont stockés dans `conversations.db`. L-GPT recherche les souvenirs pertinents par recouvrement lexical des mots de la question avec les titres et contenus des mémoires. Jusqu'à cinq souvenirs peuvent être ajoutés au contexte dans les modes qui l'autorisent. Cette recherche n'est pas encore une recherche sémantique : elle peut manquer des synonymes ou des formulations différentes.

L'utilisateur conserve le contrôle de la création, de la modification et de la suppression des mémoires. Les fichiers PDF restent à leur emplacement d'origine ; la base conserve leurs chemins, pas une copie des fichiers.

## Modèles Ollama

L-GPT interroge Ollama pour lister les modèles installés, afficher les métadonnées communiquées par Ollama et consulter ponctuellement les modèles chargés (`ollama ps`). Le choix manuel et le routage automatique heuristique sont disponibles avec les profils Performance, Équilibré et Qualité.

Commandes utiles :

```bash
ollama list
ollama show qwen3.5:9b
ollama ps
ollama pull qwen3.5:9b
ollama pull nomic-embed-text
```

`nomic-embed-text` est utilisé pour les embeddings PDF. Ollama doit être installé et démarré séparément de L-GPT sur chaque machine. Les modèles doivent également être téléchargés sur chaque machine ; ils ne sont pas inclus dans le dépôt ni dans l'application compilée.

Les paramètres `num_ctx` et `num_predict` sont transmis aux requêtes. La préférence de cache KV reste informative dans cette version : L-GPT ne modifie pas automatiquement les variables d'environnement du serveur Ollama. Les performances dépendent du modèle, de la quantification, du contexte, du backend et du matériel.

## Prérequis

### Windows

- Windows 10 ou 11.
- Python 3.11 ou plus récent.
- Ollama installé et démarré.

### macOS (préparation expérimentale)

- macOS 14 ou plus récent recommandé pour le workflow fourni.
- Python 3.11 ou plus récent pour lancer depuis les sources.
- Ollama installé pour macOS, démarré localement.
- Pour une application compilée : récupérer l'artefact `L-GPT-macOS` produit par GitHub Actions. L'artefact n'est pas signé/notarisé par Apple dans ce projet.

Le binaire macOS doit être généré sur macOS. PyInstaller ne produit pas un véritable bundle macOS depuis Windows ; c'est précisément pourquoi le workflow GitHub utilise un runner macOS.

### Linux

Le code utilise le répertoire XDG pour les données et peut être lancé depuis les sources avec Python 3.11+, mais aucune procédure de paquet Linux n'est fournie dans cette version.

## Installation sous Windows

1. Extraire le ZIP dans un dossier accessible en écriture.
2. Installer Ollama depuis son site officiel : https://ollama.com/.
3. Double-cliquer sur `INSTALLER.bat`.
4. Télécharger au moins un modèle conversationnel et `nomic-embed-text` depuis PowerShell :

   ```powershell
   ollama pull qwen3.5:9b
   ollama pull nomic-embed-text
   ```
5. Lancer `L-GPT.bat`.

## Installation macOS depuis les sources

1. Installer Python 3.11+ et Ollama pour macOS.
2. Extraire le dépôt ou l'archive dans un dossier utilisateur.
3. Ouvrir Terminal et entrer dans le dossier `L-GPT`.
4. Autoriser les scripts puis installer :

   ```bash
   chmod +x INSTALLER.sh L-GPT.command BUILD_MACOS.sh
   ./INSTALLER.sh
   ```
5. Télécharger les modèles :

   ```bash
   ollama pull qwen3.5:9b
   ollama pull nomic-embed-text
   ```
6. Lancer avec `./L-GPT.command`.

Pour construire localement le bundle depuis un Mac : `./BUILD_MACOS.sh`. Le résultat se trouve dans `dist/`. Si macOS bloque un fichier téléchargé, vérifie sa provenance et les réglages de sécurité avant d'autoriser son ouverture ; ne désactive pas globalement Gatekeeper.

## Publier et obtenir la version macOS sur GitHub sans posséder de Mac

Tu peux conserver **un seul dépôt GitHub** pour le code Windows et macOS. Il n'est pas nécessaire de créer un dépôt séparé.

1. Ouvre ton dépôt GitHub et ajoute les nouveaux fichiers de cette version en conservant les dossiers : `INSTALLER.sh`, `L-GPT.command`, `BUILD_MACOS.sh` et `.github/workflows/build-macos.yml`.
2. Fais un commit sur la branche principale, puis pousse-le sur GitHub.
3. Dans ton dépôt, ouvre l'onglet **Actions** et sélectionne **Build macOS app**.
4. Clique sur **Run workflow** puis confirme. Le runner macOS de GitHub installe Python et les dépendances, puis construit `L-GPT.app`.
5. À la fin, ouvre l'exécution réussie et télécharge l'artefact **L-GPT-macOS** dans la section **Artifacts**.
6. Pour le rendre accessible aux utilisateurs, crée une **Release** GitHub, par exemple `v3.0.0`, et joins `L-GPT-macOS.zip` ainsi que l'archive source Windows. Tu peux aussi déclencher le workflow en poussant un tag commençant par `v`.

**Important :** les artefacts Actions sont des téléchargements de build, pas automatiquement une Release publique. Pour une distribution simple, joins le ZIP macOS à une Release. Les utilisateurs Mac devront installer Ollama et télécharger leurs propres modèles. Le ZIP macOS fourni par ce workflow est non signé et non notarisé : macOS peut afficher un avertissement. Une distribution publique plus fluide nécessitera ensuite un certificat Developer ID et la notarisation Apple, qui demandent un compte développeur et des secrets GitHub configurés.

Documentation officielle utile :
- GitHub Actions : https://docs.github.com/actions
- GitHub Releases : https://docs.github.com/repositories/releasing-projects-on-github
- PyInstaller : https://pyinstaller.org/
- Ollama : https://ollama.com/

## Emplacement des données

- **Windows :** `%APPDATA%\L-GPT\conversations.db` (chemin historique conservé).
- **macOS :** `~/Library/Application Support/L-GPT/conversations.db`.
- **Linux :** `$XDG_DATA_HOME/L-GPT/conversations.db`, ou `~/.local/share/L-GPT/conversations.db` si la variable n'existe pas.

Les données ne sont pas stockées dans le dossier du programme : remplacer l'application ne doit donc pas effacer les conversations. Fais régulièrement une sauvegarde de `conversations.db` et des PDF d'origine. Si tu migres de Windows vers Mac, copie la base SQLite vers le dossier macOS indiqué ; les chemins des PDF Windows ne seront toutefois pas valides sur Mac et devront être réimportés depuis leur nouvel emplacement.

## Création de l'exécutable Windows

Après installation des dépendances, lance `BUILD_EXE.bat`. PyInstaller crée `dist\L-GPT`. Conserve tout le dossier `dist\L-GPT`, pas uniquement `L-GPT.exe`. Ollama et les modèles restent à installer séparément.

## Dépannage

- **Ollama inaccessible :** vérifie qu'Ollama est démarré et que `ollama list` fonctionne dans le terminal.
- **Aucun modèle :** lance `ollama pull nom-du-modele`, puis actualise la liste dans L-GPT.
- **Mémoire insuffisante ou génération lente :** choisis un modèle plus léger, le profil Performance et un contexte 8K ou 16K.
- **PDF sans texte :** l'OCR des PDF scannés n'est pas inclus ; le document doit contenir du texte sélectionnable.
- **macOS ne lance pas le script :** dans Terminal, vérifie que tu es dans le dossier du projet et lance `chmod +x INSTALLER.sh L-GPT.command`.
- **Échec du build GitHub :** ouvre l'exécution dans Actions et consulte la première étape rouge et ses journaux. Les dépendances natives peuvent évoluer ; le workflow doit être maintenu.

## Structure du projet

```text
L-GPT/
├── main.py
├── core/pdf_engine.py
├── assets/
├── requirements.txt
├── INSTALLER.bat
├── L-GPT.bat
├── BUILD_EXE.bat
├── INSTALLER.sh
├── L-GPT.command
├── BUILD_MACOS.sh
└── .github/workflows/build-macos.yml
```

## Limites connues

- Le workflow macOS est fourni mais doit encore être exécuté et validé sur GitHub avant d'annoncer une version Mac testée.
- Le bundle macOS n'est pas signé ni notarisé.
- La recherche mémoire est lexicale, pas sémantique.
- La création automatique de souvenirs n'est pas activée.
- Les mesures de vitesse restent approximatives ; le tableau de bord matériel continu n'est pas disponible.
- Le cache KV est une préférence informative et n'est pas modifié par L-GPT.
- L'OCR des PDF scannés n'est pas inclus.
- L'application mobile native n'est pas développée. Une future version mobile pourra se connecter à un serveur L-GPT/Ollama sécurisé sur le réseau local.

## Feuille de route

- Validation réelle du bundle macOS sur les versions Intel et Apple Silicon.
- Signature Developer ID et notarisation Apple pour une distribution simplifiée.
- Recherche sémantique de mémoire et propositions de souvenirs avec validation.
- Mesures natives d'inférence et supervision matérielle selon les API disponibles.
- API locale sécurisée pour une future application mobile.
