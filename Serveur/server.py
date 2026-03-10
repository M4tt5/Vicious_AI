from fastapi import FastAPI, Header, HTTPException
import requests
import speech_to_text.whisper_transcribe as whisper_model

app = FastAPI()

API_KEY = "VISHIELD-SECRET-KEY"

OLLAMA_URL = "http://localhost:11434/api/generate"

def transcribe_audio(audio_path: str) -> str:
    """Run Whisper and return the transcription."""
    result = whisper_model.transcribe_audio_to_text(audio_path)
    return result

@app.post("/analyze-audio")
async def analyze_audio(
    file: UploadFile = File(...),
    x_api_key: str = Header(None)
):
    """
    Full pipeline:
      1. Receive audio file (WAV 16 kHz recommended)
      2. Transcribe with Whisper
      3. Analyze transcription with Ollama
      4. Return + save JSON result
    """
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Save upload to a temp file
    suffix = os.path.splitext(file.filename)[-1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        # Step 1: Speech-to-Text
        print(f"Transcribing: {file.filename}")
        transcription = transcribe_audio(tmp_path)
        print(f"Transcription: {transcription[:120]}...")

        # Step 2: Vishing detection
        print("Running vishing analysis...")
        # ----------------------------- analysis = detect_vishing(transcription)

        # Step 3: Build full result payload
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        result = {
            "timestamp": timestamp,
            "source_file": file.filename,
            "transcription": transcription,
            "analysis": analysis
        }

        # Step 4: Save JSON
        json_filename = f"vishing_{timestamp}_{file.filename}.json"
        saved_path = save_result(result, json_filename)
        print(f"Result saved → {saved_path}")

        return result

    finally:
        os.unlink(tmp_path)  # Clean up temp file


@app.post("/generate")
async def generate(request: dict, x_api_key: str = Header(None)):

    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    prompt = request.get("text")

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": "llama3.1:8b",
            "prompt": prompt,
            "stream": False
        }
    )

    return response.json()