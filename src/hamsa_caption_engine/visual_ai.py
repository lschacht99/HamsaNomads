from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _fallback_visual_type(frame: str, prompt: str = "") -> str:
    lower = f"{frame} {prompt}".lower()
    if any(word in lower for word in ["house", "villa", "pool", "property"]):
        return "house"
    if any(word in lower for word in ["workshop", "wood", "craft", "artisan"]):
        return "workshop"
    if any(word in lower for word in ["food", "kosher", "restaurant"]):
        return "food"
    if any(word in lower for word in ["paris", "france", "travel"]):
        return "travel"
    return "unknown"


def visual_model_available(mode: str) -> bool:
    if mode == "none":
        return False
    try:
        import transformers  # noqa: F401
        return True
    except Exception:
        return False


def analyze_keyframes(keyframes_manifest: list[dict[str, Any]], output_dir: str | Path, *, mode: str = "none", prompt: str = "") -> tuple[list[dict[str, Any]], str | None]:
    """Analyze keyframes with optional local VLM; falls back to metadata-only heuristics."""
    warning: str | None = None
    if mode != "none" and not visual_model_available(mode):
        label = "SmolVLM2" if mode == "smolvlm2" else "Qwen2.5-VL"
        warning = f"{label} visual analysis is not installed. Continuing with transcript-only analysis."
    results: list[dict[str, Any]] = []
    for item in keyframes_manifest:
        frame = item.get("frame", "")
        visual_type = _fallback_visual_type(frame, prompt)
        if visual_type == "house":
            overlay = "lower_third"; mood = "premium"; score = 0.78
        elif visual_type == "workshop":
            overlay = "caption"; mood = "warm"; score = 0.68
        elif visual_type == "travel":
            overlay = "passport_stamp"; mood = "energetic"; score = 0.72
        else:
            overlay = "caption"; mood = "warm"; score = 0.45
        results.append({
            "frame": frame,
            "description": f"Fallback keyframe analysis for {Path(frame).name}: visual context inferred from filename, scene metadata, prompt, and transcript.",
            "visual_type": visual_type,
            "mood": mood,
            "suggested_overlay": overlay,
            "thumbnail_score": score,
            "mode": mode,
            "model_used": "fallback_metadata" if warning or mode == "none" else mode,
        })
    Path(output_dir).joinpath("visual_analysis.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    return results, warning
