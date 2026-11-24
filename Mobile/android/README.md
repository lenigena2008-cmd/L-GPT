# L-GPT Mobile — projet Android

Ce dossier contient le premier squelette natif Android de L-GPT v4, écrit en Kotlin avec Jetpack Compose.

## Ouvrir le projet
1. Installer Android Studio.
2. Ouvrir le dossier `mobile/android` avec **Open**.
3. Laisser Android Studio synchroniser Gradle et télécharger les dépendances.
4. Lancer l'application sur un émulateur ou un téléphone Android.

## État de cette étape
- Structure Android native Kotlin créée.
- Première interface avec les trois modes : Document, Connaissances et Intelligent.
- Sélecteur visuel de moteur : téléphone ou PC/Ollama.
- Les boutons PDF, conversation et moteurs sont encore des emplacements d'interface : ils ne sont pas encore connectés.

## Architecture prévue
- `engine/` : interfaces et implémentations des moteurs IA (à venir).
- `data/` : stockage local, documents et conversations (à venir).
- `ui/` : composants d'interface (à venir).

Le moteur local `llama.cpp`, la connexion à Ollama sur PC, l'import PDF et la base de données seront intégrés progressivement. Ollama/llama.cpp ne sont pas inclus dans ce squelette.
