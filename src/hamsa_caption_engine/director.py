from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .autocut import build_cut_plan
from .content_analysis import analyze_project_content, analysis_summary, save_content_analysis
from .edit_decision import build_edit_decision_list
from .keyframes import extract_keyframes
from .paths import ROOT
from .preprocess import normalize_videos
from .recipe_builder import recipe_from_director_plan
from .scene_detect import detect_scenes
from .transcription import save_transcript, transcribe_with_whisper


def _load_brand_rules() -> dict[str, Any]:
    path = ROOT / "brand" / "hamsa_nomads_brand.json"
    if not path.exists():
        return {"brand": "hamsa_nomads"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"brand": "hamsa_nomads"}


def _combined_transcript(inventory: list[dict[str, Any]], *, timeout: int = 600) -> dict[str, Any]:
    combined_segments: list[dict[str, Any]] = []
    texts: list[str] = []
    offset = 0.0
    warnings: list[str] = []
    for item in inventory:
        try:
            data = transcribe_with_whisper(item["audio"])
        except RuntimeError as exc:
            data = {"mode": "fallback", "segments": [], "text": ""}
            warnings.append(f"{item['clip_id']}: {exc}")
        for segment in data.get("segments", []):
            shifted = dict(segment)
            shifted["clip_id"] = item["clip_id"]
            shifted["source_start"] = segment.get("start", 0.0)
            shifted["source_end"] = segment.get("end", 0.0)
            shifted["start"] = round(float(segment.get("start", 0.0)) + offset, 2)
            shifted["end"] = round(float(segment.get("end", 0.0)) + offset, 2)
            combined_segments.append(shifted)
        texts.append(data.get("text", ""))
        clip_duration = max((float(seg.get("end", 0.0)) for seg in data.get("segments", [])), default=0.0)
        offset += max(clip_duration, 0.1)
    return {"mode": "auto_multi_clip", "segments": combined_segments, "text": " ".join(t for t in texts if t).strip(), "warnings": warnings}


def analyze_project(
    video_paths: list[str | Path],
    output_dir: str | Path,
    *,
    prompt: str = "",
    renderer: str = "ffmpeg",
    auto_cut: bool = True,
    visual_ai: str = "none",
    style: str = "hamsa-clean",
    progress: Any | None = None,
) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    if progress:
        progress("Normalizing video")
    inventory = normalize_videos(video_paths, out)
    if progress:
        progress("Transcribing")
    transcript = _combined_transcript(inventory)
    save_transcript(transcript, out / "transcript.json")
    if progress:
        progress("Detecting scenes")
    scene_map = detect_scenes(inventory, out)
    if progress:
        progress("Extracting keyframes")
    keyframes_manifest = extract_keyframes(scene_map, out, frames_per_scene=1)
    if progress:
        progress("Running visual analysis")
    from .visual_ai import analyze_keyframes
    visual_analysis, visual_warning = analyze_keyframes(keyframes_manifest, out, mode=visual_ai, prompt=prompt)
    if progress:
        progress("Building edit plan")
    cut_plan = build_cut_plan(inventory, out, enabled=auto_cut)
    content_analysis = analyze_project_content(transcript, scene_map, keyframes_manifest, visual_analysis, prompt=prompt, brand_rules=_load_brand_rules())
    content_analysis["recommended_renderer"] = renderer or content_analysis.get("recommended_renderer", "ffmpeg")
    content_analysis["requested_style"] = style
    if visual_warning:
        content_analysis.setdefault("warnings", []).append(visual_warning)
    save_content_analysis(content_analysis, out / "content_analysis.json")
    edl = build_edit_decision_list(content_analysis, cut_plan, scene_map, out)
    recipe = recipe_from_director_plan(content_analysis, edl, transcript=transcript, prompt=prompt, renderer=renderer, style=style)
    from .recipe_schema import save_recipe
    recipe_path = save_recipe(recipe, out / "edit_recipe.json")
    if progress:
        progress("Recipe ready")
    return {
        "inventory": inventory,
        "transcript": transcript,
        "scene_map": scene_map,
        "keyframes_manifest": keyframes_manifest,
        "visual_analysis": visual_analysis,
        "content_analysis": content_analysis,
        "edit_decision_list": edl,
        "recipe": recipe,
        "recipe_path": recipe_path,
        "summary": analysis_summary(content_analysis),
    }
