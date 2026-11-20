# L-GPT 2.9 — Assistant IA local, mémoire contextuelle et contrôle Ollama

L-GPT est un assistant de bureau local pour Windows. Sa mission principale est de lire, comprendre, expliquer et synthétiser des cours au format PDF. Il peut aussi répondre aux questions générales, sans document.

L'application utilise **Ollama** pour exécuter les modèles sur la machine et **SQLite** pour conserver les conversations, les paramètres et les mémoires. Aucun compte cloud n'est requis.

## Nouveautés de la version 2.9

- **Mémoire contextuelle automatique** : L-GPT recherche les mémoires qui semblent pertinentes pour la question et n'injecte qu'une petite sélection dans le contexte du modèle. Il ne transmet pas toute la base de mémoire à chaque requête.
- **Séparation des sources** : les souvenirs sont un contexte auxiliaire, jamais une preuve issue d'un PDF. Le mode Document reste strictement limité aux passages des documents.
- **Contexte Ollama appliqué** : le réglage `num_ctx` choisi dans les paramètres est maintenant transmis aux requêtes de conversation.
- **Limite de génération appliquée** : réglage `num_predict` (nombre maximal de tokens générés) disponible dans les paramètres.
- **État des modèles chargés** : consultation ponctuelle des informations renvoyées par `ollama ps` dans l'onglet IA et modèles.
- **Statistiques de réponse** : affichage du temps total et d'une estimation de tokens/s calculée à partir du texte produit. Ce chiffre est indicatif, pas une mesure native exacte du moteur.
- README et procédures d'installation mis à jour.

## Les trois modes de réponse

- **Intelligent (par défaut)** : choisit entre les documents et les connaissances générales en fonction de la question et des passages retrouvés. Fonctionne même sans PDF.
- **Document** : répond uniquement à partir des PDF indexés. Si aucun document pertinent n'est disponible, L-GPT le signale.
- **Connaissances** : répond à partir du modèle, sans utiliser les PDF.

Les réponses indiquent la provenance choisie : Documents, Connaissances ou Documents + connaissances. En mode Intelligent, une courte explication de la décision est ajoutée. Les passages documentaires cités indiquent le fichier et la page lorsque ces informations sont disponibles.

## Gestion des modèles Ollama

Le menu **Paramètres IA et mémoire → IA et modèles** interroge Ollama pour afficher les modèles locaux. L'application tente de récupérer leur taille et leurs métadonnées, notamment la quantification. Elle consulte également `ollama.ps()` pour afficher un instantané des modèles chargés lorsque l'API fournit ces données.

Commandes utiles dans PowerShell :

```powershell
ollama list
ollama show qwen3.5:9b
ollama ps
```

Pour télécharger un modèle :

```powershell
ollama pull qwen3.5:9b
ollama pull nomic-embed-text
```

`nomic-embed-text` sert à créer les embeddings pour la recherche dans les PDF ; il ne remplace pas un modèle conversationnel.

### Quantification

Les formats peuvent appartenir à plusieurs familles : K-quants (Q2_K à Q8_0 et variantes), I-quants (IQ1 à IQ4 et variantes), formats non quantifiés (F16, BF16, F32) et formats compacts ou spécialisés (TQ, MXFP4, NVFP4, FP8, INT8, etc.). Cette liste est un aide-mémoire, **pas une garantie de prise en charge**. L-GPT affiche la quantification communiquée par les métadonnées Ollama. Il ne convertit pas les modèles et ne modifie pas leurs fichiers.

### Routage et profils

Le choix manuel reste disponible. Le routage automatique choisit parmi les modèles installés selon le profil et une estimation heuristique de la tâche :

- **Performance** : favorise les modèles légers.
- **Équilibré** : compromis entre rapidité et capacité.
- **Qualité** : favorise les modèles plus puissants lorsqu'ils sont installés.

Cette logique ne constitue pas un benchmark et ne mesure pas la qualité réelle d'un modèle. Les performances dépendent du modèle, de sa quantification, du contexte, d'Ollama et du matériel.

## Contexte, génération et cache KV

Dans **Paramètres IA et mémoire → IA et modèles** :

- `num_ctx` : 8 192, 16 384, 32 768 ou 65 536 tokens. La valeur choisie est transmise aux requêtes de conversation via l'option Ollama `num_ctx`.
- `num_predict` : limite maximale de sortie configurable entre 512 et 8 192 tokens. La valeur est transmise via `num_predict`.
- Cache KV : f16, q8_0 ou q4_0. Dans cette version, ce choix reste une **préférence informative** ; Ollama configure le type de cache au niveau du serveur, notamment via `OLLAMA_KV_CACHE_TYPE`, et non dans chaque requête. L-GPT ne modifie pas automatiquement les variables d'environnement du système.

Une fenêtre de contexte élevée augmente potentiellement la mémoire nécessaire. Commence avec 8K ou 16K si la machine manque de mémoire. Le modèle peut aussi imposer ses propres limites.

## Mémoire et continuité

L'onglet **Mémoire** permet d'ajouter, modifier et supprimer des mémoires générales ou liées à un projet. Ces données sont stockées localement dans SQLite.

À chaque question, L-GPT compare les mots de la question aux titres et contenus des mémoires. Il sélectionne au maximum cinq éléments pertinents, avec une limite de taille, puis les transmet au modèle comme contexte auxiliaire. La recherche est lexicale et légère : elle ne comprend pas parfaitement les synonymes et peut manquer un souvenir formulé autrement. Si aucun souvenir ne correspond, aucun souvenir n'est ajouté.

Les mémoires ne sont pas des sources documentaires. En mode **Document**, elles ne sont pas injectées dans la réponse. En mode **Connaissances** et **Documents + connaissances**, elles peuvent aider à maintenir le contexte d'un projet ou d'une préférence, sans remplacer les informations du PDF.

La mémoire n'apprend pas automatiquement de chaque phrase et ne crée pas encore de nouveaux souvenirs toute seule : l'utilisateur garde le contrôle de leur création, modification et suppression.

Les conversations sont restaurées depuis la base locale. Les chemins des PDF associés sont conservés dans l'historique ; les fichiers eux-mêmes restent à leur emplacement d'origine.

## Statistiques et informations matérielles

Après une réponse, L-GPT affiche le temps total et une estimation de tokens/s dérivée de la longueur du texte (approximation d'environ quatre caractères par token). Ce n'est pas la mesure exacte fournie par le moteur d'inférence.

L'onglet IA et modèles affiche un instantané des modèles actuellement chargés via `ollama ps`. Les champs disponibles varient selon la version d'Ollama. Cette version ne fournit pas encore un tableau de bord continu de l'utilisation CPU, RAM système et GPU ; elle n'invente pas les valeurs qui ne sont pas exposées.

## Installation sous Windows

### Prérequis

- Windows 10 ou 11.
- Python 3.11 ou plus récent, avec l'option **Add Python to PATH** activée.
- Ollama installé et démarré : [site officiel Ollama](https://ollama.com/).
- Une connexion Internet est nécessaire pour installer les dépendances Python et télécharger les modèles ; l'utilisation quotidienne peut ensuite se faire localement.

### Étapes

1. Extraire entièrement l'archive ZIP dans un dossier accessible en écriture.
2. Installer Ollama et vérifier qu'il fonctionne.
3. Double-cliquer sur `INSTALLER.bat`. Le script crée un environnement virtuel `.venv` et installe les dépendances.
4. Dans PowerShell, télécharger au moins un modèle conversationnel et le modèle d'embedding :

   ```powershell
   ollama pull qwen3.5:9b
   ollama pull nomic-embed-text
   ```

5. Lancer `L-GPT.bat`.

## Utilisation

- Pose directement une question générale, même sans PDF.
- Utilise **Importer des PDF** pour sélectionner un ou plusieurs cours. Attends la fin de l'indexation avant de poser une question sur leur contenu.
- Choisis le mode Intelligent, Document ou Connaissances.
- Choisis manuellement le modèle ou active le routage automatique dans les paramètres.
- Ajuste `num_ctx` et `num_predict` selon les capacités de la machine.
- Ajoute et corrige les souvenirs dans l'onglet Mémoire ; les plus pertinents sont ensuite retrouvés automatiquement.
- Utilise **Créer un résumé PDF** pour générer une synthèse des documents importés.

## Création de l'exécutable

Après installation des dépendances, lance `BUILD_EXE.bat`. PyInstaller crée un dossier `dist\L-GPT`.

Conserve **tout le dossier** `dist\L-GPT` : ne déplace pas uniquement `L-GPT.exe`. Ollama doit rester installé séparément et les modèles doivent être présents sur la machine qui exécute l'application.

## Données locales et confidentialité

La base de données est enregistrée dans :

```text
%APPDATA%\L-GPT\conversations.db
```

Elle contient les conversations, les paramètres et les mémoires. Les mises à jour ne nécessitent pas la suppression de ce fichier. La version 2.9 conserve les tables existantes et utilise les tables de mémoire et de paramètres ajoutées dans la version précédente.

Les PDF ne sont pas copiés dans la base : leurs chemins sont mémorisés et les fichiers restent à leur emplacement d'origine. Pense à sauvegarder séparément la base et tes documents importants.

## Dépannage

**L-GPT indique qu'Ollama est inaccessible**

- Vérifie qu'Ollama est installé et démarré.
- Dans PowerShell, exécute `ollama list`.
- Si la commande échoue, redémarre Ollama puis relance L-GPT.

**Aucun modèle n'apparaît**

- Télécharge un modèle avec `ollama pull nom-du-modele`.
- Clique sur le bouton ↻ à côté de la liste des modèles.

**Erreur de mémoire ou génération trop lente**

- Essaie un modèle plus petit ou le profil Performance.
- Réduis `num_ctx` à 8 192 ou 16 384 et limite `num_predict`.
- Ferme les applications lourdes et vérifie `ollama ps`.

**Le cache KV sélectionné ne semble pas changer la mémoire utilisée**

- Le choix f16/q8_0/q4_0 est informatif dans l'interface. Ollama configure le cache au niveau du serveur. Pour le modifier, consulte la documentation de ta version d'Ollama et configure explicitement son environnement avant de démarrer le serveur. L-GPT ne change pas cette configuration automatiquement.

**L'indexation PDF échoue ou ne trouve aucun texte**

- Vérifie que le PDF est lisible et non protégé.
- Le moteur extrait le texte intégré au PDF. L'OCR des documents scannés n'est pas inclus.
- Vérifie que `nomic-embed-text` est installé et qu'Ollama fonctionne.

**Le lancement échoue**

- Relance `INSTALLER.bat`.
- Vérifie que Python 3.11+ est accessible.
- Consulte `L-GPT_erreurs.log` dans le dossier de l'application si un journal a été créé.

## Structure du projet

```text
L-GPT/
├── main.py                 # Interface PySide6, conversations, paramètres et mémoire
├── core/
│   └── pdf_engine.py       # Indexation RAG, réponses et génération de synthèses PDF
├── assets/                 # Icônes et ressources graphiques
├── requirements.txt        # Dépendances Python
├── INSTALLER.bat           # Installation de l'environnement
├── L-GPT.bat               # Lancement de l'application
└── BUILD_EXE.bat           # Construction de l'exécutable
```

## Limites connues de la 2.9

- La pertinence mémoire utilise un recouvrement lexical simple, pas une recherche sémantique dédiée.
- La création automatique de souvenirs à partir des conversations n'est pas activée.
- Le cache KV n'est pas configurable par requête ; sa préférence est affichée sans modifier le serveur Ollama.
- Le moniteur matériel n'est pas continu et dépend des champs renvoyés par `ollama ps`.
- Les tokens/s affichés sont estimés à partir du texte, pas mesurés directement par les métadonnées d'inférence.
- L'OCR des PDF scannés n'est pas inclus.
- La version actuelle cible Windows. Les versions macOS et mobile restent au stade de la feuille de route.

## Feuille de route

- Améliorer la recherche de souvenirs (sémantique, pondération et pertinence par projet).
- Extraction contrôlée de souvenirs à partir des conversations, avec validation par l'utilisateur.
- Mesures natives de génération et tableau de bord matériel plus complet selon les API disponibles.
- Gestion plus fine des paramètres Ollama et détection des capacités réelles des modèles.
- Architecture multiplateforme pour macOS et accès mobile à un serveur L-GPT/Ollama.
