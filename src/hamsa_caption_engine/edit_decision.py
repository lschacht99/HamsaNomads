from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_edit_decision_list(
    content_analysis: dict[str, Any],
    cut_plan: list[dict[str, Any]],
    scene_map: list[dict[str, Any]],
    output_dir: str | Path,
) -> dict[str, Any]:
    timeline: list[dict[str, Any]] = []
    selected = cut_plan or [
        {"clip_id": scene.get("parent_clip_id", scene["clip_id"]), "source": scene["source_video"], "source_start_sec": scene["start_sec"], "source_end_sec": scene["end_sec"], "timeline_start_sec": 0.0, "timeline_end_sec": scene["duration_sec"], "reason": "scene fallback"}
        for scene in scene_map[:6]
    ]
    for item in selected[:12]:
        timeline.append({"type": "video_clip", **item})
    for overlay in content_analysis.get("recommended_overlays", []):
        start = float(overlay.get("start_sec", 2.0))
        duration = float(overlay.get("duration_sec", 2.5))
        timeline.append({"type": "overlay", "overlay_type": overlay.get("type", "caption"), "start_sec": start, "end_sec": start + duration, **overlay, "reason": overlay.get("reason", "content-aware transcript/visual match")})
    transitions = []
    for index, clip in enumerate([entry for entry in timeline if entry.get("type") == "video_clip"][1:], start=1):
        transition_type = "quick_fade" if content_analysis.get("renderer", "ffmpeg") == "ffmpeg" else "route_line_wipe"
        transitions.append({"type": transition_type, "start_sec": max(0.0, float(clip.get("timeline_start_sec", 0.0)) - 0.15), "duration_sec": 0.3, "reason": "moving between selected content moments"})
    edl = {"timeline": timeline, "transitions": transitions, "clip_count": len([entry for entry in timeline if entry.get("type") == "video_clip"]), "summary": content_analysis.get("summary", "Content-aware edit plan")}
    Path(output_dir).joinpath("edit_decision_list.json").write_text(json.dumps(edl, indent=2, ensure_ascii=False), encoding="utf-8")
    return edl
