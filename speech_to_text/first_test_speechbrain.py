'''
before starting, install:
pip install speechbrain torch torchaudio
and install ffmpeg for your OS (if not already installed)
'''
import shutil
from speechbrain.pretrained import EncoderDecoderASR

ffmpeg_path = shutil.which("ffmpeg")
if ffmpeg_path is None:
    raise EnvironmentError("ffmpeg not found. Please install ffmpeg and ensure it's in your system PATH.")

# Load a SpeechBrain pretrained ASR model
asr = EncoderDecoderASR.from_hparams(
    source="speechbrain/asr-crdnn-rnnlm-librispeech",
    savedir="pretrained_models/asr-crdnn-rnnlm-librispeech",
)

# path to the audio
audio_path = "audio-wav-16khz_1002976_normalized.wav"

# Transcription using SpeechBrain
transcription = asr.transcribe_file(audio_path)

print("Texte transcrit :")
print(transcription)
