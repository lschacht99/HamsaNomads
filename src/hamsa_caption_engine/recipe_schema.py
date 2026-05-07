from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

STYLE_ALIASES = {
    "game": "game",
    "quest": "game",
    "paris": "paris-tip",
    "tip": "paris-tip",
    "clean": "hamsa-clean",
    "wrong": "wrong-vs-right",
    "right": "wrong-vs-right",
    "wrong/right": "wrong-vs-right",
    "wrong-vs-right": "wrong-vs-right",
    "dialogue": "video-game-dialogue",
    "story": "video-game-dialogue",
}


@dataclass
class IntroCardRecipe:
    enabled: bool = False
    title: str = ""
    label: str = "JEWISH TRAVEL NOTE"
    duration_seconds: float = 1.5


@dataclass
class CaptionRecipe:
    start: float
    end: float
    text: str


@dataclass
class OverlayRecipe:
    start: float
    end: float
    text: str
    kind: str = "note"


@dataclass
class ZoomRecipe:
    start: float
    end: float
    scale: float = 1.04
    anchor: str = "center"


@dataclass
class ScreenshotRecipe:
    timestamp: str
    label: str = ""


@dataclass
class ThumbnailRecipe:
    timestamp: str = "00:00:01"
    title: str = ""


@dataclass
class CTARecipe:
    text: str = "Follow Hamsa Nomads for more Jewish travel notes."
    start: float | None = None


@dataclass
class OutputSettingsRecipe:
    width: int = 1080
    height: int = 1920
    video_name: str = "captioned_vertical.mp4"
    thumbnail_name: str = "thumbnail.jpg"
    duration_seconds: float = 30.0


@dataclass
class EditRecipe:
    project_title: str = "Hamsa Nomads Edit"
    video_goal: str = "Create a warm, branded Jewish travel note."
    style: str = "hamsa-clean"
    tone: str = "warm, human, documentary, grounded"
    brand: str = "hamsa"
    renderer: str = "ffmpeg"
    intro_card: IntroCardRecipe = field(default_factory=IntroCardRecipe)
    captions: list[CaptionRecipe] = field(default_factory=list)
    overlays: list[OverlayRecipe] = field(default_factory=list)
    keyword_highlights: list[str] = field(default_factory=list)
    zooms: list[ZoomRecipe] = field(default_factory=list)
    screenshots: list[ScreenshotRecipe] = field(default_factory=list)
    thumbnail: ThumbnailRecipe = field(default_factory=ThumbnailRecipe)
    cta: CTARecipe = field(default_factory=CTARecipe)
    output_settings: OutputSettingsRecipe = field(default_factory=OutputSettingsRecipe)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _coerce_dataclass(cls, value: dict[str, Any] | None):
    return cls(**(value or {}))


def recipe_from_dict(data: dict[str, Any]) -> EditRecipe:
    return EditRecipe(
        project_title=data.get("project_title", "Hamsa Nomads Edit"),
        video_goal=data.get("video_goal", "Create a warm, branded Jewish travel note."),
        style=data.get("style", "hamsa-clean"),
        tone=data.get("tone", "warm, human, documentary, grounded"),
        brand=data.get("brand", "hamsa"),
        renderer=data.get("renderer", "ffmpeg"),
        intro_card=_coerce_dataclass(IntroCardRecipe, data.get("intro_card")),
        captions=[CaptionRecipe(**item) for item in data.get("captions", [])],
        overlays=[OverlayRecipe(**item) for item in data.get("overlays", [])],
        keyword_highlights=list(data.get("keyword_highlights", [])),
        zooms=[ZoomRecipe(**item) for item in data.get("zooms", [])],
        screenshots=[ScreenshotRecipe(**item) for item in data.get("screenshots", [])],
        thumbnail=_coerce_dataclass(ThumbnailRecipe, data.get("thumbnail")),
        cta=_coerce_dataclass(CTARecipe, data.get("cta")),
        output_settings=_coerce_dataclass(OutputSettingsRecipe, data.get("output_settings")),
    )


def load_recipe(path: Path) -> EditRecipe:
    return recipe_from_dict(json.loads(path.read_text(encoding="utf-8")))


def save_recipe(recipe: EditRecipe, path: Path) -> None:
    path.write_text(json.dumps(recipe.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")


def detect_style(prompt: str, fallback: str = "hamsa-clean") -> str:
    lower = prompt.lower()
    if "wrong-vs-right" in lower or "wrong vs right" in lower or "wrong/right" in lower:
        return "wrong-vs-right"
    if "dialogue" in lower or "storytime" in lower or "story time" in lower:
        return "video-game-dialogue"
    if "game" in lower or "quest" in lower or "unlocked" in lower:
        return "game"
    if "paris" in lower or "france" in lower or "tip" in lower:
        return "paris-tip"
    if "clean" in lower or "documentary" in lower:
        return "hamsa-clean"
    return fallback


def detect_keywords(prompt: str) -> list[str]:
    lower = prompt.lower()
    candidates = [
        "Paris",
        "France",
        "game",
        "quest",
        "wrong/right",
        "luxury",
        "retreat",
        "storytime",
        "kosher",
        "croissants",
        "Chamour",
    ]
    return [word for word in candidates if word.lower() in lower]


def intro_title_from_prompt(prompt: str, style: str) -> str:
    cleaned = prompt.strip().rstrip(".")
    if len(cleaned) <= 56:
        return cleaned or "Jewish travel note"
    if style == "wrong-vs-right":
        return "Stop saying this abroad"
    if style == "game":
        return "Quest unlocked"
    if style == "paris-tip":
        return "Paris tip"
    return "Jewish travel note"


def cta_from_keywords(keywords: list[str], style: str) -> str:
    if "Paris" in keywords or "France" in keywords:
        return "Follow Hamsa Nomads for more Jewish travel notes in France."
    if "retreat" in [item.lower() for item in keywords] or style == "hamsa-clean":
        return "Follow Hamsa Nomads for grounded Jewish travel inspiration."
    if style == "game":
        return "Follow Hamsa Nomads for the next travel quest."
    return "Follow Hamsa Nomads for more Jewish travel notes."


def draft_recipe_from_prompt(
    prompt: str,
    *,
    fallback_style: str = "hamsa-clean",
    brand: str = "hamsa",
    intro_title: str | None = None,
) -> EditRecipe:
    style = detect_style(prompt, fallback=fallback_style)
    keywords = detect_keywords(prompt)
    title = intro_title or intro_title_from_prompt(prompt, style)
    tone_bits = ["warm", "human", "Jewish travel"]
    lower = prompt.lower()
    if "funny" in lower:
        tone_bits.append("funny")
    if "luxury" in lower or "retreat" in lower:
        tone_bits.extend(["premium", "calm"])
    if "story" in lower:
        tone_bits.append("story-driven")

    return EditRecipe(
        project_title=title,
        video_goal=prompt or "Create a warm, branded Jewish travel note.",
        style=style,
        tone=", ".join(dict.fromkeys(tone_bits)),
        brand=brand,
        renderer="ffmpeg",
        intro_card=IntroCardRecipe(enabled=bool(title), title=title),
        overlays=[],
        keyword_highlights=keywords,
        zooms=[ZoomRecipe(start=0.0, end=2.0, scale=1.03)] if "luxury" in lower or "retreat" in lower else [],
        screenshots=[ScreenshotRecipe(timestamp="00:00:01", label="thumbnail moment")],
        thumbnail=ThumbnailRecipe(timestamp="00:00:01", title=title),
        cta=CTARecipe(text=cta_from_keywords(keywords, style)),
        output_settings=OutputSettingsRecipe(),
    )
