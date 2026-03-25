from fastapi import FastAPI, Header, HTTPException, UploadFile, File, Form
import requests
import speech_to_text.whisper_transcribe as whisper_model
import json
import os
import tempfile
import shutil
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

API_KEY = os.getenv("API_KEY")

OLLAMA_URL = "http://localhost:11434/api/generate"

# stockage des sessions
sessions = {}

# -----------------------------
# IA VISHING (QWEN)
# -----------------------------
def detect_vishing(transcription: str, context: str = "") -> dict:

    system_prompt = (
        "Tu es un expert en cybersécurité spécialisé dans la détection du vishing. "
        "Analyse la conversation et détecte une fraude. "
        "Réponds UNIQUEMENT en JSON avec : "
        "'risk_score' (0 à 100), 'is_vishing', 'reasoning', 'urgency_detected'."
    )

    prompt = f"""
Contexte précédent :
{context}

Nouvelle transcription :
{transcription}
"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": "qwen2.5:7b",
                "prompt": f"{system_prompt}\n{prompt}",
                "stream": False,
                "format": "json"
            },
            timeout=30
        )
        response.raise_for_status()

        return json.loads(response.json().get("response", "{}"))

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
    x_api_key: str = Header(None)
):

    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # créer session si elle n'existe pas
    if session_id not in sessions:
        sessions[session_id] = {
            "transcriptions": [],
            "analyses": []
        }

    # save fichier temporaire
    suffix = os.path.splitext(file.filename)[-1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        # transcription
        transcription = transcribe_audio(tmp_path)

        # contexte = 3 derniers chunks
        context = " ".join(sessions[session_id]["transcriptions"][-3:])

        # analyse IA
        analysis = detect_vishing(transcription, context)

        # stockage
        sessions[session_id]["transcriptions"].append(transcription)
        sessions[session_id]["analyses"].append(analysis)

        return {
            "chunk_transcription": transcription,
            "chunk_analysis": analysis
        }

    finally:
        os.unlink(tmp_path)

# -----------------------------
# FIN SESSION
# -----------------------------
@app.post("/end-session")
async def end_session(
    session_id: str = Form(...),
    x_api_key: str = Header(None)
):

    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    data = sessions.pop(session_id)

    full_text = " ".join(data["transcriptions"])

    scores = [
        a.get("risk_score", 0)
        for a in data["analyses"]
        if isinstance(a, dict)
    ]

    global_score = sum(scores) / len(scores) if scores else 0

    result = {
        "timestamp": datetime.utcnow().isoformat(),
        "full_transcription": full_text,
        "global_risk_score": global_score,
        "chunks": data["analyses"]
    }

    filename = f"session_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.json"
    save_result(result, filename)

    return result