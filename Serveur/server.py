from fastapi import FastAPI, Header, HTTPException, UploadFile, File, Form
import requests
import speech_to_text.whisper_transcribe as whisper_model
import json
import os
import tempfile
import shutil
from datetime import datetime
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

cred = credentials.Certificate("viciousai-firebase-adminsdk-fbsvc-19d9b0bcfa.json")
firebase_admin.initialize_app(cred)

bearer_scheme = HTTPBearer()

def verify_firebase_token(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
) -> str:
    try:
        decoded = firebase_auth.verify_id_token(credentials.credentials)
        return decoded["uid"]
    except Exception:
        raise HTTPException(status_code=401, detail="Token Firebase invalide ou expiré")

app = FastAPI()

OLLAMA_URL = "http://localhost:11434/api/generate"

sessions = {}

# -----------------------------
# IA VISHING (QWEN)
# -----------------------------
def detect_vishing(full_transcription: str) -> dict:
    """
    Analyse la transcription COMPLÈTE de la conversation depuis le début.
    Plus de contexte partiel — l'IA voit tout à chaque segment.
    """
    system_prompt = """Tu es un expert en cybersécurité spécialisé dans la détection du vishing (fraude téléphonique).

Tu analyses des transcriptions de conversations téléphoniques en te basant sur 4 tactiques de social engineering reconnues :

1. Urgency — Créer un sentiment d'urgence ou de pression pour pousser la victime à agir rapidement sans réfléchir.
2. Authority — Utiliser une position d'autorité ou d'expertise (banque, police, Amazon, Microsoft...) pour manipuler la cible.
3. Sensitive Information — Tenter d'obtenir des informations confidentielles (numéro de carte, mot de passe, code OTP...).
4. Impersonation — Se faire passer pour quelqu'un d'autre afin d'accéder à des informations confidentielles.

Pour chaque conversation, tu dois :
- Identifier quelles tactiques sont présentes
- Évaluer le niveau de risque global
- Expliquer ton raisonnement de façon claire et concise

Réponds UNIQUEMENT en JSON valide avec exactement ces champs :
{
  "risk_score": <entier entre 0 et 100>,
  "is_vishing": <true ou false>,
  "reasoning": "<explication concise en français>",
  "urgency_detected": <true ou false>,
  "tactics_detected": {
    "urgency": <true ou false>,
    "authority": <true ou false>,
    "sensitive_information": <true ou false>,
    "impersonation": <true ou false>
  }
}"""

    prompt = f"""
Analyse la transcription complète de la conversation téléphonique suivante :

{full_transcription}

Identifie les tactiques de social engineering présentes et évalue le risque de vishing.
"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": "qwen2.5:7b",
                "prompt": f"{system_prompt}\n{prompt}",
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9
                }
            },
            timeout=60
        )
        response.raise_for_status()
        result = json.loads(response.json().get("response", "{}"))
        print(f"Analyse : score={result.get('risk_score')} | vishing={result.get('is_vishing')} | tactiques={result.get('tactics_detected')}")
        return result

    except Exception as e:
        print(f"Erreur Ollama : {e}")
        return {"error": "analyse échouée"}

# -----------------------------
# SPEECH TO TEXT
# -----------------------------
def transcribe_audio(audio_path: str) -> str:
    return whisper_model.transcribe_audio_to_text(audio_path)

# -----------------------------
# SAVE JSON
# -----------------------------
def save_result(data: dict, filename: str) -> str:
    folder = "results"
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    return filepath

# -----------------------------
# STREAM AUDIO (toutes les 5 sec)
# -----------------------------
@app.post("/stream-audio")
async def stream_audio(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    uid: str = Depends(verify_firebase_token)
):
    if session_id not in sessions:
        sessions[session_id] = {
            "transcriptions": [],
            "analyses": [],
            "uid": uid
        }

    suffix = os.path.splitext(file.filename)[-1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        # Transcription du nouveau segment
        new_transcription = transcribe_audio(tmp_path)
        sessions[session_id]["transcriptions"].append(new_transcription)

        # ── Transcription complète depuis le début de la session ──────────────
        full_transcription = " ".join(sessions[session_id]["transcriptions"])

        # ── L'IA analyse toute la conversation à chaque segment ───────────────
        analysis = detect_vishing(full_transcription)
        sessions[session_id]["analyses"].append(analysis)

        return {
            "chunk_transcription": new_transcription,       # juste le nouveau segment
            "full_transcription":  full_transcription,      # toute la conversation
            "chunk_analysis":      analysis                 # analyse sur le tout
        }

    finally:
        os.unlink(tmp_path)

# -----------------------------
# FIN SESSION
# -----------------------------
@app.post("/end-session")
async def end_session(
    session_id: str = Form(...),
    uid: str = Depends(verify_firebase_token)
):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    data           = sessions.pop(session_id)
    full_text      = " ".join(data["transcriptions"])

    # Score global = dernier score (le plus précis car basé sur toute la transcription)
    last_scores = [
        a.get("risk_score")
        for a in data["analyses"]
        if isinstance(a, dict) and "risk_score" in a
    ]
    global_score = last_scores[-1] if last_scores else 0

    # Dernière analyse = la plus complète (elle a vu toute la transcription)
    last_analysis = data["analyses"][-1] if data["analyses"] else {}

    result = {
        "timestamp":          datetime.utcnow().isoformat(),
        "full_transcription": full_text,
        "global_risk_score":  global_score,
        "last_analysis":      last_analysis,    # analyse finale la plus fiable
        "chunks":             data["analyses"]
    }

    filename = f"session_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.json"
    filepath = save_result(result, filename)

    try:
        return result
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)