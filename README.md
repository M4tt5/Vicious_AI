# Vicious AI – Analyse intelligente d’appels téléphoniques
## Présentation du projet

Vicious AI est une application Android permettant d’analyser le contenu d’un appel téléphonique à l’aide d’une intelligence artificielle distante. L’objectif principal du projet est de fournir à l’utilisateur un pourcentage de confiance indiquant la fiabilité de son interlocuteur, par exemple dans le cadre de la détection d’arnaques téléphoniques.

L’analyse est réalisée sur des serveurs externes afin de garantir le respect de la vie privée et d’éviter tout traitement local sensible sur l’appareil de l’utilisateur.

## Fonctionnalités principales

L’application propose une interface moderne et épurée comprenant plusieurs écrans essentiels. L’utilisateur accède d’abord à un écran de connexion visuel, permettant la saisie d’une adresse e-mail et d’un mot de passe. Une fois connecté, il arrive sur l’écran principal qui lui permet de lancer l’analyse d’un appel.

Lorsque l’analyse est en cours, une nouvelle vue affiche un pourcentage de confiance dynamique compris entre 0 % et 100 %. Ce pourcentage est représenté par un code couleur facilitant l’interprétation :

- Rouge : confiance faible (0 à 40 %)
- Orange : confiance moyenne (40 à 60 %)
- Vert : confiance élevée (au-dessus de 60 %)

L’utilisateur peut également consulter une section d’aide expliquant le fonctionnement de l’application et la gestion des permissions Android.

## Permissions requises

Pour fonctionner correctement, l’application nécessite certaines autorisations Android :
- Accès au microphone pour enregistrer l’audio
- Accès à l’état du téléphone pour détecter les appels
- Accès Internet pour communiquer avec les serveurs d’analyse

Si ces permissions sont refusées, l’utilisateur peut les réactiver manuellement depuis les paramètres de l’application.

## Technologies utilisées

Le projet repose sur les technologies suivantes :
- Android Studio
- Kotlin
- Material Design Components
- API Android (MediaRecorder, TelephonyManager)
- Architecture client-serveur pour l’analyse IA

## Installation et exécution

Pour lancer le projet, il suffit de cloner le dépôt GitHub, d’ouvrir le projet dans Android Studio, puis de synchroniser les dépendances Gradle. L’application peut ensuite être exécutée sur un appareil physique Android.
