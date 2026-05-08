from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from .paths import find_executable, find_ffmpeg


def _duration(path: Path) -> float:
    ffprobe = find_executable("ffprobe")
    if not ffprobe:
        return 0.0
    proc = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)], capture_output=True, text=True)
    try:
        return float((proc.stdout or "0").strip())
    except ValueError:
        return 0.0


def detect_silences(video_path: str | Path, *, silence_threshold_db: int = -35, min_silence_duration_sec: float = 0.7) -> list[dict[str, float]]:
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        return []
    proc = subprocess.run([ffmpeg, "-hide_banner", "-i", str(video_path), "-af", f"silencedetect=noise={silence_threshold_db}dB:d={min_silence_duration_sec}", "-f", "null", "-"], capture_output=True, text=True)
    silences: list[dict[str, float]] = []
    current: float | None = None
    for line in (proc.stderr or "").splitlines():
        if "silence_start:" in line:
            match = re.search(r"silence_start:\s*([0-9.]+)", line)
            if match:
                current = float(match.group(1))
        elif "silence_end:" in line and current is not None:
            match = re.search(r"silence_end:\s*([0-9.]+)", line)
            if match:
                silences.append({"start": current, "end": float(match.group(1))})
            current = None
    return silences


def build_cut_plan(
    inventory: list[dict[str, Any]],
    output_dir: str | Path,
    *,
    enabled: bool = True,
    silence_threshold_db: int = -35,
    min_silence_duration_sec: float = 0.7,
    keep_silence_sec: float = 0.25,
) -> list[dict[str, Any]]:
    out = Path(output_dir)
    timeline_cursor = 0.0
    plan: list[dict[str, Any]] = []
    for item in inventory:
        source = Path(item["normalized"])
        duration = _duration(source)
        if not enabled or duration <= 0:
            segment_duration = duration or 0.0
            plan.append({"clip_id": item["clip_id"], "source": str(source), "source_start_sec": 0.0, "source_end_sec": round(segment_duration, 2), "timeline_start_sec": round(timeline_cursor, 2), "timeline_end_sec": round(timeline_cursor + segment_duration, 2), "reason": "full clip / auto-cut disabled"})
            timeline_cursor += segment_duration
            continue
        silences = detect_silences(source, silence_threshold_db=silence_threshold_db, min_silence_duration_sec=min_silence_duration_sec)
        cursor = 0.0
        for silence in silences:
            speech_end = max(cursor, silence["start"] + keep_silence_sec)
            if speech_end - cursor >= 0.25:
                seg_len = speech_end - cursor
                plan.append({"clip_id": item["clip_id"], "source": str(source), "source_start_sec": round(cursor, 2), "source_end_sec": round(speech_end, 2), "timeline_start_sec": round(timeline_cursor, 2), "timeline_end_sec": round(timeline_cursor + seg_len, 2), "reason": "speech segment / silence removed"})
                timeline_cursor += seg_len
            cursor = min(duration, silence["end"] - keep_silence_sec)
        if duration - cursor >= 0.25:
            seg_len = duration - cursor
            plan.append({"clip_id": item["clip_id"], "source": str(source), "source_start_sec": round(cursor, 2), "source_end_sec": round(duration, 2), "timeline_start_sec": round(timeline_cursor, 2), "timeline_end_sec": round(timeline_cursor + seg_len, 2), "reason": "speech segment / hook" if not plan else "speech segment"})
            timeline_cursor += seg_len
    (out / "cut_plan.json").write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    return plan
