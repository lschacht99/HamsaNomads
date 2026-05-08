from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from .paths import find_ffmpeg

SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v"}


def is_supported_video(path: str | Path) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS


def _run(cmd: list[str], *, timeout: int = 600) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def normalize_videos(video_paths: list[str | Path], output_dir: str | Path, *, timeout: int = 600) -> list[dict[str, Any]]:
    """Normalize user videos to browser/FFmpeg friendly MP4s without touching originals."""
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("FFmpeg missing. Cannot normalize videos.")
    out = Path(output_dir)
    normalized_dir = out / "normalized"
    normalized_dir.mkdir(parents=True, exist_ok=True)
    inventory: list[dict[str, Any]] = []
    clip_number = 1
    for raw in video_paths:
        source = Path(raw)
        if not is_supported_video(source):
            continue
        clip_id = f"clip_{clip_number:03d}"
        normalized = normalized_dir / f"{clip_id}.mp4"
        audio = normalized_dir / f"{clip_id}.wav"
        normalize_cmd = [
            ffmpeg,
            "-y",
            "-i",
            str(source),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ar",
            "44100",
            "-ac",
            "2",
            str(normalized),
        ]
        proc = _run(normalize_cmd, timeout=timeout)
        if proc.returncode != 0:
            raise RuntimeError(f"Failed to normalize {source}:\n{proc.stderr or proc.stdout}")
        wav_cmd = [ffmpeg, "-y", "-i", str(normalized), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(audio)]
        wav_proc = _run(wav_cmd, timeout=timeout)
        if wav_proc.returncode != 0:
            raise RuntimeError(f"Failed to extract WAV for {normalized}:\n{wav_proc.stderr or wav_proc.stdout}")
        inventory.append({"clip_id": clip_id, "source": str(source), "normalized": str(normalized), "audio": str(audio)})
        clip_number += 1
    (out / "session_inventory.json").write_text(json.dumps(inventory, indent=2, ensure_ascii=False), encoding="utf-8")
    return inventory
