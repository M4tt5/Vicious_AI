from fastapi import FastAPI, Header, HTTPException, UploadFile, File, Form
import requests
import speech_to_text.whisper_transcribe as whisper_model
import json
import os
import csv
import tempfile
import shutil
import time
from datetime import datetime
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .rag_engine import retrieve_relevant_context

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

OLLAMA_URL     = "http://localhost:11434/api/generate"
BENCHMARK_FILE = "benchmark.csv"

sessions = {}

# -----------------------------
# BENCHMARK — écriture CSV
# -----------------------------
def init_benchmark_file():
    """Crée le fichier CSV avec les en-têtes s'il n'existe pas encore."""
    if not os.path.exists(BENCHMARK_FILE):
        with open(BENCHMARK_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp",
                "session_id",
                "segment_index",
                "transcription_chars",
                "t_rag_s",
                "t_whisper_s",
                "t_qwen_s",
                "t_total_s",
                "risk_score",
                "is_vishing"
            ])

def append_benchmark(row: dict):
    """Ajoute une ligne de mesure dans le CSV."""
    with open(BENCHMARK_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            row.get("timestamp", ""),
            row.get("session_id", ""),
            row.get("segment_index", ""),
            row.get("transcription_chars", ""),
            round(row.get("t_rag_s", 0), 3),
            round(row.get("t_whisper_s", 0), 3),
            round(row.get("t_qwen_s", 0), 3),
            round(row.get("t_total_s", 0), 3),
            row.get("risk_score", ""),
            row.get("is_vishing", ""),
        ])

def print_session_summary(session_id: str):
    """Lit le CSV et affiche un résumé des temps pour la session courante."""
    rows = []
    try:
        with open(BENCHMARK_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows   = [r for r in reader if r["session_id"] == session_id]
    except FileNotFoundError:
        return

    if not rows:
        return

    def avg(col):
        vals = [float(r[col]) for r in rows if r[col] not in ("", None)]
        return sum(vals) / len(vals) if vals else 0.0

    def total(col):
        vals = [float(r[col]) for r in rows if r[col] not in ("", None)]
        return sum(vals)

    t_tot = total("t_total_s") or 1

    print("\n" + "═" * 60)
    print("  RÉSUMÉ BENCHMARK — session " + session_id[:8])
    print("═" * 60)
    print(f"  Segments traités      : {len(rows)}")
    print(f"  ── Temps moyens par segment ──────────────────")
    print(f"  RAG                   : {avg('t_rag_s'):.3f}s")
    print(f"  Whisper               : {avg('t_whisper_s'):.3f}s")
    print(f"  Qwen                  : {avg('t_qwen_s'):.3f}s")
    print(f"  Total / segment       : {avg('t_total_s'):.3f}s")
    print(f"  ── Temps cumulés sur la session ──────────────")
    print(f"  RAG                   : {total('t_rag_s'):.3f}s")
    print(f"  Whisper               : {total('t_whisper_s'):.3f}s")
    print(f"  Qwen                  : {total('t_qwen_s'):.3f}s")
    print(f"  Total session         : {total('t_total_s'):.3f}s")
    print(f"  ── Répartition du temps ──────────────────────")
    print(f"  RAG      : {total('t_rag_s') / t_tot * 100:.1f}%")
    print(f"  Whisper  : {total('t_whisper_s') / t_tot * 100:.1f}%")
    print(f"  Qwen     : {total('t_qwen_s') / t_tot * 100:.1f}%")
    autres = max(0, t_tot - total("t_rag_s") - total("t_whisper_s") - total("t_qwen_s"))
    print(f"  Autres   : {autres / t_tot * 100:.1f}%")
    print("═" * 60)
    print(f"  Données complètes sauvegardées → {BENCHMARK_FILE}")
    print("═" * 60 + "\n")

# Initialisation au démarrage du serveur
init_benchmark_file()

# -----------------------------
# IA VISHING (QWEN)
# -----------------------------
def detect_vishing(full_transcription: str) -> tuple[dict, float, float]:
    """
    Analyse la transcription complète.
    Retourne (analyse, t_rag_s, t_qwen_s).
    """
    # RAG
    t_rag_start = time.time()
    try:
        recent_text = " ".join(full_transcription.split()[-200:])
        rag_context = retrieve_relevant_context(recent_text)
        rag_text = "\n".join([
            f"- ({round(item['score'],2)}) [{item['label']}/{item['risk']}] {item['text']}"
            for item in rag_context
        ])
    except Exception:
        rag_text = ""
    t_rag_s = time.time() - t_rag_start

    system_prompt = f"""Tu es un expert en cybersécurité spécialisé dans la détection du vishing (fraude téléphonique).

Voici des exemples connus d'arnaques téléphoniques :
{rag_text}

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
{{
  "risk_score": <entier entre 0 et 100>,
  "is_vishing": <true ou false>,
  "reasoning": "<explication concise en français>",
  "urgency_detected": <true ou false>,
  "tactics_detected": {{
    "urgency": <true ou false>,
    "authority": <true ou false>,
    "sensitive_information": <true ou false>,
    "impersonation": <true ou false>
  }}
}}"""

    prompt = f"""
Analyse la transcription complète de la conversation téléphonique suivante :

{full_transcription}

Identifie les tactiques de social engineering présentes et évalue le risque de vishing.
"""

    # Qwen
    t_qwen_start = time.time()
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": "qwen2.5:3b",
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
        result   = json.loads(response.json().get("response", "{}"))
        t_qwen_s = time.time() - t_qwen_start

        print(
            f"  [TIMING] RAG        : {t_rag_s:.3f}s\n"
            f"  [TIMING] Qwen       : {t_qwen_s:.3f}s\n"
            f"  [RESULT] score={result.get('risk_score')} | "
            f"vishing={result.get('is_vishing')} | "
            f"tactiques={result.get('tactics_detected')}"
        )

        return result, t_rag_s, t_qwen_s

    except Exception as e:
        t_qwen_s = time.time() - t_qwen_start
        print(f"  [ERROR]  Ollama : {e}")
        return {"error": "analyse échouée"}, t_rag_s, t_qwen_s

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
    t_total_start = time.time()

    if session_id not in sessions:
        sessions[session_id] = {
            "transcriptions": [],
            "analyses":       [],
            "segment_count":  0,
            "uid":            uid
        }

    sessions[session_id]["segment_count"] += 1
    seg_idx = sessions[session_id]["segment_count"]

    print(f"\n[SEGMENT #{seg_idx}] session={session_id[:8]}...")

    suffix = os.path.splitext(file.filename)[-1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        # ── Whisper ───────────────────────────────────────────────────────────
        t_whisper_start   = time.time()
        new_transcription = transcribe_audio(tmp_path)
        t_whisper_s       = time.time() - t_whisper_start
        print(f"  [TIMING] Whisper    : {t_whisper_s:.3f}s")

        sessions[session_id]["transcriptions"].append(new_transcription)
        full_transcription = " ".join(sessions[session_id]["transcriptions"])

        # ── Qwen + RAG ────────────────────────────────────────────────────────
        analysis, t_rag_s, t_qwen_s = detect_vishing(full_transcription)
        sessions[session_id]["analyses"].append(analysis)

        t_total_s = time.time() - t_total_start
        print(f"  [TIMING] Total      : {t_total_s:.3f}s")

        # ── Sauvegarde benchmark ──────────────────────────────────────────────
        append_benchmark({
            "timestamp":           datetime.utcnow().isoformat(),
            "session_id":          session_id,
            "segment_index":       seg_idx,
            "transcription_chars": len(full_transcription),
            "t_rag_s":             t_rag_s,
            "t_whisper_s":         t_whisper_s,
            "t_qwen_s":            t_qwen_s,
            "t_total_s":           t_total_s,
            "risk_score":          analysis.get("risk_score", ""),
            "is_vishing":          analysis.get("is_vishing", ""),
        })

        return {
            "chunk_transcription": new_transcription,
            "full_transcription":  full_transcription,
            "chunk_analysis":      analysis
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

    data      = sessions.pop(session_id)
    full_text = " ".join(data["transcriptions"])

    last_scores = [
        a.get("risk_score")
        for a in data["analyses"]
        if isinstance(a, dict) and "risk_score" in a
    ]
    global_score  = last_scores[-1] if last_scores else 0
    last_analysis = data["analyses"][-1] if data["analyses"] else {}

    result = {
        "timestamp":          datetime.utcnow().isoformat(),
        "full_transcription": full_text,
        "global_risk_score":  global_score,
        "last_analysis":      last_analysis,
        "chunks":             data["analyses"]
    }

    filename = f"session_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.json"
    filepath = save_result(result, filename)

    # Affiche le résumé de performance de la session dans la console
    print_session_summary(session_id)

    try:
        return result
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)
