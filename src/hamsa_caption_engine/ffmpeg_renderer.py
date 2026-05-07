from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path
from typing import Any

from .paths import find_ffmpeg, find_ffprobe
from .recipe_schema import validate_recipe, save_recipe
from .transcription import load_manual_transcript, save_transcript, segments_from_transcript_text, transcribe_with_whisper

VIDEO_W = 1080
VIDEO_H = 1920

STYLE_COLORS = {
    "video_game_dialogue": ("&H00111111", "&H00E7F2F6", "&H006A8A7B"),
    "game": ("&H00111111", "&H00E7F2F6", "&H006A8A7B"),
    "paris-tip": ("&H00111111", "&H00DBE7EC", "&H006A88C8"),
    "hamsa-clean": ("&H00111111", "&H00E7F2F6", "&H006A8A7B"),
    "wrong-vs-right": ("&H00111111", "&H00DBE7EC", "&H006A88C8"),
    "passport_stamp": ("&H00111111", "&H00DBE7EC", "&H00A1C7DC"),
    "retreat_luxury": ("&H00111111", "&H00DBE7EC", "&H00A1C7DC"),
}


def _ass_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "").replace("}", "").replace("\n", "\\N")


def _ass_time(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - math.floor(seconds)) * 100))
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


def write_ass(segments: list[dict[str, Any]], recipe: dict[str, Any], path: Path) -> Path:
    style = recipe.get("style", {}).get("name", "hamsa-clean")
    primary, back, outline = STYLE_COLORS.get(style, STYLE_COLORS["hamsa-clean"])
    label = recipe.get("intro_card", {}).get("label", "HAMSA NOMADS")
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {VIDEO_W}
PlayResY: {VIDEO_H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,Arial,66,{primary},&H000000FF,{outline},{back},-1,0,0,0,100,100,0,0,3,4,0,2,84,84,250,1
Style: Label,Georgia,44,&H00111111,&H000000FF,&H00A1C7DC,&H00E7F2F6,-1,0,0,0,100,100,0,0,3,2,0,8,80,80,120,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    intro = recipe.get("intro_card", {})
    if intro.get("enabled", True):
        end = float(intro.get("duration_sec", 1.8))
        events.append(f"Dialogue: 2,{_ass_time(0)},{_ass_time(end)},Label,,0,0,0,,{_ass_escape(label)}\\N{_ass_escape(intro.get('headline', 'Jewish travel note'))}")
    for seg in segments:
        events.append(f"Dialogue: 3,{_ass_time(float(seg['start']))},{_ass_time(float(seg['end']))},Caption,,0,0,0,,{_ass_escape(seg['text'])}")
    for card in recipe.get("section_cards", []):
        start = float(card.get("start_sec", 0))
        end = start + float(card.get("duration_sec", 0.7))
        events.append(f"Dialogue: 4,{_ass_time(start)},{_ass_time(end)},Label,,0,0,0,,{_ass_escape(card.get('title', 'LOCAL TIP'))}")
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    return path


def _detect_cut_plan(video_path: Path, output_dir: Path, recipe: dict[str, Any], log_notes: list[str]) -> dict[str, Any]:
    settings = recipe.get("auto_cut", {})
    plan = {"enabled": bool(settings.get("enabled", False)), "source": str(video_path), "segments": [], "notes": []}
    if not plan["enabled"]:
        output_dir.joinpath("cut_plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
        return plan
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        plan["notes"].append("auto-cut skipped: ffmpeg missing")
        output_dir.joinpath("cut_plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
        return plan
    threshold = settings.get("silence_threshold_db", -35)
    min_silence = settings.get("min_silence_duration_sec", 0.7)
    cmd = [ffmpeg, "-hide_banner", "-i", str(video_path), "-af", f"silencedetect=noise={threshold}dB:d={min_silence}", "-f", "null", "-"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    stderr = proc.stderr or ""
    silences: list[dict[str, float]] = []
    current_start: float | None = None
    for line in stderr.splitlines():
        if "silence_start:" in line:
            try:
                current_start = float(line.rsplit("silence_start:", 1)[1].strip())
            except ValueError:
                pass
        if "silence_end:" in line and current_start is not None:
            try:
                end_part = line.split("silence_end:", 1)[1].split("|", 1)[0].strip()
                silences.append({"start": current_start, "end": float(end_part)})
            except ValueError:
                pass
            current_start = None
    plan["silences"] = silences
    if silences and silences[0]["start"] <= 0.2 and silences[0]["end"] >= 1.0:
        note = f"opening trimmed candidate: first dead air ends at {silences[0]['end']:.2f}s"
        plan["notes"].append(note)
        log_notes.append(note)
    # Conservative metadata-only plan: renderer falls back to original footage to avoid sync damage on weak PCs.
    plan["notes"].append("cut metadata saved; original media preserved; jump-cut render can be expanded from this plan")
    output_dir.joinpath("cut_plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
    return plan


def render_ffmpeg(video_path: str | Path, output_dir: str | Path, recipe: dict[str, Any], *, transcript_path: str | Path | None = None, thumbnail_at: str = "00:00:01") -> dict[str, Any]:
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("FFmpeg missing. Run download_ffmpeg.bat or put ffmpeg.exe and ffprobe.exe inside tools\\ffmpeg\\bin\\.")
    video = Path(video_path)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    recipe = validate_recipe(recipe)
    recipe["renderer"] = "ffmpeg"
    recipe["input_video"]["src"] = str(video)
    notes: list[str] = []
    _detect_cut_plan(video, out, recipe, notes)

    if transcript_path:
        transcript = load_manual_transcript(transcript_path)
    else:
        try:
            transcript = transcribe_with_whisper(video, model=recipe.get("transcription", {}).get("model", "base"), language=recipe.get("transcription", {}).get("language", "auto"))
        except RuntimeError:
            transcript = {"mode": "fallback", "segments": segments_from_transcript_text(recipe.get("intro_card", {}).get("headline", "Hamsa Nomads travel tip")), "text": ""}
            notes.append("automatic transcription unavailable; used branded fallback captions")
    save_transcript(transcript, out / "transcript.json")
    ass = write_ass(transcript.get("segments", []), recipe, out / "captions.ass")
    save_recipe(recipe, out / "edit_recipe.json")

    vf = f"scale={VIDEO_W}:{VIDEO_H}:force_original_aspect_ratio=increase,crop={VIDEO_W}:{VIDEO_H},subtitles={ass.as_posix()}"
    final = out / "final_video.mp4"
    cmd = [ffmpeg, "-y", "-i", str(video), "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(final)]
    subprocess.run(cmd, check=True)
    thumb = out / "thumbnail.jpg"
    subprocess.run([ffmpeg, "-y", "-ss", thumbnail_at, "-i", str(video), "-frames:v", "1", "-vf", f"scale={VIDEO_W}:{VIDEO_H}:force_original_aspect_ratio=increase,crop={VIDEO_W}:{VIDEO_H}", str(thumb)], check=True)
    return {"final_video": final, "thumbnail": thumb, "recipe": out / "edit_recipe.json", "transcript": out / "transcript.json", "notes": notes}
