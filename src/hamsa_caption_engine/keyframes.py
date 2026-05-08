from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from .paths import find_ffmpeg


def extract_keyframes(scene_map: list[dict[str, Any]], output_dir: str | Path, *, frames_per_scene: int = 1) -> list[dict[str, Any]]:
    ffmpeg = find_ffmpeg()
    out = Path(output_dir)
    keyframe_dir = out / "keyframes"
    keyframe_dir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, Any]] = []
    if not ffmpeg:
        (out / "keyframes_manifest.json").write_text("[]", encoding="utf-8")
        return manifest
    for scene in scene_map:
        start = float(scene.get("start_sec", 0.0))
        end = float(scene.get("end_sec", start + 1.0))
        duration = max(0.1, end - start)
        timestamps = [start, start + min(1.5, duration / 2), max(start, end - 0.2)] if frames_per_scene >= 3 else [start + min(1.5, duration / 2)]
        for idx, timestamp in enumerate(timestamps[:frames_per_scene], start=1):
            frame_path = keyframe_dir / f"{scene['clip_id']}_frame_{idx:03d}.jpg"
            proc = subprocess.run([ffmpeg, "-y", "-ss", f"{timestamp:.2f}", "-i", str(scene["source_video"]), "-frames:v", "1", "-q:v", "3", str(frame_path)], capture_output=True, text=True)
            if proc.returncode == 0 and frame_path.exists():
                manifest.append({"scene_id": scene["clip_id"], "source_video": scene["source_video"], "timestamp_sec": round(timestamp, 2), "frame": str(frame_path), "purpose": "hook" if abs(timestamp - 1.5) < 0.3 else "scene_reference"})
    if manifest:
        first = manifest[0].copy(); first["purpose"] = "first_frame"; manifest.append(first)
        best = max(manifest, key=lambda item: item.get("timestamp_sec", 0)); best = best.copy(); best["purpose"] = "thumbnail_candidate"; manifest.append(best)
    (out / "keyframes_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest
