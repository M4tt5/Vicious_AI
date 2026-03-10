'''
Before starting, install:
pip install vosk soundfile

Download vosk-model-small-en-us-0.15 from https://alphacephei.com/vosk/models
and extract it to a folder named 'model' in this script's directory.
'''
import os
import wave
import json
from vosk import Model, KaldiRecognizer

# path to the audio (must be WAV PCM 16-bit)
audio_path = "audio-wav-16khz_1002976_normalized_noise.wav"
model_path = "model"

if not os.path.exists(audio_path):
    raise FileNotFoundError(f"Audio file not found: {audio_path}")

if not os.path.isdir(model_path):
    raise FileNotFoundError(
        f"Vosk model not found at '{model_path}'"
    )

wf = wave.open(audio_path, "rb")
if wf.getsampwidth() != 2:
    raise ValueError("Audio must be 16-bit PCM WAV. Convert the file before running.")

model = Model(model_path)
rec = KaldiRecognizer(model, wf.getframerate())
rec.SetWords(True)

results = []
while True:
    data = wf.readframes(4000)
    if len(data) == 0:
        break
    if rec.AcceptWaveform(data):
        part = json.loads(rec.Result())
        if "text" in part:
            results.append(part["text"])

# final chunk
final_part = json.loads(rec.FinalResult())
if "text" in final_part:
    results.append(final_part["text"])

transcription = " ".join([r for r in results if r])

print("Texte transcrit :")
print(transcription)
