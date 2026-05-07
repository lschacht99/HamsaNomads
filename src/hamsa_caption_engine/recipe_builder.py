from __future__ import annotations

from copy import deepcopy
from typing import Any

from .recipe_schema import default_recipe, normalize_style, validate_recipe


def _has(prompt: str, *needles: str) -> bool:
    lower = prompt.lower()
    return any(needle in lower for needle in needles)


def apply_prompt_rules(recipe: dict[str, Any], prompt: str, *, requested_renderer: str | None = None) -> dict[str, Any]:
    new = validate_recipe(deepcopy(recipe))
    lower = prompt.lower().strip()
    if requested_renderer:
        new["renderer"] = requested_renderer

    if _has(lower, "make captions nicer", "professional captions", "premium captions"):
        new["style"]["name"] = "hamsa-clean"
        new["caption_system"].update(type="animated_dialogue_box", box_style="parchment")
    if _has(lower, "video game", "quest", "rpg", "level", "mission"):
        new["style"]["name"] = "video_game_dialogue"
        new["caption_system"].update(type="video_game_dialogue", box_style="parchment")
        new["intro_card"].update(label="QUEST UNLOCKED", headline="Paris quest", subheadline="A warm travel mission, Hamsa style")
        new["section_cards"] = [{"title": "PARIS QUEST", "start_sec": 1.5, "duration_sec": 0.8}]
        new["transitions"].append({"type": "game_quest_banner_reveal", "start_sec": 1.5, "duration_sec": 0.35})
    if _has(lower, "paris", "france", "chamour", "croissant"):
        new["style"]["name"] = "paris-tip"
        new["intro_card"].update(label="PARIS NOTE", headline="Ask like a local", subheadline="Chamour, context, and confidence")
        new["caption_system"]["highlight_keywords"] = sorted(set(new["caption_system"].get("highlight_keywords", []) + ["Paris", "France", "chamour"]))
        new["caption_system"]["keyword_highlights"] = [{"word": "Chamour", "style": "correct", "color": "#7B8A6A"}]
        new["cta"]["text"] = "Follow Hamsa Nomads for Jewish travel tips in France"
    if _has(lower, "wrong/right", "wrong vs right", "wrong-vs-right", "mistake", "don't say", "dont say", "instead"):
        new["style"]["name"] = "wrong-vs-right"
        new["overlays"].append({"type": "wrong_vs_right", "start_sec": 2.0, "duration_sec": 3.0, "wrong": "Don’t ask: Cholov Yisroel", "right": "Ask: Chamour"})
        new["caption_system"]["keyword_highlights"] = [
            {"word": "Cholov Yisroel", "style": "wrong", "color": "#C8886A"},
            {"word": "Chamour", "style": "correct", "color": "#7B8A6A"},
        ]
        new["section_cards"].append({"title": "WRONG WORD", "start_sec": 2.0, "duration_sec": 0.7})
    if _has(lower, "luxury", "retreat", "house", "villa"):
        new["style"]["name"] = "retreat_luxury"
        new["intro_card"].update(label="RETREAT NOTE", headline="A calmer kind of luxury", subheadline="Warm, grounded, and human")
        new["motion"]["subtle_zoom_amount"] = 1.05
    if _has(lower, "passport", "travel note", "stamp"):
        new["style"]["name"] = "passport_stamp"
        new["overlays"].append({"type": "passport_stamp", "start_sec": 3.2, "duration_sec": 0.8, "text": "HAMSA APPROVED"})
        new["freeze_frames"].append({"time_sec": 3.2, "duration_sec": 0.5, "overlay": "Passport stamp moment"})
        new["transitions"].append({"type": "passport_stamp_pop", "start_sec": 3.2, "duration_sec": 0.35})
    if _has(lower, "premium animation", "animated", "cinematic title"):
        new["renderer"] = "remotion"
    if _has(lower, "smooth", "cinematic", "premium", "animated"):
        new["renderer"] = "remotion"
        new["transitions"].append({"type": "route_line_wipe", "start_sec": 1.5, "duration_sec": 0.35})
        new["transitions"].append({"type": "parchment_card_slide", "start_sec": 4.0, "duration_sec": 0.35})
    if _has(lower, "make it faster", "cut the pauses", "more dynamic", "make it punchy", "reel style"):
        new["auto_cut"]["enabled"] = True
        new["input_video"]["remove_silence"] = True
        new["motion"].update(punch_in_on_hook=True, punch_in_on_keywords=True, subtle_zoom_amount=1.08)
    if _has(lower, "simple", "fast", "weak pc"):
        new["renderer"] = "ffmpeg"
        new["transitions"] = [{"type": "hard_cut", "start_sec": 0.0, "duration_sec": 0.0}]
    new["brand"] = "hamsa_nomads"
    new["style"]["brand_identity"] = "hamsa_nomads"
    return validate_recipe(new)


def recipe_from_prompt(prompt: str, *, input_video: str = "", renderer: str | None = None, style: str = "hamsa-clean") -> dict[str, Any]:
    base = default_recipe(input_video=input_video, renderer=renderer or "ffmpeg", style=normalize_style(style))
    if prompt.strip():
        base["project_title"] = prompt.strip()[:72]
        base["intro_card"]["headline"] = prompt.strip()[:48]
        base["thumbnail"]["headline"] = prompt.strip()[:40]
    return apply_prompt_rules(base, prompt, requested_renderer=renderer)
