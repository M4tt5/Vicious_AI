import whisper
import shutil

def transcribe_audio_to_text(audio_path: str, model_size: str = "base", language: str = "en", fp16: bool = False) -> str:
    """
    Transcribe an audio into a text with Whisper.

    Args:
        audio_path:  Path to the audio file to transcribe
        model_size:  Size of the Whisper model to use (ex: "tiny", "base", "small", "medium", "large")
        language:    Language of the audio (ex: "en" for English)
        fp16:        Whether to use half-precision (fp16) for faster inference on compatible hardware. Default is False.

    Returns:
        The transcribed text

    Requires:
        pip install torch openai-whisper
        ffmpeg installed and in system PATH
        numpy 2.2.3 (not 2.2.4)
    """
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path is None:
        raise EnvironmentError("ffmpeg not found. Please install ffmpeg and ensure it's in your system PATH.")

    model = whisper.load_model(model_size)

    result = model.transcribe(audio_path, language=language, fp16=fp16)

    return result["text"]


if __name__ == "__main__":
    text = transcribe_audio("audio-wav-16khz_1002976_normalized_noise.wav")
    print("Texte transcrit :")
    print(text)