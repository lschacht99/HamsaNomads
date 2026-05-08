from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

PLACE_WORDS = ["Paris", "France", "Vermont", "New York", "Montreal", "Jerusalem", "Brooklyn", "Miami", "Israel", "London"]
JEWISH_TERMS = ["kosher", "Shabbos", "Shabbat", "Shavuos", "chamour", "Cholov Yisroel", "minyan", "challah", "mikvah", "Eruv", "Jewish"]
CONTENT_KEYWORDS = [
    "retreat", "villa", "house", "tour", "workshop", "wood", "artisan", "follow my day",
    "passport", "stamp", "quest", "mission", "level", "story", "funny", "tip", "mistake",
]
WRONG_MARKERS = ["wrong", "right", "don't say", "dont say", "instead", "mistake", "cholov yisroel", "chamour"]


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    return [part.strip(" \t\r\n.,") for part in parts if part.strip()]


def _contains(text: str, words: list[str]) -> list[str]:
    lower = text.lower()
    return [word for word in words if word.lower() in lower]


def _unique(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _hook_from_text(text: str, places: list[str], jewish_terms: list[str]) -> str:
    sentences = _sentences(text)
    if "cholov yisroel" in text.lower() and "chamour" in text.lower():
        return "Stop saying this in France" if ("France" in places or "Paris" in places) else "Stop saying the wrong word"
    if "Vermont" in places and "Shavuos" in jewish_terms:
        return "A different kind of Shavuos"
    if any(term.lower() in text.lower() for term in ["follow my day", "workshop", "wood", "artisan"]):
        return "From the workshop"
    if sentences:
        words = sentences[0].split()
        return " ".join(words[:10]).strip() or "Hamsa Nomads travel note"
    return "Hamsa Nomads travel note"


def _content_type(text: str, places: list[str], jewish_terms: list[str]) -> str:
    lower = text.lower()
    if any(word in lower for word in ["quest", "mission", "level", "rpg"]):
        return "video game quest"
    if any(word in lower for word in ["passport", "stamp", "travel note"]):
        return "passport stamp travel note"
    if any(word in lower for word in ["retreat", "shavuos", "villa"]) and ("Vermont" in places or "Shavuos" in jewish_terms):
        return "retreat ad"
    if any(word in lower for word in ["house tour", "villa", "luxury house"]):
        return "luxury house tour"
    if any(word in lower for word in ["follow my day", "behind the scenes", "workshop", "wood", "artisan"]):
        return "behind the scenes"
    if any(word in lower for word in ["funny", "mistake", "wrong", "instead"]):
        return "funny explainer"
    if any(place in places for place in ["Paris", "France", "Montreal", "New York"]) or "kosher" in [t.lower() for t in jewish_terms]:
        return "travel tip"
    if any(word in lower for word in ["story", "storytime"]):
        return "storytime"
    return "travel tip"


def _recommended_style(content_type: str, text: str, places: list[str], jewish_terms: list[str]) -> str:
    lower = text.lower()
    if "video game" in content_type:
        return "video_game_dialogue"
    if content_type in {"retreat ad", "luxury house tour"}:
        return "retreat_luxury"
    if content_type == "behind the scenes":
        return "behind_the_scenes"
    if content_type == "passport stamp travel note":
        return "passport_stamp"
    if "Paris" in places or "France" in places or "chamour" in [t.lower() for t in jewish_terms] or "croissant" in lower:
        return "paris-tip"
    if any(marker in lower for marker in WRONG_MARKERS):
        return "wrong-vs-right"
    return "hamsa-clean"


def analyze_transcript(transcript: dict[str, Any] | str) -> dict[str, Any]:
    if isinstance(transcript, dict):
        text = transcript.get("text") or " ".join(segment.get("text", "") for segment in transcript.get("segments", []))
        segments = transcript.get("segments", [])
    else:
        text = transcript
        segments = []
    places = _unique(_contains(text, PLACE_WORDS))
    jewish_terms = _unique(_contains(text, JEWISH_TERMS))
    keywords = _unique(_contains(text, CONTENT_KEYWORDS) + places + jewish_terms)
    hook = _hook_from_text(text, places, jewish_terms)
    content_type = _content_type(text, places, jewish_terms)
    recommended_style = _recommended_style(content_type, text, places, jewish_terms)
    lower = text.lower()

    overlays: list[dict[str, Any]] = []
    if "cholov yisroel" in lower and "chamour" in lower:
        overlays.append({"type": "wrong_vs_right", "wrong": "Don’t ask: Cholov Yisroel", "right": "Ask: chamour", "start_sec": 2.5, "duration_sec": 3.5})
    elif any(marker in lower for marker in WRONG_MARKERS):
        overlays.append({"type": "wrong_vs_right", "wrong": "Don’t say it that way", "right": "Use the local phrase", "start_sec": 2.5, "duration_sec": 3.0})
    if places and content_type in {"travel tip", "passport stamp travel note", "funny explainer"}:
        overlays.append({"type": "passport_stamp", "text": places[0].upper(), "start_sec": 4.0, "duration_sec": 1.0})

    if content_type == "retreat ad":
        cta = "Join the Hamsa Nomads retreat"
    elif "France" in places or "Paris" in places:
        cta = "Follow Hamsa Nomads for Jewish travel tips in France"
    elif content_type == "behind the scenes":
        cta = "Follow Hamsa Nomads for more behind-the-scenes travel stories"
    else:
        cta = "Follow Hamsa Nomads for Jewish travel tips"

    caption_keywords = _unique((places + jewish_terms + keywords)[:8])
    if not caption_keywords and hook:
        caption_keywords = hook.split()[:4]

    main_topic = content_type.replace("_", " ").title()
    if places:
        main_topic = f"{main_topic} in {places[0]}"
    elif jewish_terms:
        main_topic = f"{main_topic}: {jewish_terms[0]}"

    return {
        "main_topic": main_topic,
        "hook": hook,
        "keywords": keywords,
        "places": places,
        "jewish_terms": jewish_terms,
        "wrong_vs_right_moments": [o for o in overlays if o.get("type") == "wrong_vs_right"],
        "numbered_tips": re.findall(r"\b(?:tip|number)\s+(one|two|three|four|five|\d+)\b", lower),
        "funny_moments": [sentence for sentence in _sentences(text) if any(word in sentence.lower() for word in ["funny", "mistake", "oops", "wrong"])][:3],
        "cta_opportunity": bool(cta),
        "emotional_tone": "premium, warm, human" if recommended_style != "video_game_dialogue" else "playful, premium, travel quest",
        "content_type": content_type,
        "recommended_style": recommended_style,
        "recommended_renderer": "remotion" if content_type in {"retreat ad", "luxury house tour", "video game quest", "passport stamp travel note"} else "ffmpeg",
        "recommended_intro": hook,
        "recommended_overlays": overlays,
        "recommended_cta": cta,
        "caption_keywords": caption_keywords,
        "transcript_length": len(text),
        "caption_segment_count": len(segments),
    }


def save_content_analysis(analysis: dict[str, Any], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")
    return target


def analysis_summary(analysis: dict[str, Any]) -> str:
    overlays = analysis.get("recommended_overlays", [])
    return "\n".join([
        "Video analyzed:",
        f"- Topic: {analysis.get('main_topic', 'Unknown')}",
        f"- Hook: {analysis.get('hook', '')}",
        f"- Style: {analysis.get('recommended_style', 'hamsa-clean')}",
        f"- Suggested overlays: {', '.join(o.get('type', 'overlay') for o in overlays) if overlays else 'none'}",
        f"- Keywords: {', '.join(analysis.get('caption_keywords', [])) or 'none'}",
        f"- CTA: {analysis.get('recommended_cta', '')}",
    ])


def analyze_project_content(
    transcript: dict[str, Any],
    scene_map: list[dict[str, Any]],
    keyframes_manifest: list[dict[str, Any]],
    visual_analysis: list[dict[str, Any]],
    *,
    prompt: str = "",
    brand_rules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Combine transcript, scene, keyframe, visual, prompt, and brand context into edit intent."""
    base = analyze_transcript(transcript)
    text = f"{transcript.get('text', '')} {prompt}".strip()
    lower = text.lower()
    visual_types = [item.get("visual_type", "unknown") for item in visual_analysis]
    visual_text = " ".join(visual_types).lower()

    video_type = "talking_head_tip"
    style = base.get("recommended_style", "hamsa-clean")
    if "cholov yisroel" in lower and "chamour" in lower:
        video_type = "paris_travel_tip"
        style = "paris-tip"
        base["hook"] = "Stop saying this in France"
        base["recommended_overlays"] = [{"type": "wrong_vs_right", "start_sec": 2.5, "duration_sec": 3.5, "wrong": "Cholov Yisroel", "right": "chamour", "reason": "detected Cholov Yisroel/chamour correction"}]
        base["recommended_cta"] = "Follow Hamsa Nomads for Jewish travel tips in France"
        base["best_thumbnail_idea"] = "Stop saying this in France"
    elif ("house" in visual_text or "pool" in visual_text or "landscape" in visual_text) and ("vermont" in lower or "shavuos" in lower or "retreat" in lower):
        video_type = "retreat_ad"
        style = "retreat_luxury"
        base["recommended_overlays"] = [{"type": "lower_third", "start_sec": 2.0, "duration_sec": 2.5, "text": "weekend rhythm", "reason": "visual property/retreat context"}]
        base["recommended_cta"] = "Join the Hamsa Nomads retreat"
        base["best_thumbnail_idea"] = "A different kind of Shavuos"
    elif "workshop" in visual_text or any(word in lower for word in ["workshop", "wood", "artisan", "craft"]):
        video_type = "behind_the_scenes"
        style = "documentary_note"
        base["recommended_overlays"] = [{"type": "lower_third", "start_sec": 1.5, "duration_sec": 2.5, "text": "from the workshop", "reason": "workshop/artisan visual context"}]
        base["recommended_cta"] = "Follow the build"
        base["best_thumbnail_idea"] = "From the workshop"
    elif "quest" in lower or "video game" in lower:
        video_type = "video_game_quest"
        style = "video_game_dialogue"
    elif "passport" in lower or "stamp" in lower or "travel" in visual_text:
        video_type = "passport_stamp_note"
        style = "passport_stamp"
    elif "montage" in lower or len(scene_map) > 4:
        video_type = "montage"

    if any(word in lower for word in ["premium", "smooth", "cinematic", "elegant"]):
        renderer = "remotion"
        transition_style = "soft_zoom_transition"
    else:
        renderer = base.get("recommended_renderer", "ffmpeg")
        transition_style = "quick_fade"
    if any(word in lower for word in ["make it faster", "punchy", "reel style", "cut the pauses"]):
        transition_style = "hard_cut"

    selected_clips = len(scene_map) or len({scene.get("parent_clip_id") for scene in scene_map})
    analysis = {
        **base,
        "main_topic": base.get("main_topic", "Hamsa Nomads Edit"),
        "strongest_hook": base.get("hook", "Hamsa Nomads travel note"),
        "video_type": video_type,
        "tone": base.get("emotional_tone", "premium, warm, human"),
        "locations": base.get("places", []),
        "important_keywords": base.get("caption_keywords", []),
        "emotional_moments": [item for item in visual_analysis if item.get("mood") in {"warm", "funny", "premium"}][:3],
        "best_thumbnail_idea": base.get("best_thumbnail_idea", base.get("hook", "Jewish travel note")),
        "recommended_style": style,
        "recommended_renderer": renderer,
        "transition_style": transition_style,
        "visual_summary": {"types": visual_types, "keyframes": len(keyframes_manifest)},
        "selected_clip_count": selected_clips,
        "brand": (brand_rules or {}).get("brand", "hamsa_nomads") if isinstance(brand_rules, dict) else "hamsa_nomads",
        "summary": f"{video_type} built from transcript, {len(scene_map)} scenes, {len(keyframes_manifest)} keyframes, and prompt guidance.",
    }
    return analysis
