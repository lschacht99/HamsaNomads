from __future__ import annotations

from copy import deepcopy
from typing import Any

from .content_analysis import analyze_transcript
from .recipe_schema import default_recipe, normalize_style, validate_recipe


def _has(prompt: str, *needles: str) -> bool:
    lower = prompt.lower()
    return any(needle in lower for needle in needles)


def _dedupe_overlays(overlays: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    result = []
    for overlay in overlays:
        key = (overlay.get("type"), overlay.get("wrong"), overlay.get("right"), overlay.get("text"), overlay.get("word"), overlay.get("style"), overlay.get("color"))
        if key not in seen:
            seen.add(key)
            result.append(overlay)
    return result


def make_beat_map(hook: str, overlays: list[dict[str, Any]], *, duration: float = 25.0) -> list[dict[str, Any]]:
    beat_map = [
        {"start_sec": 0.0, "end_sec": 2.5, "purpose": "hook", "visual_action": "intro_overlay", "text": hook},
        {"start_sec": 2.5, "end_sec": 6.0, "purpose": "problem", "visual_action": "caption_focus"},
    ]
    cursor = 6.0
    if any(overlay.get("type") == "wrong_vs_right" for overlay in overlays):
        beat_map.append({"start_sec": 6.0, "end_sec": 10.0, "purpose": "solution", "visual_action": "wrong_vs_right"})
        cursor = 10.0
    if any(overlay.get("type") == "passport_stamp" for overlay in overlays):
        beat_map.append({"start_sec": cursor, "end_sec": cursor + 2.0, "purpose": "travel_context", "visual_action": "passport_stamp"})
        cursor += 2.0
    beat_map.append({"start_sec": max(cursor, duration - 3.0), "end_sec": duration, "purpose": "cta", "visual_action": "end_card"})
    return beat_map


def recipe_from_analysis(
    analysis: dict[str, Any],
    *,
    input_video: str = "",
    renderer: str | None = None,
    transcript: dict[str, Any] | None = None,
) -> dict[str, Any]:
    style = normalize_style(analysis.get("recommended_style", "hamsa-clean"))
    chosen_renderer = renderer or analysis.get("recommended_renderer", "ffmpeg")
    recipe = default_recipe(input_video=input_video, renderer=chosen_renderer, style=style)
    hook = analysis.get("hook") or analysis.get("recommended_intro") or "Hamsa Nomads travel note"
    overlays = list(analysis.get("recommended_overlays", []))
    caption_keywords = list(analysis.get("caption_keywords", []))
    keyword_highlights = []
    for term in analysis.get("jewish_terms", []):
        color = "#7B8A6A"
        style_name = "correct"
        if term.lower() == "cholov yisroel":
            color = "#C8886A"
            style_name = "wrong"
        keyword_highlights.append({"word": term, "style": style_name, "color": color})
    for place in analysis.get("places", []):
        keyword_highlights.append({"word": place, "style": "place", "color": "#C8886A"})

    intro_label = "HAMSA NOTE"
    thumbnail = hook
    if style == "paris-tip":
        intro_label = "PARIS TIP"
        if "chamour" in [term.lower() for term in analysis.get("jewish_terms", [])]:
            thumbnail = "Stop saying this in France"
    elif style == "retreat_luxury":
        intro_label = "RETREAT NOTE"
        if "Shavuos" in analysis.get("jewish_terms", []):
            hook = "A different kind of Shavuos"
            thumbnail = hook
    elif style == "behind_the_scenes":
        intro_label = "BEHIND THE SCENES"
        hook = "From the workshop"
        thumbnail = hook
    elif style == "video_game_dialogue":
        intro_label = "QUEST UNLOCKED"
    elif style == "passport_stamp":
        intro_label = "PASSPORT NOTE"

    recipe["project_title"] = analysis.get("main_topic", hook)
    recipe["intro_card"].update(label=intro_label, headline=hook, subheadline=analysis.get("main_topic", "A Hamsa Nomads travel note"), duration_sec=1.5, style="premium_editorial")
    recipe["caption_system"].update(
        type="video_game_dialogue" if style == "video_game_dialogue" else "premium_travel_note",
        position="lower_third",
        max_words_per_caption=6,
        box_style="parchment",
        theme="premium",
        highlight_keywords=caption_keywords,
        keyword_highlights=keyword_highlights,
    )
    recipe["overlays"] = _dedupe_overlays(overlays)
    recipe["cta"].update(enabled=True, text=analysis.get("recommended_cta", "Follow Hamsa Nomads for Jewish travel tips"), style="clean_brand_end")
    recipe["thumbnail"].update(enabled=True, headline=thumbnail, style="passport_stamp")
    recipe["beat_map"] = make_beat_map(hook, recipe["overlays"], duration=float(recipe.get("output", {}).get("duration_sec", 25)))
    recipe["content_analysis"] = analysis
    if transcript:
        recipe["captions"] = transcript.get("segments", [])
    if style == "video_game_dialogue" and not any(o.get("type") == "quest_banner" for o in recipe["overlays"]):
        recipe["overlays"].append({"type": "quest_banner", "start_sec": 1.5, "duration_sec": 2.5, "text": "LOCAL TIP"})
    return validate_recipe(recipe)


def recipe_from_transcript(
    transcript: dict[str, Any] | str,
    *,
    input_video: str = "",
    renderer: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    analysis = analyze_transcript(transcript)
    return recipe_from_analysis(analysis, input_video=input_video, renderer=renderer, transcript=transcript if isinstance(transcript, dict) else None), analysis


def apply_prompt_rules(recipe: dict[str, Any], prompt: str, *, requested_renderer: str | None = None) -> dict[str, Any]:
    new = validate_recipe(deepcopy(recipe))
    lower = prompt.lower().strip()
    if requested_renderer:
        new["renderer"] = requested_renderer

    if _has(lower, "premium", "elegant", "editorial", "luxury", "clean", "beautiful captions", "more aesthetic", "make it prettier", "more beautiful", "polished", "branded", "make captions nicer", "professional captions", "premium captions"):
        new["style"]["name"] = "hamsa-clean"
        new["caption_system"].update(type="premium_travel_note", box_style="parchment", theme="premium")
        new["intro_card"]["style"] = "premium_editorial"
    if _has(lower, "less video game"):
        new["style"]["name"] = "hamsa-clean"
        new["overlays"] = [o for o in new.get("overlays", []) if o.get("type") != "quest_banner"]
    elif _has(lower, "video game", "quest", "rpg", "level", "mission"):
        new["style"]["name"] = "video_game_dialogue"
        new["caption_system"].update(type="video_game_dialogue", box_style="parchment", theme="premium")
        new["intro_card"].update(label="QUEST UNLOCKED", headline=new["intro_card"].get("headline") or "Travel quest", subheadline="A warm travel mission, Hamsa style")
        if not any(o.get("type") == "quest_banner" for o in new.get("overlays", [])):
            new["overlays"].append({"type": "quest_banner", "start_sec": 1.5, "duration_sec": 2.5, "text": "LOCAL TIP"})
    if _has(lower, "paris", "france", "chamour", "croissant", "kosher travel"):
        new["style"]["name"] = "paris-tip"
        new["caption_system"].update(type="premium_travel_note", box_style="parchment", theme="premium")
        new["intro_card"].update(label="PARIS TIP", headline=new["intro_card"].get("headline") or "Ask like a local", subheadline="Kosher travel context, Hamsa style")
        keywords = ["Paris", "kosher", "chamour"]
        new["caption_system"]["highlight_keywords"] = sorted(set(new["caption_system"].get("highlight_keywords", []) + keywords))
        new["caption_system"]["keyword_highlights"] = _dedupe_overlays(new["caption_system"].get("keyword_highlights", []) + [{"word": "Chamour", "style": "correct", "color": "#7B8A6A"}, {"word": "Paris", "style": "place", "color": "#C8886A"}, {"word": "kosher", "style": "keyword", "color": "#7B8A6A"}])
        new["cta"]["text"] = "Follow Hamsa Nomads for Jewish travel tips in France"
    if _has(lower, "wrong/right", "wrong vs right", "wrong-vs-right", "mistake", "don't say", "dont say", "instead"):
        new["style"]["name"] = "wrong-vs-right" if new["style"].get("name") not in {"paris-tip", "video_game_dialogue"} else new["style"]["name"]
        if not any(o.get("type") == "wrong_vs_right" for o in new.get("overlays", [])):
            new["overlays"].append({"type": "wrong_vs_right", "start_sec": 2.5, "duration_sec": 3.5, "wrong": "Don’t ask: Cholov Yisroel", "right": "Ask: chamour"})
        new["caption_system"]["keyword_highlights"] = _dedupe_overlays(new["caption_system"].get("keyword_highlights", []) + [
            {"word": "Cholov Yisroel", "style": "wrong", "color": "#C8886A"},
            {"word": "Chamour", "style": "correct", "color": "#7B8A6A"},
        ])
    if _has(lower, "luxury", "retreat", "house", "villa"):
        new["style"]["name"] = "retreat_luxury"
        new["intro_card"].update(label="RETREAT NOTE", headline=new["intro_card"].get("headline") or "A calmer kind of luxury", subheadline="Warm, grounded, and human")
        new["motion"]["subtle_zoom_amount"] = 1.05
    if _has(lower, "passport", "travel note", "stamp"):
        if not any(o.get("type") == "passport_stamp" for o in new.get("overlays", [])):
            new["overlays"].append({"type": "passport_stamp", "start_sec": 4.0, "duration_sec": 1.0, "text": "HAMSA APPROVED"})
        new["transitions"].append({"type": "passport_stamp_pop", "start_sec": 4.0, "duration_sec": 0.35})
    if _has(lower, "premium animation", "animated", "cinematic title", "designed intro"):
        new["renderer"] = "remotion"
    if _has(lower, "smooth", "cinematic", "animated"):
        new["renderer"] = "remotion"
        new["transitions"].append({"type": "route_line_wipe", "start_sec": 1.5, "duration_sec": 0.35})
    if _has(lower, "make it faster", "cut the pauses", "more dynamic", "make it punchy", "reel style"):
        new["auto_cut"]["enabled"] = True
        new["input_video"]["remove_silence"] = True
        new["motion"].update(punch_in_on_hook=True, punch_in_on_keywords=True, subtle_zoom_amount=1.08)
    if _has(lower, "simple", "fast", "weak pc"):
        new["renderer"] = "ffmpeg"
        new["transitions"] = [{"type": "hard_cut", "start_sec": 0.0, "duration_sec": 0.0}]
    new["overlays"] = _dedupe_overlays(new.get("overlays", []))
    new["beat_map"] = make_beat_map(new.get("intro_card", {}).get("headline", "Hamsa Nomads travel note"), new.get("overlays", []), duration=float(new.get("output", {}).get("duration_sec", 25)))
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


def recipe_from_director_plan(
    content_analysis: dict[str, Any],
    edit_decision_list: dict[str, Any],
    *,
    transcript: dict[str, Any] | None = None,
    prompt: str = "",
    renderer: str | None = None,
    style: str | None = None,
) -> dict[str, Any]:
    """Build the renderer control recipe from content analysis and the EDL, not generic overlays."""
    selected_style = normalize_style(style or content_analysis.get("recommended_style", "hamsa-clean"))
    if style in {None, "hamsa-clean"}:
        selected_style = normalize_style(content_analysis.get("recommended_style", selected_style))
    chosen_renderer = renderer or content_analysis.get("recommended_renderer", "ffmpeg")
    timeline = [entry for entry in edit_decision_list.get("timeline", []) if entry.get("type") == "video_clip"]
    duration = max((float(entry.get("timeline_end_sec", 0.0)) for entry in timeline), default=25.0)
    recipe = default_recipe(input_video=timeline[0]["source"] if timeline else "", renderer=chosen_renderer, style=selected_style)
    overlays = list(content_analysis.get("recommended_overlays", []))
    hook = content_analysis.get("strongest_hook") or content_analysis.get("hook") or content_analysis.get("recommended_intro") or "Hamsa Nomads travel note"
    label_by_type = {
        "paris_travel_tip": "PARIS TIP",
        "retreat_ad": "RETREAT NOTE",
        "behind_the_scenes": "BEHIND THE SCENES",
        "workshop/artisan": "FROM THE WORKSHOP",
        "video_game_quest": "QUEST UNLOCKED",
        "passport_stamp_note": "PASSPORT NOTE",
        "house_tour": "HOUSE TOUR",
        "montage": "HAMSA MOMENTS",
    }
    recipe.update(
        project_title=content_analysis.get("main_topic", hook),
        timeline=timeline,
        edit_decision_list=edit_decision_list,
        content_analysis=content_analysis,
    )
    recipe["output"].update(duration_sec=round(duration or 25.0, 2))
    recipe["auto_cut"]["enabled"] = bool(timeline)
    recipe["input_video"]["remove_silence"] = bool(timeline)
    recipe["intro_card"].update(
        enabled=True,
        label=label_by_type.get(content_analysis.get("video_type"), "HAMSA NOTE"),
        headline=hook,
        subheadline=content_analysis.get("main_topic", "A content-aware Hamsa Nomads edit"),
    )
    recipe["caption_system"].update(
        type="video_game_dialogue" if selected_style == "video_game_dialogue" else "premium_travel_note",
        highlight_keywords=content_analysis.get("important_keywords") or content_analysis.get("caption_keywords", []),
        keyword_highlights=[{"word": term, "style": "keyword", "color": "#7B8A6A"} for term in content_analysis.get("jewish_terms", [])],
    )
    if transcript:
        recipe["captions"] = transcript.get("segments", [])
    recipe["overlays"] = _dedupe_overlays(overlays)
    recipe["transitions"] = edit_decision_list.get("transitions", []) or [{"type": content_analysis.get("transition_style", "quick_fade"), "start_sec": 2.5, "duration_sec": 0.35, "reason": "content-aware transition default"}]
    recipe["beat_map"] = make_beat_map(hook, recipe["overlays"], duration=float(recipe["output"].get("duration_sec", 25.0)))
    recipe["thumbnail"].update(enabled=True, headline=content_analysis.get("best_thumbnail_idea", hook), time_sec=1.5)
    recipe["cta"].update(enabled=bool(content_analysis.get("recommended_cta")), text=content_analysis.get("recommended_cta", "Follow Hamsa Nomads for Jewish travel tips"), start_sec=max(0.0, duration - 3.0))
    if prompt:
        recipe = apply_prompt_rules(recipe, prompt, requested_renderer=chosen_renderer)
        recipe["timeline"] = timeline
        recipe["edit_decision_list"] = edit_decision_list
        recipe["content_analysis"] = content_analysis
    return validate_recipe(recipe)
