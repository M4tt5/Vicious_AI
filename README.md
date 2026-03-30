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


## Installation du serveur Python

### Prérequis système

- **Python 3.9+**
- **FFmpeg** (requis par Whisper pour décoder l'audio)
- **Ollama** (pour faire tourner le modèle de langage en local)

---

### 1. Installer FFmpeg

FFmpeg est nécessaire pour que Whisper puisse traiter les fichiers audio.

**Windows :**
```bash
winget install ffmpeg
# ou via Chocolatey :
choco install ffmpeg
```

**macOS :**
```bash
brew install ffmpeg
```

**Linux (Debian/Ubuntu) :**
```bash
sudo apt update && sudo apt install ffmpeg
```

Vérifier l'installation :
```bash
ffmpeg -version
```
Pour Windows, peut demander de créer le raccourci pour qu'il puisse le reconnaître
---

### 2. Installer les dépendances Python

Cloner le dépôt et installer les packages :

```bash
git clone https://github.com/KyleDottin/Vicious_AI.git
cd Vicious_AI
pip install -r requirements.txt
```

Si le fichier `requirements.txt` n'est pas présent, installer manuellement :

```bash
# Serveur web
pip install fastapi uvicorn python-multipart

# Chargement des variables d'environnement
pip install python-dotenv

# Requêtes HTTP (pour communiquer avec Ollama)
pip install requests

# Transcription audio (Speech-to-Text)
pip install openai-whisper

# PyTorch (requis par Whisper) — choisir la version adaptée à votre machine :

# CPU uniquement :
pip install torch

# GPU NVIDIA (CUDA 11.8) — plus rapide :
pip install torch --index-url https://download.pytorch.org/whl/cu118

# GPU NVIDIA (CUDA 12.1) :
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

---

### 3. Installer et configurer Ollama

Ollama permet de faire tourner le modèle **Qwen2.5:7b** en local pour la détection de vishing.

**Installation :**
```bash
# Linux / macOS :
curl -fsSL https://ollama.com/install.sh | sh

# Windows : télécharger l'installeur sur https://ollama.com
```

**Télécharger le modèle utilisé par le serveur :**
```bash
ollama pull qwen2.5:7b
```

**Démarrer Ollama (si pas lancé automatiquement) :**
```bash
ollama server
```

Ollama tourne sur `http://localhost:11434` par défaut, ce qui correspond à la configuration dans `server.py`.

---

### 4. Configurer les variables d'environnement

Créer un fichier `.env` à la racine du projet :

```env
API_KEY=votre_clé_secrète_ici
```

Cette clé est utilisée pour sécuriser les endpoints du serveur. L'application Android doit envoyer cette même clé dans le header `x-api-key` de chaque requête.

---

### 5. Lancer le serveur

```bash
python -m uvicorn Serveur.server:app --host localhost --port 8000
```

Le serveur sera accessible sur `http://<IP_de_votre_machine>:8000`.

Pour le développement avec rechargement automatique :
```bash
python -m uvicorn Serveur.server:app --host localhost --port 8000 --reload
```


## Installation sur Android

1. Cloner le dépôt et ouvrir le projet dans **Android Studio**
2. Synchroniser les dépendances Gradle
3. Configurer l'URL du serveur dans le code Kotlin (pointer vers l'IP du serveur)
4. Exécuter sur un appareil physique Android (recommandé pour l'accès au microphone et au téléphone)



## Endpoints de l'API

### `POST /stream-audio`
Reçoit un chunk audio toutes les ~5 secondes, le transcrit et l'analyse.

| Paramètre | Type | Description |
|---|---|---|
| `file` | fichier audio | Chunk audio (`.wav`, `.m4a`, etc.) |
| `session_id` | string | Identifiant unique de la session d'appel |
| `x-api-key` | header | Clé d'authentification |

**Réponse :**
```json
{
  "chunk_transcription": "Bonjour, je vous appelle de votre banque...",
  "chunk_analysis": {
    "risk_score": 85,
    "is_vishing": true,
    "reasoning": "Demande urgente d'informations bancaires",
    "urgency_detected": true
  }
}
```

---

### `POST /end-session`
Clôture une session et retourne le bilan complet de l'analyse.

| Paramètre | Type | Description |
|---|---|---|
| `session_id` | string | Identifiant de la session à clôturer |
| `x-api-key` | header | Clé d'authentification |

**Réponse :**
```json
{
  "timestamp": "2025-01-01T12:00:00",
  "full_transcription": "Transcription complète...",
  "global_risk_score": 72.5,
  "chunks": [...]
}
```

Les résultats sont également sauvegardés automatiquement dans le dossier `results/` au format JSON.


## Auteurs

- **Kyle DOTTIN**
- **Matthis DAVIAUD**
- **Martin JOUBERT DE LA MOTTE**
- **Nolan ECHASSERIEAU**
