# L-GPT 2.8 — Assistant IA local, modèles et mémoire

L-GPT est un assistant de bureau local pour Windows. Sa mission principale est de lire, comprendre, expliquer et synthétiser des cours au format PDF. Il peut aussi répondre aux questions générales sans document.

L'application utilise **Ollama** pour exécuter les modèles de langage sur la machine et **SQLite** pour conserver les conversations, les préférences et les mémoires. Aucun compte cloud n'est requis.

## Nouveautés de la version 2.8

- Paramètres IA accessibles depuis la barre latérale.
- Détection des modèles installés dans Ollama et consultation de leurs métadonnées lorsqu'elles sont disponibles.
- Affichage de la taille des modèles et de leur quantification lorsque Ollama la communique.
- Routage automatique simple entre modèles installés, avec choix manuel toujours possible.
- Trois profils : Performance, Équilibré et Qualité.
- Préférences de contexte et de cache KV enregistrées dans les paramètres.
- Espace de mémoire permettant d'ajouter, modifier et supprimer des informations générales ou liées à un projet.
- Migration SQLite non destructive : les tables des conversations existantes sont conservées et les nouvelles tables sont ajoutées si nécessaire.
- Documentation et procédures d'installation actualisées.

> Transparence : le routage v2.8 est une heuristique locale fondée sur la longueur et certains indices de complexité de la question, les modèles installés et le profil choisi. Ce n'est pas un benchmark ni un système de mesure parfaite de la difficulté.

## Les trois modes de réponse

- **Intelligent (par défaut)** : choisit entre les documents et les connaissances générales en fonction de la question et des passages retrouvés. Fonctionne même sans PDF.
- **Document** : répond uniquement à partir des PDF indexés. Si aucun document pertinent n'est disponible, L-GPT le signale.
- **Connaissances** : répond à partir du modèle, sans utiliser les PDF.

Les réponses indiquent la provenance choisie : Documents, Connaissances ou Documents + connaissances. En mode Intelligent, une courte explication de la décision est ajoutée. Les passages documentaires cités indiquent le fichier et la page lorsque ces informations sont disponibles.

## Gestion des modèles Ollama

Le menu **Paramètres IA et mémoire → IA et modèles** interroge Ollama pour afficher les modèles locaux. L'application tente de récupérer leur taille et leurs métadonnées, notamment la quantification.

Les formats de quantification peuvent notamment appartenir aux familles suivantes :

- K-quants : Q2_K, Q3_K, Q4_K, Q5_K, Q6_K, Q8_0 et variantes.
- I-quants : IQ1, IQ2, IQ3, IQ4 et variantes.
- Formats non quantifiés ou autres : F16, BF16, F32, ainsi que certains formats compacts ou spécialisés tels que TQ, MXFP4, NVFP4, FP8 ou INT8.

La liste ci-dessus est un aide-mémoire, **pas une garantie de prise en charge**. L-GPT affiche la quantification fournie par les métadonnées Ollama ; si elle n'est pas disponible, il indique qu'elle n'est pas communiquée. La présence d'un nom de format ne signifie pas que chaque modèle, version d'Ollama ou matériel le prend en charge. L-GPT ne convertit pas les modèles et ne modifie pas automatiquement leurs fichiers.

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

Adapte le nom du modèle à celui que tu souhaites réellement installer. `nomic-embed-text` sert à créer les embeddings pour la recherche dans les PDF ; il ne remplace pas un modèle conversationnel.

## Routage automatique et profils

Le choix manuel reste disponible dans la liste des modèles de la barre latérale. Lorsque le routage automatique est activé, L-GPT essaie de choisir un modèle installé selon le profil et une estimation simple de la tâche :

- **Performance** : favorise les modèles plus légers.
- **Équilibré** : compromis entre rapidité et capacité ; profil par défaut.
- **Qualité** : favorise les modèles plus puissants lorsqu'ils sont installés.

Le routage reconnaît notamment des variantes de modèles contenant `4b`, `9b` ou `27b`. Si aucune correspondance n'est trouvée, il retombe sur le modèle actuellement sélectionné ou sur le premier modèle disponible. Le modèle choisi et la raison simplifiée apparaissent sous la liste des modèles.

Cette logique est volontairement prudente : elle ne mesure pas automatiquement la RAM disponible, la vitesse réelle de génération ou la qualité d'une réponse. Les performances dépendent du modèle, de sa quantification, du contexte, d'Ollama et du matériel.

## Contexte et cache KV

Les préférences de contexte proposées sont 8 192, 16 384, 32 768 et 65 536 tokens. Les choix de cache KV proposés sont f16, q8_0 et q4_0.

**Dans cette version, ces valeurs sont enregistrées comme préférences utilisateur et affichées dans les paramètres. Elles ne sont pas encore injectées automatiquement dans chaque appel Ollama.** Leur application effective dépend du support par la version d'Ollama, le modèle et le backend matériel. Ne considère donc pas la valeur choisie comme la fenêtre réellement active. La fenêtre utilisée par le moteur actuel reste définie dans `core/pdf_engine.py`.

## Mémoire et continuité

Dans l'onglet **Mémoire**, l'utilisateur peut créer, modifier et supprimer :

- des mémoires générales ;
- des mémoires de type projet, pour conserver objectifs, décisions, contraintes ou prochaines étapes.

Ces données sont stockées localement dans la base SQLite de L-GPT. La gestion est **manuelle dans cette version** : L-GPT ne prétend pas extraire automatiquement des souvenirs de chaque conversation et n'injecte pas encore automatiquement les mémoires dans les prompts. Elles constituent un espace persistant que l'utilisateur peut consulter et entretenir.

Les conversations sont restaurées depuis la base locale. Les chemins des PDF associés sont conservés dans l'historique ; les fichiers eux-mêmes restent à leur emplacement d'origine. Si un PDF a été déplacé ou supprimé, il faudra le retrouver pour pouvoir le réindexer.

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

Le modèle conversationnel peut être remplacé par un autre modèle compatible déjà installé dans Ollama.

## Utilisation

- Pose directement une question générale, même sans PDF.
- Utilise **Importer des PDF** pour sélectionner un ou plusieurs cours. Attends la fin de l'indexation avant de poser une question sur leur contenu.
- Choisis le mode Intelligent, Document ou Connaissances.
- Choisis manuellement le modèle dans la liste ou configure le routage automatique dans les paramètres.
- Utilise **Créer un résumé PDF** pour générer une synthèse des documents importés.
- Les conversations sont sauvegardées automatiquement et apparaissent dans la liste RÉCENT.
- Ajoute ou corrige les informations persistantes dans l'onglet Mémoire.

## Création de l'exécutable

Après installation des dépendances, lance `BUILD_EXE.bat`. PyInstaller crée un dossier `dist\L-GPT`.

Conserve **tout le dossier** `dist\L-GPT` : ne déplace pas uniquement `L-GPT.exe`. Ollama doit rester installé séparément et les modèles doivent être présents sur la machine qui exécute l'application.

## Données locales et confidentialité

La base de données est enregistrée dans :

```text
%APPDATA%\L-GPT\conversations.db
```

Elle contient les conversations, les paramètres et les mémoires. Les mises à jour de L-GPT ne doivent pas nécessiter la suppression de ce fichier. La version 2.8 ajoute des tables si elles n'existent pas ; elle ne supprime pas les anciennes conversations.

Les PDF ne sont pas copiés dans la base : leurs chemins sont mémorisés et les fichiers restent à leur emplacement d'origine. Pense à sauvegarder séparément la base et tes documents importants.

## Dépannage

**L-GPT indique qu'Ollama est inaccessible**

- Vérifie qu'Ollama est installé et démarré.
- Dans PowerShell, exécute `ollama list`.
- Si la commande échoue, redémarre Ollama puis relance L-GPT.

**Aucun modèle n'apparaît**

- Télécharge un modèle avec `ollama pull nom-du-modele`.
- Clique sur le bouton ↻ à côté de la liste des modèles.

**Le modèle est trop lent ou la mémoire manque**

- Essaie un modèle plus petit ou un profil Performance.
- Réduis la taille de contexte dans les paramètres pour garder une préférence plus basse ; note que son application effective au moteur est encore à venir dans cette version.
- Ferme les applications lourdes et vérifie les informations d'Ollama avec `ollama ps`.

**L'indexation PDF échoue ou ne trouve aucun texte**

- Vérifie que le PDF est lisible et non protégé.
- Le moteur extrait le texte intégré au PDF. L'OCR des documents scannés n'est pas inclus dans cette version.
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
│   └── pdf_engine.py       # Indexation RAG, réponses et génération PDF
├── assets/                 # Icônes et ressources visuelles
├── requirements.txt        # Dépendances Python
├── INSTALLER.bat           # Création de l'environnement et installation
├── L-GPT.bat               # Démarrage de l'application
├── BUILD_EXE.bat           # Construction avec PyInstaller
└── README.md               # Documentation
```

## Limites connues de la version 2.8

- Windows est la plateforme ciblée et testée par conception ; les versions macOS et mobile sont des évolutions futures.
- Le routage des modèles est heuristique et ne constitue pas une évaluation automatique de la qualité.
- Les préférences de contexte/cache sont sauvegardées, mais pas encore appliquées dynamiquement aux appels Ollama.
- La mémoire est gérée manuellement et n'est pas automatiquement injectée dans les conversations.
- La mesure détaillée en temps réel de RAM, CPU, GPU, VRAM, tokens/seconde et temps avant premier token n'est pas encore implémentée.
- L'OCR des PDF scannés et la conversion de quantification ne sont pas inclus.
- La compatibilité des modèles et des options dépend de la version d'Ollama et du matériel.

## Feuille de route indicative

- **2.8** : inventaire des modèles, profils et routage de base, préférences IA, mémoire locale manuelle, documentation.
- **2.9** : application effective et validation des paramètres de contexte/cache, statistiques de génération et surveillance des ressources lorsque disponibles, récupération sélective des mémoires.
- **3.0** : séparation plus poussée du moteur et de l'interface pour préparer macOS et un client mobile connecté à un serveur L-GPT/Ollama.

## Identité de L-GPT

L-GPT possède une identité fonctionnelle définie par sa mission, ses règles et ses modes de fonctionnement. Cela ne signifie pas qu'il possède une conscience subjective.
