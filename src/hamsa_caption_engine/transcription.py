from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MISSING_WHISPER_MESSAGE = "Automatic transcription is not installed.\nRun install_windows.bat and choose Whisper install, or run:\n.venv\\Scripts\\python.exe -m pip install -e \".[whisper]\""


def faster_whisper_available() -> bool:
    try:
        import faster_whisper  # noqa: F401
        return True
    except ImportError:
        return False


def segments_from_transcript_text(text: str, *, words_per_caption: int = 6) -> list[dict[str, Any]]:
    words = [w for w in text.replace("\n", " ").split(" ") if w.strip()]
    if not words:
        words = ["Follow", "Hamsa", "Nomads", "for", "Jewish", "travel", "tips"]
    segments: list[dict[str, Any]] = []
    cursor = 0.0
    for index in range(0, len(words), words_per_caption):
        chunk = words[index:index + words_per_caption]
        duration = max(1.2, min(3.0, len(chunk) * 0.42))
        segments.append({"start": round(cursor, 2), "end": round(cursor + duration, 2), "text": " ".join(chunk)})
        cursor += duration
    return segments


def transcribe_with_whisper(video_path: str | Path, *, model: str = "base", language: str = "auto") -> dict[str, Any]:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError(MISSING_WHISPER_MESSAGE) from exc
    whisper = WhisperModel(model, device="cpu", compute_type="int8")
    kwargs: dict[str, Any] = {"vad_filter": True}
    if language and language != "auto":
        kwargs["language"] = language
    segments_iter, info = whisper.transcribe(str(video_path), **kwargs)
    segments = [{"start": float(s.start), "end": float(s.end), "text": s.text.strip()} for s in segments_iter]
    return {
        "mode": "auto",
        "model": model,
        "language": getattr(info, "language", language),
        "duration": getattr(info, "duration", None),
        "segments": segments,
        "text": " ".join(segment["text"] for segment in segments).strip(),
    }


def load_manual_transcript(path: str | Path) -> dict[str, Any]:
    text = Path(path).read_text(encoding="utf-8")
    return {"mode": "manual", "segments": segments_from_transcript_text(text), "text": text.strip()}


def save_transcript(data: dict[str, Any], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return target
