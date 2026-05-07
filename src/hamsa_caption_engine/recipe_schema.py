from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

DEFAULT_RECIPE: dict[str, Any] = {
    "project_title": "Hamsa Nomads Edit",
    "brand": "hamsa_nomads",
    "renderer": "ffmpeg",
    "output": {"width": 1080, "height": 1920, "fps": 30, "duration_sec": 25, "format": "mp4"},
    "input_video": {"src": "", "crop": "vertical_center_face", "remove_silence": False},
    "style": {"name": "hamsa-clean", "tone": "warm, human, grounded, documentary", "brand_identity": "hamsa_nomads"},
    "logo": {"enabled": True, "position": "top_center", "watermark": False, "path": "assets/brand/hamsa-logo.png"},
    "transcription": {"mode": "auto", "model": "base", "language": "auto"},
    "auto_cut": {
        "enabled": False,
        "silence_threshold_db": -35,
        "min_silence_duration_sec": 0.7,
        "keep_silence_sec": 0.25,
    },
    "intro_card": {
        "enabled": True,
        "duration_sec": 1.8,
        "label": "HAMSA NOMADS",
        "headline": "Jewish travel note",
        "subheadline": "Warm local context for your next trip",
        "motif": "imperfect_route_line",
    },
    "caption_system": {
        "type": "animated_dialogue_box",
        "position": "lower_third",
        "max_words_per_caption": 6,
        "box_style": "parchment",
        "highlight_keywords": [],
        "keyword_highlights": [],
    },
    "overlays": [],
    "motion": {
        "punch_in_on_hook": True,
        "punch_in_on_keywords": True,
        "subtle_zoom_amount": 1.08,
        "caption_pop": True,
        "avoid_cheap_transitions": True,
    },
    "transitions": [],
    "section_cards": [],
    "freeze_frames": [],
    "thumbnail": {"enabled": True, "time_sec": 1.5, "headline": "Jewish travel note", "style": "passport_stamp"},
    "cta": {
        "enabled": True,
        "start_sec": 22,
        "text": "Follow Hamsa Nomads for Jewish travel tips",
        "style": "clean_brand_end",
    },
}

STYLE_ALIASES = {
    "game": "video_game_dialogue",
    "quest": "video_game_dialogue",
    "video-game-dialogue": "video_game_dialogue",
    "video_game_dialogue": "video_game_dialogue",
    "paris": "paris-tip",
    "paris-tip": "paris-tip",
    "clean": "hamsa-clean",
    "hamsa-clean": "hamsa-clean",
    "wrong": "wrong-vs-right",
    "wrong-vs-right": "wrong-vs-right",
    "passport": "passport_stamp",
    "passport-stamp": "passport_stamp",
    "passport_stamp": "passport_stamp",
    "retreat": "retreat_luxury",
    "retreat_luxury": "retreat_luxury",
}


def normalize_style(style: str | None) -> str:
    if not style:
        return "hamsa-clean"
    return STYLE_ALIASES.get(style.strip().lower(), style.strip())


def default_recipe(*, input_video: str = "", renderer: str = "ffmpeg", style: str = "hamsa-clean") -> dict[str, Any]:
    recipe = deepcopy(DEFAULT_RECIPE)
    recipe["renderer"] = renderer
    recipe["input_video"]["src"] = input_video
    recipe["style"]["name"] = normalize_style(style)
    return recipe


def validate_recipe(recipe: dict[str, Any]) -> dict[str, Any]:
    merged = default_recipe()
    for key, value in recipe.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key].update(value)
        else:
            merged[key] = value
    merged["brand"] = "hamsa_nomads"
    merged["style"]["brand_identity"] = "hamsa_nomads"
    merged["style"]["name"] = normalize_style(merged["style"].get("name"))
    if merged["renderer"] not in {"ffmpeg", "remotion"}:
        merged["renderer"] = "ffmpeg"
    return merged


def load_recipe(path: str | Path) -> dict[str, Any]:
    return validate_recipe(json.loads(Path(path).read_text(encoding="utf-8")))


def save_recipe(recipe: dict[str, Any], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(validate_recipe(recipe), indent=2, ensure_ascii=False), encoding="utf-8")
    return target


def recipe_summary(recipe: dict[str, Any]) -> str:
    overlays = recipe.get("overlays", [])
    return "\n".join([
        "Updated recipe:",
        f"- renderer: {recipe.get('renderer', 'ffmpeg')}",
        f"- style: {recipe.get('style', {}).get('name', 'hamsa-clean')}",
        f"- intro: {recipe.get('intro_card', {}).get('headline', '')}",
        f"- overlays: {', '.join(o.get('type', 'overlay') for o in overlays) if overlays else 'none'}",
        f"- CTA: {recipe.get('cta', {}).get('text', '')}",
    ])
