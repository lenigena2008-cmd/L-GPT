# L-GPT Mobile — Version 4.0

## Objectif

Créer une application Android native pour L-GPT, complémentaire
à la version Windows/macOS.

## Architecture Dual Engine

L'application proposera trois possibilités :

1. PC : utiliser les modèles installés sur l'ordinateur via Ollama.
2. Mobile : exécuter les modèles directement sur Android via llama.cpp.
3. Automatique : sélectionner le moteur le plus adapté.

## Fonctionnalités prévues

- Importation et analyse de PDF.
- Résumés automatiques.
- Conversations avec l'IA.
- Mode Document.
- Mode Connaissances.
- Mode Intelligent.
- Historique des conversations.
- Bibliothèque de documents.
- Gestion des modèles IA.
- Synchronisation avec L-GPT Desktop.

## Architecture technique

- Interface : Kotlin / Android.
- Moteur IA local : llama.cpp.
- Moteur IA PC : Ollama.
- Communication PC/mobile : API sécurisée.
- Stockage local : SQLite.
- Gestion des PDF : composants compatibles Android.

## Principes

- Ne pas modifier la version Windows fonctionnelle.
- Conserver une architecture modulaire.
- Permettre le fonctionnement hors ligne.
- Ne pas imposer une connexion à un PC.
- Protéger les données et les communications.

## État du développement

Phase de préparation de l'architecture.
Aucune fonctionnalité Android n'est encore implémentée.
