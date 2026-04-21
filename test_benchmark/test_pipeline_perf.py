"""
Script de test de performance — simule l'envoi de segments audio de 5s
à partir de fichiers audio de 30 secondes (test1.m4a à test10.m4a).

Chaque fichier de 30s est découpé en 6 segments de 5s avant envoi.
Le délai entre chaque segment reproduit le comportement de l'app Android.

Dépendances :
    pip install pydub requests
    ffmpeg doit être installé sur la machine (nécessaire pour pydub)

Usage :
    python test_pipeline_perf.py
"""

import requests
import time
import uuid
import os
from pydub import AudioSegment
import tempfile

# ── Configuration ─────────────────────────────────────────────────────────────
SERVER_URL      = "http://127.0.0.1:8000"
AUDIO_FOLDER    = "."
NB_FILES        = 10          # nombre de fichiers audio (test1.m4a à test10.m4a)
SEGMENT_MS      = 5_000       # durée de chaque segment en ms (5 secondes)
DELAY_S         = 5           # délai entre chaque envoi (reproduit l'app Android)

FIREBASE_TOKEN  = "TOKEN"

# ── Helpers ───────────────────────────────────────────────────────────────────

def headers():
    return {"Authorization": f"Bearer {FIREBASE_TOKEN}"}

def print_separator():
    print("─" * 60)

def format_score(score) -> str:
    if score is None or score == "?":
        return "  Score : ? /100"
    score = int(score)
    filled = int(score / 5)
    bar    = "█" * filled + "░" * (20 - filled)
    if score >= 70:
        level = "RISQUE ÉLEVÉ"
    elif score >= 40:
        level = "RISQUE MODÉRÉ"
    else:
        level = "RISQUE FAIBLE"
    return f"  Score : [{bar}] {score}/100 — {level}"

def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    m, s = divmod(int(seconds), 60)
    return f"{m}m{s:02d}s"

# ── Découpage audio ───────────────────────────────────────────────────────────

def split_audio(filepath: str, segment_ms: int) -> list[str]:
    """
    Découpe un fichier audio en segments de segment_ms millisecondes.
    Retourne une liste de chemins vers les fichiers temporaires créés.
    """
    audio    = AudioSegment.from_file(filepath)
    segments = []
    tmp_dir  = tempfile.mkdtemp()

    for i, start in enumerate(range(0, len(audio), segment_ms)):
        chunk    = audio[start:start + segment_ms]
        out_path = os.path.join(tmp_dir, f"chunk_{i+1}.wav")
        chunk.export(out_path, format="wav")   # ipod = m4a/aac
        segments.append(out_path)

    return segments

# ── Envoi d'un segment ────────────────────────────────────────────────────────

def send_segment(session_id: str, segment_path: str, label: str) -> tuple[dict | None, float]:
    """Envoie un segment et retourne (réponse, durée_requête)."""
    t0 = time.time()
    with open(segment_path, "rb") as f:
        response = requests.post(
            f"{SERVER_URL}/stream-audio",
            headers=headers(),
            files={"file": (os.path.basename(segment_path), f, "audio/wav")},
            data={"session_id": session_id},
            timeout=120
        )
    elapsed = time.time() - t0

    if response.status_code == 200:
        return response.json(), elapsed
    else:
        print(f"  ✘ [{label}] Erreur {response.status_code} : {response.text}")
        return None, elapsed

# ── Fin de session ────────────────────────────────────────────────────────────

def end_session(session_id: str) -> tuple[dict | None, float]:
    t0 = time.time()
    response = requests.post(
        f"{SERVER_URL}/end-session",
        headers=headers(),
        data={"session_id": session_id},
        timeout=120
    )
    elapsed = time.time() - t0

    if response.status_code == 200:
        return response.json(), elapsed
    else:
        print(f"  ✘ end-session Erreur {response.status_code} : {response.text}")
        return None, elapsed

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    session_id      = str(uuid.uuid4())
    all_durations   = []   # durées de toutes les requêtes /stream-audio
    segment_global  = 0    # numéro de segment global sur toute la session

    print_separator()
    print(f"Session ID     : {session_id}")
    print(f"Serveur        : {SERVER_URL}")
    print(f"Fichiers       : {NB_FILES} fichiers de ~30s")
    print(f"Segment        : {SEGMENT_MS // 1000}s par chunk")
    print(f"Délai simulé   : {DELAY_S}s entre chaque envoi")
    print_separator()

    t_session_start = time.time()

    for file_num in range(1, NB_FILES + 1):
        filepath = os.path.join(AUDIO_FOLDER, f"test{file_num}.wav")

        if not os.path.exists(filepath):
            print(f"\n[Fichier {file_num}/{NB_FILES}] ✘ Introuvable : {filepath}")
            continue

        size_kb = os.path.getsize(filepath) // 1024
        print(f"\n[Fichier {file_num}/{NB_FILES}] {os.path.basename(filepath)} ({size_kb} Ko)")

        # Découpage en segments de 5s
        print(f"  Découpage en segments de {SEGMENT_MS // 1000}s...")
        t_split = time.time()
        segments = split_audio(filepath, SEGMENT_MS)
        print(f"  → {len(segments)} segments créés en {time.time() - t_split:.2f}s")

        for seg_idx, seg_path in enumerate(segments):
            segment_global += 1
            label = f"fichier {file_num}, chunk {seg_idx + 1}/{len(segments)}"

            print(f"\n  [Segment global #{segment_global} — {label}]")

            result, duration = send_segment(session_id, seg_path, label)
            all_durations.append(duration)

            if result:
                analysis   = result.get("chunk_analysis", {})
                score      = analysis.get("risk_score", "?")
                is_vishing = analysis.get("is_vishing", "?")
                transcript = result.get("chunk_transcription", "")

                print(f"  ✔ Transcription : {transcript[:80] if transcript else '(vide)'}")
                print(format_score(score))
                print(f"  Vishing         : {is_vishing}")
                print(f"  Temps requête   : {duration:.2f}s")

            # Nettoyage du fichier temporaire
            os.remove(seg_path)

            # Délai entre segments sauf pour le dernier
            is_last = (file_num == NB_FILES and seg_idx == len(segments) - 1)
            if not is_last:
                print(f"\n  Attente {DELAY_S}s (simulation app Android)...")
                time.sleep(DELAY_S)

    # ── Fin de session ────────────────────────────────────────────────────────
    print_separator()
    print("\n[Fin de session — résultat final]")

    final, end_duration = end_session(session_id)

    t_session_total = time.time() - t_session_start

    if final:
        global_score  = final.get("global_risk_score", "?")
        last_analysis = final.get("last_analysis", {})
        reasoning     = last_analysis.get("reasoning", "")
        is_vishing    = last_analysis.get("is_vishing", "?")
        chunks        = final.get("chunks", [])

        print(f"\n  Segments analysés  : {len(chunks)}")
        print(format_score(global_score))
        print(f"  Vishing détecté    : {is_vishing}")
        if reasoning:
            print(f"  Raisonnement final : {reasoning}")

    # ── Rapport de performance ────────────────────────────────────────────────
    print_separator()
    print("RAPPORT DE PERFORMANCE")
    print_separator()

    if all_durations:
        avg  = sum(all_durations) / len(all_durations)
        mini = min(all_durations)
        maxi = max(all_durations)

        print(f"  Segments envoyés   : {segment_global}")
        print(f"  Durée moyenne      : {avg:.2f}s / segment")
        print(f"  Durée minimale     : {mini:.2f}s")
        print(f"  Durée maximale     : {maxi:.2f}s")
        print(f"  Durée end-session  : {end_duration:.2f}s")
        print(f"  Durée totale       : {format_duration(t_session_total)}")
        print(f"  (dont attentes)    : {format_duration(DELAY_S * (segment_global - 1))}s de délais simulés")
        print(f"  (dont traitement)  : {format_duration(t_session_total - DELAY_S * (segment_global - 1))} de traitement réel")

    print_separator()

if __name__ == "__main__":
    main()
