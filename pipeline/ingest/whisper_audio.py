import os
from typing import Optional

from config import WHISPER_MODEL

_model_cache: dict = {}


def get_whisper_model(model_size: Optional[str] = None):
    """Load Whisper model once per size (singleton cache).

    Whisper (and its heavy torch dependency) is imported lazily here so that
    PDF / Excel / URL uploads work even when audio support isn't installed.
    """
    try:
        import whisper
    except ImportError as e:
        raise RuntimeError(
            "Audio transcription needs the 'openai-whisper' package (and torch), "
            "which isn't installed. Install it, or use PDF/Excel/URL sources instead."
        ) from e

    size = model_size or WHISPER_MODEL
    if size not in _model_cache:
        print(f"[Whisper] Loading model '{size}'...")
        _model_cache[size] = whisper.load_model(size)
    return _model_cache[size]


def parse_audio(uploaded_file, model_size: Optional[str] = None) -> str:
    """
    Transcribe audio with OpenAI Whisper (local).
    model_size: tiny/base/small/medium/large — defaults to config.WHISPER_MODEL.
    """
    os.makedirs("uploads", exist_ok=True)
    temp_path = os.path.join("uploads", uploaded_file.name)
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    try:
        model = get_whisper_model(model_size)
        result = model.transcribe(temp_path)
        transcript = result.get("text", "").strip()

        # Format with speaker-unknown segments if segments available
        segments = result.get("segments", [])
        if segments:
            lines = []
            for seg in segments:
                text = seg.get("text", "").strip()
                if text:
                    lines.append(f"[Speaker unknown]: {text}")
            if lines:
                transcript = "\n".join(lines)

        os.remove(temp_path)
        return transcript

    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise Exception(f"Failed to transcribe audio {uploaded_file.name}. Error: {str(e)}") from e
