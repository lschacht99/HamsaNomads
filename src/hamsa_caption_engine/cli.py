from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

from .recipe_schema import EditRecipe, draft_recipe_from_prompt, load_recipe, save_recipe

ROOT = Path.cwd()
INPUT_DIR = ROOT / "input"
OUTPUT_DIR = ROOT / "output"
REMOTION_DIR = ROOT / "remotion"
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920


@dataclass
class CaptionSegment:
    start: float
    end: float
    text: str


BRAND_FILE = ROOT / "brand" / "hamsa_nomads_brand.json"
BRAND_FALLBACK = {
    "name": "Hamsa Nomads",
    "colors": {
        "warm_cream": "#F6F2E7",
        "ivory_parchment": "#ECE7DB",
        "sand": "#DCC7A1",
        "clay": "#C8886A",
        "olive_sage": "#7B8A6A",
        "ink_black": "#111111",
    },
    "typography": {
        "headline_serif": {"font": "Playfair Display", "fallbacks": ["Georgia", "Times New Roman", "serif"]},
        "body_sans": {"font": "Montserrat", "fallbacks": ["Arial", "Segoe UI", "sans-serif"]},
        "accent_handwritten": {"font": "Caveat", "fallbacks": ["Comic Sans MS", "Segoe Print", "cursive"]},
    },
    "rules": {
        "personality": ["warm", "human", "Jewish travel network", "documentary", "natural", "connected", "grounded"],
        "visual_signature": "imperfect line",
        "motifs": ["route", "path", "passport", "map"],
        "avoid": ["corporate", "glossy", "neon", "childish", "cheap CapCut effects"],
    },
}


def load_brand_system(brand: str = "hamsa") -> dict:
    if brand != "hamsa":
        raise SystemExit(f"Unsupported brand: {brand}. Only --brand hamsa is available.")
    if BRAND_FILE.exists():
        return json.loads(BRAND_FILE.read_text(encoding="utf-8"))
    return BRAND_FALLBACK


BRAND_SYSTEM = load_brand_system("hamsa")


def brand_font(role: str) -> str:
    typography = BRAND_SYSTEM["typography"][role]
    return str(typography["font"])


def ass_color(hex_color: str, alpha: str = "00") -> str:
    clean = hex_color.lstrip("#")
    red, green, blue = clean[0:2], clean[2:4], clean[4:6]
    return f"&H{alpha}{blue}{green}{red}"


def brand_ass_color(name: str, alpha: str = "00") -> str:
    return ass_color(str(BRAND_SYSTEM["colors"][name]), alpha)


def override_color(ass_colour: str) -> str:
    clean = ass_colour.removeprefix("&H")
    if len(clean) == 8:
        clean = clean[2:]
    return f"&H{clean}&"


CAPTION_STYLES: dict[str, dict[str, str | int]] = {
    "game": {
        "font": brand_font("headline_serif"),
        "fontsize": 70,
        "primary": brand_ass_color("ink_black"),
        "secondary": brand_ass_color("olive_sage"),
        "outline": brand_ass_color("clay"),
        "back": brand_ass_color("warm_cream", "12"),
        "bold": -1,
        "italic": 0,
        "borderstyle": 3,
        "outline_width": 4,
        "shadow": 0,
        "alignment": 2,
        "margin_l": 78,
        "margin_r": 78,
        "margin_v": 238,
        "label": "QUEST UNLOCKED",
        "label_alt": "LOCAL TIP",
        "label_color": brand_ass_color("olive_sage"),
        "accent_color": brand_ass_color("clay"),
    },
    "paris-tip": {
        "font": brand_font("body_sans"),
        "fontsize": 64,
        "primary": brand_ass_color("ink_black"),
        "secondary": brand_ass_color("clay"),
        "outline": brand_ass_color("sand"),
        "back": brand_ass_color("ivory_parchment", "08"),
        "bold": -1,
        "italic": 0,
        "borderstyle": 3,
        "outline_width": 3,
        "shadow": 0,
        "alignment": 2,
        "margin_l": 92,
        "margin_r": 92,
        "margin_v": 310,
        "label": "PARIS TIP",
        "label_color": brand_ass_color("clay"),
        "accent_color": brand_ass_color("sand"),
    },
    "hamsa-clean": {
        "font": brand_font("body_sans"),
        "fontsize": 64,
        "primary": brand_ass_color("ink_black"),
        "secondary": brand_ass_color("olive_sage"),
        "outline": brand_ass_color("olive_sage"),
        "back": brand_ass_color("warm_cream", "06"),
        "bold": -1,
        "italic": 0,
        "borderstyle": 3,
        "outline_width": 2,
        "shadow": 0,
        "alignment": 2,
        "margin_l": 96,
        "margin_r": 96,
        "margin_v": 255,
        "label": "",
        "label_color": brand_ass_color("olive_sage"),
        "accent_color": brand_ass_color("clay"),
    },
    "wrong-vs-right": {
        "font": brand_font("body_sans"),
        "fontsize": 62,
        "primary": brand_ass_color("ink_black"),
        "secondary": brand_ass_color("olive_sage"),
        "outline": brand_ass_color("sand"),
        "back": brand_ass_color("ivory_parchment", "08"),
        "bold": -1,
        "italic": 0,
        "borderstyle": 3,
        "outline_width": 3,
        "shadow": 0,
        "alignment": 2,
        "margin_l": 84,
        "margin_r": 84,
        "margin_v": 250,
        "label": "ASK IT BETTER",
        "wrong_color": brand_ass_color("clay"),
        "right_color": brand_ass_color("olive_sage"),
        "label_color": brand_ass_color("ink_black"),
    },
    "video-game-dialogue": {
        "font": brand_font("body_sans"),
        "fontsize": 58,
        "primary": brand_ass_color("ink_black"),
        "secondary": brand_ass_color("clay"),
        "outline": brand_ass_color("olive_sage"),
        "back": brand_ass_color("warm_cream", "04"),
        "bold": -1,
        "italic": 0,
        "borderstyle": 3,
        "outline_width": 4,
        "shadow": 0,
        "alignment": 2,
        "margin_l": 86,
        "margin_r": 86,
        "margin_v": 170,
        "label": "HAMSA NOMADS",
        "label_color": brand_ass_color("clay"),
        "accent_color": brand_ass_color("olive_sage"),
    },
}

def run(cmd: Sequence[str]) -> None:
    print("$ " + " ".join(str(part) for part in cmd))
    subprocess.run(cmd, check=True)


def require_binary(name: str) -> str:
    local_names = [name, f"{name}.exe"] if not name.lower().endswith(".exe") else [name]
    for local_name in local_names:
        local_path = ROOT / local_name
        if local_path.exists():
            return str(local_path)

    exe = shutil.which(name)
    if not exe:
        raise SystemExit(
            f"Missing required executable: {name}. Put ffmpeg.exe in this project folder, "
            "or install FFmpeg and make sure it is on PATH."
        )
    return exe


def find_single_mp4(input_dir: Path) -> Path:
    videos = sorted(input_dir.glob("*.mp4"))
    if len(videos) != 1:
        raise SystemExit(
            f"Expected exactly one .mp4 in {input_dir}. Found {len(videos)}."
        )
    return videos[0]


def ass_timestamp(seconds: float) -> str:
    seconds = max(0.0, seconds)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - math.floor(seconds)) * 100))
    if centis == 100:
        secs += 1
        centis = 0
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


def escape_ass(text: str) -> str:
    return (
        text.replace("\\", r"\\")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("\n", r"\N")
        .strip()
    )


def ass_tag(**tags: str | int) -> str:
    parts = []
    for key, value in tags.items():
        parts.append(f"\\{key}{value}")
    return "{" + "".join(parts) + "}"


def label_prefix(style: dict[str, str | int], label: str) -> str:
    if not label:
        return ""
    label_color = override_color(str(style.get("label_color", style["secondary"])))
    return f"{ass_tag(fs=34, b=1, c=label_color)}{escape_ass(label)}{ass_tag(r='')}\\N"


def line_with_color(line: str, ass_colour: str) -> str:
    return f"{ass_tag(c=override_color(ass_colour), b=1)}{escape_ass(line)}{ass_tag(r='')}"


def format_caption_text(style_name: str, raw_text: str, segment_index: int) -> str:
    style = CAPTION_STYLES[style_name]
    escaped = escape_ass(raw_text)

    if style_name == "hamsa-clean":
        accent = override_color(str(style["accent_color"]))
        return f"{ass_tag(c=accent, fs=34)}⌁{ass_tag(r='')}\\N{escaped}"

    if style_name == "paris-tip":
        return label_prefix(style, "PARIS TIP") + escaped

    if style_name == "game":
        label = str(style["label_alt"] if segment_index % 2 else style["label"])
        accent = override_color(str(style["accent_color"]))
        return label_prefix(style, label) + f"{ass_tag(c=accent, fs=42)}route note •{ass_tag(r='')}\\N{escaped}"

    if style_name == "wrong-vs-right":
        label = label_prefix(style, str(style["label"]))
        formatted_lines = []
        for line_index, line in enumerate(raw_text.splitlines() or [raw_text]):
            lowered = line.lower()
            if "❌" in line or "wrong" in lowered or "don't" in lowered or "dont" in lowered:
                formatted_lines.append(line_with_color(line, str(style["wrong_color"])))
            elif "✅" in line or "right" in lowered or lowered.startswith("ask:") or " ask:" in lowered:
                formatted_lines.append(line_with_color(line, str(style["right_color"])))
            else:
                colour = str(style["wrong_color"] if line_index == 0 else style["right_color"])
                formatted_lines.append(line_with_color(line, colour))
        return label + r"\N".join(formatted_lines)

    if style_name == "video-game-dialogue":
        label = label_prefix(style, str(style["label"]))
        accent = override_color(str(style["accent_color"]))
        return label + f"{ass_tag(c=accent, fs=34)}— map path —{ass_tag(r='')}\\N{escaped}"

    return escaped


def style_line(style_name: str) -> str:
    style = CAPTION_STYLES[style_name]
    values = [
        "Default",
        style["font"],
        style["fontsize"],
        style["primary"],
        style["secondary"],
        style["outline"],
        style["back"],
        style["bold"],
        style["italic"],
        0,
        0,
        100,
        100,
        0,
        0,
        style["borderstyle"],
        style["outline_width"],
        style["shadow"],
        style["alignment"],
        style["margin_l"],
        style["margin_r"],
        style["margin_v"],
        1,
    ]
    return "Style: " + ",".join(str(value) for value in values)


def write_ass(path: Path, segments: Iterable[CaptionSegment], style_name: str) -> None:
    events = []
    for segment_index, segment in enumerate(segments):
        if not segment.text.strip() or segment.end <= segment.start:
            continue
        text = format_caption_text(style_name, segment.text, segment_index)
        events.append(
            f"Dialogue: 0,{ass_timestamp(segment.start)},{ass_timestamp(segment.end)},Default,,0,0,0,,{text}"
        )

    content = "\n".join(
        [
            "[Script Info]",
            "Title: Hamsa Nomads Captions",
            "ScriptType: v4.00+",
            f"PlayResX: {VIDEO_WIDTH}",
            f"PlayResY: {VIDEO_HEIGHT}",
            "ScaledBorderAndShadow: yes",
            "WrapStyle: 0",
            "YCbCr Matrix: TV.709",
            "",
            "[V4+ Styles]",
            "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding",
            style_line(style_name),
            "",
            "[Events]",
            "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
            *events,
            "",
        ]
    )
    path.write_text(content, encoding="utf-8")


def extract_audio(ffmpeg: str, source: Path, wav_path: Path) -> list[str]:
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(source),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(wav_path),
    ]
    run(cmd)
    return cmd


def transcribe(audio_path: Path, model_size: str, language: str | None) -> list[CaptionSegment]:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise SystemExit(
            "Python package faster-whisper is not installed. Run: pip install -r requirements.txt"
        ) from exc

    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _info = model.transcribe(
        str(audio_path),
        language=language,
        vad_filter=True,
        beam_size=1,
        word_timestamps=False,
    )
    return [
        CaptionSegment(start=float(item.start), end=float(item.end), text=item.text.strip())
        for item in segments
    ]


def transcript_segments(transcript_path: Path) -> list[CaptionSegment]:
    lines = [line.strip() for line in transcript_path.read_text(encoding="utf-8").splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        raise SystemExit(f"Transcript file is empty: {transcript_path}")

    segments: list[CaptionSegment] = []
    for index, line in enumerate(lines):
        start = index * 3.0
        segments.append(CaptionSegment(start=start, end=start + 2.8, text=line))
    return segments


def ffmpeg_subtitle_path(path: Path) -> str:
    # FFmpeg's subtitles filter accepts forward slashes on Windows. Escape characters
    # that are special inside filter values.
    value = path.resolve().as_posix()
    return value.replace("\\", "/").replace(":", r"\:").replace("'", r"\'")


def render_video(ffmpeg: str, source: Path, ass_path: Path, output_path: Path) -> list[str]:
    vf = (
        f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},"
        f"subtitles='{ffmpeg_subtitle_path(ass_path)}'"
    )
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(source),
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    run(cmd)
    return cmd


def drawtext_escape(text: str) -> str:
    return text.replace("\\", r"\\").replace(":", r"\:").replace("'", r"\'").replace("%", r"\%")


def ffmpeg_color(name: str) -> str:
    return str(BRAND_SYSTEM["colors"][name])


def render_intro_card(ffmpeg: str, output_path: Path, title: str, label: str, duration: float) -> list[str]:
    title_text = drawtext_escape(title)
    label_text = drawtext_escape(label or "JEWISH TRAVEL NOTE")
    logo_text = drawtext_escape("Hamsa Nomads")
    font = drawtext_escape(brand_font("body_sans"))
    headline_font = drawtext_escape(brand_font("headline_serif"))
    cream = ffmpeg_color("warm_cream")
    parchment = ffmpeg_color("ivory_parchment")
    ink = ffmpeg_color("ink_black")
    clay = ffmpeg_color("clay")
    olive = ffmpeg_color("olive_sage")
    sand = ffmpeg_color("sand")
    vf = ",".join(
        [
            f"drawbox=x=70:y=250:w=940:h=1420:color={parchment}@0.95:t=fill",
            f"drawbox=x=96:y=282:w=888:h=1360:color={sand}@0.35:t=4",
            f"drawbox=x=170:y=610:w=210:h=5:color={clay}@0.95:t=fill",
            f"drawbox=x=376:y=610:w=170:h=5:color={olive}@0.95:t=fill",
            f"drawbox=x=540:y=590:w=8:h=45:color={olive}@0.95:t=fill",
            f"drawbox=x=545:y=632:w=190:h=5:color={clay}@0.95:t=fill",
            f"drawtext=font='{font}':text='{label_text}':fontcolor={olive}:fontsize=34:x=(w-text_w)/2:y=430",
            f"drawtext=font='{headline_font}':text='{title_text}':fontcolor={ink}:fontsize=76:line_spacing=10:x=(w-text_w)/2:y=780",
            f"drawtext=font='{font}':text='{logo_text}':fontcolor={clay}:fontsize=36:x=(w-text_w)/2:y=1380",
        ]
    )
    cmd = [
        ffmpeg,
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c={cream}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:d={duration}",
        "-f",
        "lavfi",
        "-i",
        f"anullsrc=channel_layout=stereo:sample_rate=44100:d={duration}",
        "-vf",
        vf,
        "-shortest",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "22",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        str(output_path),
    ]
    run(cmd)
    return cmd


def render_remotion(recipe_path: Path, source: Path, output_path: Path) -> list[str]:
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if not npm:
        raise SystemExit("Remotion renderer needs Node.js/npm. Install Node.js, then run npm install in the remotion folder.")
    if not REMOTION_DIR.exists():
        raise SystemExit("Missing remotion folder. Use renderer ffmpeg or restore the Remotion project.")
    cmd = [
        npm,
        "--prefix",
        str(REMOTION_DIR),
        "run",
        "render",
        "--",
        "--recipe",
        str(recipe_path),
        "--video",
        str(source),
        "--out",
        str(output_path),
    ]
    run(cmd)
    return cmd


def concat_videos(ffmpeg: str, intro_path: Path, video_path: Path, output_path: Path, list_path: Path) -> list[str]:
    list_path.write_text(
        f"file '{intro_path.resolve().as_posix()}'\nfile '{video_path.resolve().as_posix()}'\n",
        encoding="utf-8",
    )
    cmd = [
        ffmpeg,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_path),
        "-c",
        "copy",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    run(cmd)
    return cmd


def create_thumbnail(ffmpeg: str, source: Path, thumbnail_path: Path, at: str) -> list[str]:
    vf = f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,crop={VIDEO_WIDTH}:{VIDEO_HEIGHT}"
    cmd = [
        ffmpeg,
        "-y",
        "-ss",
        at,
        "-i",
        str(source),
        "-frames:v",
        "1",
        "-vf",
        vf,
        "-q:v",
        "2",
        str(thumbnail_path),
    ]
    run(cmd)
    return cmd


def write_edit_plan(
    path: Path,
    *,
    source: Path,
    output_video: Path,
    ass_path: Path,
    thumbnail_path: Path,
    style: str,
    model: str,
    segments: list[CaptionSegment],
    commands: list[list[str]],
    recipe: EditRecipe | None = None,
    recipe_path: Path | None = None,
) -> None:
    plan = {
        "project": "hamsa-caption-engine",
        "source": str(source),
        "outputs": {
            "video": str(output_video),
            "subtitles": str(ass_path),
            "thumbnail": str(thumbnail_path),
        },
        "render": {
            "width": VIDEO_WIDTH,
            "height": VIDEO_HEIGHT,
            "format": "mp4",
            "video_codec": "libx264",
            "audio_codec": "aac",
            "hardware_note": "CPU-first settings for weak Windows PCs with Intel graphics; no paid APIs are used.",
        },
        "caption_style": style,
        "renderer": recipe.renderer if recipe else "ffmpeg",
        "brand": {
            "name": BRAND_SYSTEM["name"],
            "colors": BRAND_SYSTEM["colors"],
            "visual_signature": BRAND_SYSTEM["rules"]["visual_signature"],
            "motifs": BRAND_SYSTEM["rules"]["motifs"],
        },
        "transcription": {
            "engine": "faster-whisper",
            "model": model,
            "device": "cpu",
            "compute_type": "int8",
        },
        "segments": [asdict(segment) for segment in segments],
        "recipe_path": str(recipe_path) if recipe_path else None,
        "recipe": recipe.to_dict() if recipe else None,
        "commands": commands,
    }
    path.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a vertical MP4 with styled local captions from one MP4 in /input."
    )
    parser.add_argument("--input", type=Path, help="MP4 to process. Defaults to the only MP4 in ./input.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="Output folder. Default: ./output")
    parser.add_argument("--style", choices=sorted(CAPTION_STYLES), default="hamsa-clean")
    parser.add_argument("--brand", default="hamsa", help="Brand system to use. Default: hamsa")
    parser.add_argument("--prompt", help="Local prompt used to draft edit_recipe.json before rendering.")
    parser.add_argument("--recipe", type=Path, help="Path to a custom edit_recipe.json to render from.")
    parser.add_argument("--renderer", choices=["ffmpeg", "remotion"], help="Renderer override. Default comes from recipe, or ffmpeg.")
    parser.add_argument("--intro-card", help="Optional branded title card text for the first 1.5 seconds.")
    parser.add_argument("--model", default="tiny.en", help="faster-whisper model size. Use tiny.en/base.en on weak PCs.")
    parser.add_argument("--language", default="en", help="Spoken language code, or 'auto'. Default: en")
    parser.add_argument("--thumbnail-at", default="00:00:01", help="Timestamp for thumbnail.jpg. Default: 00:00:01")
    parser.add_argument("--video-name", default="captioned_vertical.mp4", help="Output MP4 filename. Default: captioned_vertical.mp4")
    parser.add_argument("--transcript", type=Path, help="Optional UTF-8 text file; skips Whisper and creates timed captions from lines.")
    return parser.parse_args(argv)


def segments_from_recipe(recipe: EditRecipe) -> list[CaptionSegment]:
    return [
        CaptionSegment(start=item.start, end=item.end, text=item.text)
        for item in recipe.captions
    ]


def overlay_segments_from_recipe(recipe: EditRecipe) -> list[CaptionSegment]:
    return [
        CaptionSegment(start=item.start, end=item.end, text=item.text)
        for item in recipe.overlays
        if item.text.strip() and item.end > item.start
    ]


def build_recipe(args: argparse.Namespace) -> tuple[EditRecipe, Path]:
    if args.recipe:
        recipe = load_recipe(args.recipe)
        return recipe, args.recipe

    recipe = draft_recipe_from_prompt(
        args.prompt or args.intro_card or "Create a warm Hamsa Nomads travel note.",
        fallback_style=args.style,
        brand=args.brand,
        intro_title=args.intro_card,
    )
    if not args.prompt and not args.intro_card:
        recipe.intro_card.enabled = False
    recipe.style = recipe.style or args.style
    recipe.brand = args.brand
    if args.renderer:
        recipe.renderer = args.renderer
    recipe.output_settings.video_name = args.video_name
    recipe.thumbnail.timestamp = args.thumbnail_at
    recipe_path = args.output_dir / "edit_recipe.json"
    return recipe, recipe_path


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    load_brand_system(args.brand)
    source = args.input or find_single_mp4(INPUT_DIR)
    if not source.exists():
        raise SystemExit(f"Input video does not exist: {source}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    recipe, recipe_path = build_recipe(args)
    if recipe.brand != "hamsa":
        raise SystemExit(f"Unsupported recipe brand: {recipe.brand}. Only hamsa is available.")

    if args.renderer:
        recipe.renderer = args.renderer
    renderer = recipe.renderer or "ffmpeg"
    if renderer not in {"ffmpeg", "remotion"}:
        raise SystemExit(f"Unsupported renderer: {renderer}. Use ffmpeg or remotion.")
    ffmpeg = require_binary("ffmpeg") if renderer == "ffmpeg" else shutil.which("ffmpeg")

    style = recipe.style if recipe.style in CAPTION_STYLES else args.style
    video_name = recipe.output_settings.video_name or args.video_name
    output_video = args.output_dir / video_name
    ass_path = args.output_dir / "captions.ass"
    thumbnail_path = args.output_dir / (recipe.output_settings.thumbnail_name or "thumbnail.jpg")
    edit_plan_path = args.output_dir / "edit_plan.json"
    commands: list[list[str]] = []

    if not args.recipe:
        save_recipe(recipe, recipe_path)

    recipe_segments = segments_from_recipe(recipe)
    segments: list[CaptionSegment] = []
    with tempfile.TemporaryDirectory(prefix="hamsa_caption_") as temp_dir:
        temp_root = Path(temp_dir)
        wav_path = temp_root / "audio.wav"
        if recipe_segments:
            segments = recipe_segments
        elif args.transcript:
            segments = transcript_segments(args.transcript)
        elif renderer == "ffmpeg":
            if not ffmpeg:
                raise SystemExit("FFmpeg renderer needs ffmpeg.exe in the project folder or on PATH.")
            commands.append(extract_audio(ffmpeg, source, wav_path))
            language = None if args.language.lower() == "auto" else args.language
            segments = transcribe(wav_path, args.model, language)

        segments = [*segments, *overlay_segments_from_recipe(recipe)]
        if renderer == "ffmpeg" and not segments:
            raise SystemExit("No caption segments were produced.")
        write_ass(ass_path, segments, style)

        if renderer == "remotion":
            if recipe_path != args.output_dir / "edit_recipe.json":
                recipe_path = args.output_dir / "edit_recipe.json"
            save_recipe(recipe, recipe_path)
            commands.append(render_remotion(recipe_path, source, output_video))
        else:
            intro_enabled = bool(recipe.intro_card.enabled or args.intro_card)
            if intro_enabled:
                main_video = temp_root / "captioned_main.mp4"
                intro_video = temp_root / "intro_card.mp4"
                concat_list = temp_root / "concat.txt"
                commands.append(render_video(ffmpeg, source, ass_path, main_video))
                commands.append(
                    render_intro_card(
                        ffmpeg,
                        intro_video,
                        args.intro_card or recipe.intro_card.title or recipe.project_title,
                        recipe.intro_card.label or "JEWISH TRAVEL NOTE",
                        recipe.intro_card.duration_seconds or 1.5,
                    )
                )
                commands.append(concat_videos(ffmpeg, intro_video, main_video, output_video, concat_list))
            else:
                commands.append(render_video(ffmpeg, source, ass_path, output_video))

    if ffmpeg:
        commands.append(create_thumbnail(ffmpeg, source, thumbnail_path, recipe.thumbnail.timestamp or args.thumbnail_at))
        for index, screenshot in enumerate(recipe.screenshots, start=1):
            screenshot_path = args.output_dir / f"screenshot_{index:02d}.jpg"
            commands.append(create_thumbnail(ffmpeg, source, screenshot_path, screenshot.timestamp))
    else:
        print("Skipping FFmpeg thumbnail/screenshot export because ffmpeg was not found.")
    write_edit_plan(
        edit_plan_path,
        source=source,
        output_video=output_video,
        ass_path=ass_path,
        thumbnail_path=thumbnail_path,
        style=style,
        model=args.model,
        segments=segments,
        commands=commands,
        recipe=recipe,
        recipe_path=recipe_path,
    )

    print(f"Wrote {output_video}")
    print(f"Wrote {ass_path}")
    print(f"Wrote {thumbnail_path}")
    print(f"Wrote {recipe_path}")
    print(f"Wrote {edit_plan_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
