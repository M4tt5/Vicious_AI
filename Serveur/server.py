from fastapi import FastAPI, Header, HTTPException
import requests

app = FastAPI()

API_KEY = "VISHIELD-SECRET-KEY"

OLLAMA_URL = "http://localhost:11434/api/generate"

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