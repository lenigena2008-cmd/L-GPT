# L-GPT — Assistant IA local pour Windows

L-GPT est une application de bureau qui utilise les modèles installés localement avec **Ollama**.

## Fonctionnalités

- Interface de conversation sombre, avec réponses Markdown.
- Import de plusieurs PDF et recherche de passages pertinents pour répondre aux questions.
- Affichage des documents et pages utilisés comme sources.
- Génération de synthèses PDF structurées à partir de plusieurs cours, avec fenêtre de contexte augmentée jusqu’à 16 384 tokens et génération sans limite artificielle de tokens de sortie.
- Détection automatique des modèles de conversation installés dans Ollama.
- Historique permanent des conversations, sauvegardé automatiquement dans une base SQLite locale.
- Restauration des anciennes discussions, renommage et suppression depuis la barre latérale.
- Réindexation automatique des PDF associés à une conversation lorsqu’on la rouvre (si les fichiers sont toujours au même emplacement).
- Génération en flux (streaming) et sans limite artificielle de nombre de tokens de sortie : le modèle peut continuer jusqu'à ce qu'il termine sa réponse. La durée et la longueur restent dépendantes du modèle, de la mémoire disponible et de sa fenêtre de contexte.
- Traitement local : les PDF et leurs index restent sur l'ordinateur.

## Prérequis

1. Windows 10 ou 11.
2. Python 3.11 ou plus récent.
3. Ollama installé et démarré.
4. Au moins un modèle de conversation Ollama et le modèle d'embeddings `nomic-embed-text`.

Téléchargement officiel d'Ollama : <https://ollama.com/download>

## Installer L-GPT

1. Télécharge ou clone le dépôt GitHub.
2. Extrais le dossier `L-GPT` dans un emplacement normal, par exemple `Documents\L-GPT`.
3. Double-clique sur `INSTALLER.bat` et attends la fin de l'installation.
4. Télécharge les modèles Ollama souhaités (voir la section suivante).
5. Vérifie qu'Ollama est démarré, puis lance `L-GPT.bat`.

## Télécharger des modèles Ollama

Ollama n'installe pas automatiquement de modèle avec son programme. Les modèles se téléchargent séparément.

### Méthode simple avec le terminal Windows

1. Ouvre le menu Démarrer.
2. Recherche **Terminal** ou **PowerShell** et ouvre-le.
3. Tape la commande `ollama pull` suivie du nom du modèle.
4. Attends la fin du téléchargement. La taille peut atteindre plusieurs gigaoctets.

Exemples de commandes :

```powershell
ollama pull gemma4
ollama pull gemma4:e4b
ollama pull gemma4:12b
ollama pull qwen3
ollama pull llama3.3
ollama pull nomic-embed-text
```

Les noms et variantes disponibles évoluent. Avant de télécharger une variante précise, consulte sa fiche et copie le nom exact affiché dans la bibliothèque Ollama : <https://ollama.com/library>.

Par exemple, la page Gemma 4 liste plusieurs tailles (`gemma4:e2b`, `gemma4:e4b`, `gemma4:12b`, `gemma4:26b`, `gemma4:31b`). Il suffit d'utiliser le nom exact après `ollama pull`.

### Vérifier les modèles installés

Dans le terminal, exécute :

```powershell
ollama list
```

Pour lancer un modèle directement dans le terminal :

```powershell
ollama run gemma4
```

Pour supprimer un modèle et libérer de l'espace disque :

```powershell
ollama rm nom-du-modele
```

### Faire apparaître un nouveau modèle dans L-GPT

L-GPT interroge Ollama au démarrage et récupère automatiquement les modèles locaux installés. Si l'application est déjà ouverte pendant le téléchargement d'un nouveau modèle :

1. Termine le téléchargement dans le terminal.
2. Dans L-GPT, clique sur le petit bouton **↻** à côté de la liste « Modèle IA ».
3. Le nouveau modèle doit apparaître dans la liste. Sélectionne-le pour l'utiliser.

Le modèle `nomic-embed-text` sert à transformer les passages PDF en vecteurs de recherche. Il est donc utilisé en arrière-plan et n'est pas proposé comme modèle de conversation.

### Choisir une taille adaptée à son ordinateur

Les modèles les plus grands demandent généralement plus de mémoire vive et peuvent répondre beaucoup plus lentement. Commence par une variante légère si ton ordinateur dispose de peu de mémoire. Vérifie la taille indiquée sur la fiche du modèle avant de le télécharger. Avoir assez d'espace disque ne garantit pas que le modèle pourra fonctionner en mémoire.

## Utiliser L-GPT

1. Démarre Ollama.
2. Lance `L-GPT.bat`.
3. Choisis un modèle dans la liste « Modèle IA ».
4. Clique sur **Importer des PDF** et sélectionne un ou plusieurs cours.
5. Attends la fin de l'indexation, puis pose tes questions dans la zone de saisie. Entrée envoie le message ; Maj+Entrée ajoute une ligne.
6. Pour créer une synthèse, clique sur **Créer un résumé PDF**, choisis l'emplacement du fichier et attends la fin de la génération.

Les index sont mis en cache à côté des PDF (`.rag.json`) pour éviter de recalculer les embeddings à chaque lancement. Les PDF scannés sans couche de texte nécessitent un OCR et ne sont pas pris en charge dans cette version.

## Génération de réponses longues

La génération des réponses utilise le streaming et `num_predict = -1` côté Ollama, ce qui supprime la limite artificielle de sortie imposée auparavant par L-GPT. La génération se poursuit jusqu'à ce que le modèle décide de terminer.

Cela ne signifie pas une longueur littéralement infinie : le modèle peut terminer naturellement, et la mémoire disponible, la fenêtre de contexte, la taille du prompt et les limites propres au modèle restent déterminantes. Une réponse très longue peut aussi prendre plusieurs minutes.

## Créer une application `.exe`

Après l'installation des dépendances, lance `BUILD_EXE.bat`. Le résultat est normalement placé dans `dist\L-GPT\L-GPT.exe`. Conserve tout le dossier `dist\L-GPT`, pas uniquement le fichier EXE. Ollama et ses modèles restent des prérequis externes.

## Dépannage

- **Ollama hors ligne** : vérifie qu'Ollama est installé et démarré.
- **Un modèle n'apparaît pas** : exécute `ollama list`, puis clique sur **↻** dans L-GPT.
- **Erreur de mémoire / modèle impossible à charger** : essaie une variante plus petite et ferme les applications lourdes. La mémoire requise dépend de la taille, de la quantification et de la fenêtre de contexte.
- **Erreur au démarrage de l'interface** : consulte `L-GPT_erreurs.log` s'il a été créé.
- **Réinstaller les dépendances** : relance `INSTALLER.bat`.

## Historique permanent des conversations

Les conversations sont enregistrées automatiquement dans une base SQLite locale. Fermer puis relancer L-GPT ne supprime donc pas l'historique.

- La liste « Récent » affiche les conversations enregistrées, de la plus récente à la plus ancienne.
- Clique sur une conversation pour afficher à nouveau tous ses messages.
- « Renommer » permet de modifier son titre et « Supprimer » l'efface définitivement.
- « Nouvelle conversation » démarre un fil séparé sans effacer les précédents.
- Les messages sont sauvegardés au fil de la discussion et à la fermeture de l'application.
- Lorsqu'une conversation est rouverte, L-GPT essaie de réindexer les PDF qui lui étaient associés. Les fichiers doivent toujours exister au même emplacement. Si un PDF a été déplacé ou supprimé, il faudra le réimporter.

### Emplacement de la base de données

Sous Windows, les données sont conservées dans :

```text
%APPDATA%\L-GPT\conversations.db
```

En général, cela correspond à `C:\Users\VotreNom\AppData\Roaming\L-GPT\conversations.db`. La base est indépendante du dossier du programme : mettre à jour ou remplacer le dossier de L-GPT ne supprime donc pas les conversations. Pour sauvegarder l'historique, ferme L-GPT puis copie le fichier `conversations.db` dans un emplacement sûr. Ne partage pas ce fichier s'il contient des conversations privées.

Pour continuer une discussion, L-GPT transmet au modèle les derniers échanges de la conversation restaurée. Le fil complet reste visible et sauvegardé dans la base, mais le contexte réellement transmis au modèle dépend de la fenêtre de contexte et de la mémoire disponible.

## Formules dans les PDF générés

Les consignes de génération interdisent le LaTeX. Les formules doivent être écrites en notation texte lisible, par exemple `(a)/(b)`, `x^2`, `×`, `√(...)` et `H2O`. Le moteur nettoie également plusieurs commandes LaTeX fréquentes avant la mise en page du PDF.


## Arrêter une génération (v2.3)

- Pendant une réponse dans le chat, le bouton d'envoi est remplacé par un bouton carré **Arrêter**. Il interrompt le flux Ollama et conserve dans la conversation le texte déjà généré.
- Pendant la création d'une synthèse PDF, le bouton **Arrêter la synthèse** apparaît sous le bouton de création. L'arrêt est pris en compte pendant les appels de génération et entre les différentes parties du cours.
- L'arrêt d'une synthèse avant la création finale du PDF ne produit pas de fichier PDF incomplet.


## Version 2.4 – Nettoyage des formules

- Nettoyage renforcé du LaTeX résiduel dans les synthèses PDF.
- Conversion des fractions (`\\frac`, `\\dfrac`, `\\tfrac`), racines, indices, exposants, symboles grecs et opérateurs courants en notation texte lisible.
- Nettoyage des commandes de mise en forme, délimiteurs mathématiques et environnements d’alignement.
- Les consignes de génération et de fusion des synthèses interdisent plus explicitement les commandes LaTeX.
- Les fonctionnalités de la version 2.3, notamment l’arrêt de génération et l’historique permanent, sont conservées.
