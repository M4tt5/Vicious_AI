'''
before starting, install: 
pip install torch
pip install openai-whisper
and install ffmpeg for your OS
have numpy 2.2.3 not 2.2.4
'''
import whisper
import shutil

ffmpeg_path = shutil.which("ffmpeg")
if ffmpeg_path is None:
    raise EnvironmentError("ffmpeg not found. Please install ffmpeg and ensure it's in your system PATH.")

# Load the Whisper model
model = whisper.load_model("base")

# path to the audio
audio_path = "audio-wav-16khz_1002976_normalized_noise.wav"

# Transcription
result = model.transcribe(
    audio_path,
    language="en",
    fp16=False
)

# transcription result
print("Texte transcrit :")
print(result["text"])
