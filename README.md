# L-GPT 2.6 — Assistant IA local

L-GPT est un assistant local dont la mission principale est de lire, comprendre et synthétiser des cours PDF. Il peut également répondre à des questions générales sans qu'aucun PDF ne soit importé.

## Trois modes de réponse
- **Intelligent (par défaut)** : choisit automatiquement entre les documents importés et les connaissances du modèle. Sans PDF, il répond directement avec les connaissances du modèle.
- **Document** : répond uniquement à partir des PDF indexés. Si aucun document n'est disponible, il l'indique clairement.
- **Connaissances** : répond sans consulter les PDF.

Chaque réponse indique la source utilisée : Documents, Connaissances ou Documents + connaissances.

## Installation
1. Installe Python 3.11 ou plus récent et Ollama.
2. Installe les dépendances avec `pip install -r requirements.txt`.
3. Télécharge un modèle de conversation dans Ollama (par exemple `ollama pull qwen3.5:9b`) et le modèle d'embedding `ollama pull nomic-embed-text`.
4. Lance `L-GPT.bat`.

Les PDF sont facultatifs pour les conversations générales. Pour interroger un PDF, importe-le et attends l'indexation.

## Données et confidentialité
Les conversations restent stockées localement dans `%APPDATA%\L-GPT\conversations.db`. Cette version conserve la base de conversations existante ; ne la supprime pas lors d'une mise à jour. Les fichiers PDF restent à leur emplacement d'origine.

## Limites
Le mode Intelligent s'appuie sur une sélection heuristique et la pertinence sémantique des passages retrouvés ; il peut se tromper de source. Vérifie les réponses importantes. Les PDF scannés nécessitent un OCR qui n'est pas inclus.

L-GPT possède une identité fonctionnelle (mission, règles et modes), pas une conscience subjective.

## Création de l'exécutable
Lance `BUILD_EXE.bat` depuis Windows après installation des dépendances.
