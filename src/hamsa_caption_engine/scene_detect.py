from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from .paths import find_executable


def _duration(path: Path) -> float:
    ffprobe = find_executable("ffprobe")
    if not ffprobe:
        return 0.0
    proc = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)], capture_output=True, text=True)
    try:
        return float((proc.stdout or "0").strip())
    except ValueError:
        return 0.0


def _classify(path: Path) -> str:
    lower = path.name.lower()
    if any(word in lower for word in ["house", "villa", "property", "pool"]):
        return "broll"
    if any(word in lower for word in ["talk", "interview", "selfie"]):
        return "talking_head"
    return "unknown"


def detect_scenes(inventory: list[dict[str, Any]], output_dir: str | Path) -> list[dict[str, Any]]:
    """Detect scenes with PySceneDetect when available, otherwise save one safe scene per normalized clip."""
    scene_map: list[dict[str, Any]] = []
    try:
        from scenedetect import detect, ContentDetector  # type: ignore
    except Exception:
        detect = None
        ContentDetector = None
    for item in inventory:
        source = Path(item["normalized"])
        scenes: list[tuple[float, float]] = []
        if detect and ContentDetector:
            try:
                for start, end in detect(str(source), ContentDetector()):
                    scenes.append((float(start.get_seconds()), float(end.get_seconds())))
            except Exception:
                scenes = []
        if not scenes:
            duration = _duration(source)
            scenes = [(0.0, duration or 0.0)]
        for index, (start, end) in enumerate(scenes, start=1):
            scene_map.append({
                "clip_id": f"{item['clip_id']}_scene_{index:03d}",
                "parent_clip_id": item["clip_id"],
                "source_video": str(source),
                "start_sec": round(start, 2),
                "end_sec": round(end, 2),
                "duration_sec": round(max(0.0, end - start), 2),
                "type": _classify(source),
            })
    Path(output_dir).joinpath("scene_map.json").write_text(json.dumps(scene_map, indent=2, ensure_ascii=False), encoding="utf-8")
    return scene_map
